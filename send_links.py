#!/usr/bin/env python3
"""Assign one unique link per person from a Luma CSV and optionally email it."""

from __future__ import annotations

import argparse
import csv
import os
import smtplib
import ssl
import sys
import time
from dataclasses import dataclass
from email.message import EmailMessage
from pathlib import Path


DEFAULT_CSV = Path(r"c:\Users\DELL\Downloads\luma-10am-2pm.csv")
DEFAULT_LINKS = Path(__file__).with_name("links.txt")
DEFAULT_OUTPUT = Path(__file__).with_name("assigned.csv")


@dataclass
class Person:
    email: str
    first_name: str
    last_name: str
    checked_in_at: str

    @property
    def display_name(self) -> str:
        name = " ".join(part for part in (self.first_name, self.last_name) if part)
        return name or "there"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Give each person in a CSV exactly one unique link."
    )
    parser.add_argument("--csv", type=Path, default=DEFAULT_CSV, help="People CSV path")
    parser.add_argument("--links", type=Path, default=DEFAULT_LINKS, help="Links file (one URL per line)")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUTPUT, help="Assignment CSV to write")
    parser.add_argument("--send", action="store_true", help="Actually send emails (off by default)")
    parser.add_argument("--one", help="Send one extra email to this address")
    parser.add_argument("--link", help="Unique link to send with --one")
    parser.add_argument("--delay", type=float, default=0.8, help="Seconds between emails")
    parser.add_argument(
        "--subject",
        default="Your unique link",
        help="Email subject line",
    )
    return parser.parse_args()


def parse_people_text(text: str) -> list[Person]:
    from io import StringIO

    reader = csv.DictReader(StringIO(text.lstrip("\ufeff")))
    if not reader.fieldnames:
        raise ValueError("CSV has no header row")

    headers = {name.strip().lower(): name for name in reader.fieldnames if name}
    email_key = headers.get("email")
    if not email_key:
        raise ValueError("CSV must have an email column")

    people: list[Person] = []
    seen: set[str] = set()
    for row in reader:
        email = (row.get(email_key) or "").strip()
        if not email or email.lower() in seen:
            continue
        seen.add(email.lower())
        first_name = (row.get(headers.get("first_name", ""), "") or "").strip()
        if not first_name:
            first_name = (row.get(headers.get("name", ""), "") or "").strip()
        people.append(
            Person(
                email=email,
                first_name=first_name,
                last_name=(row.get(headers.get("last_name", ""), "") or "").strip(),
                checked_in_at=(row.get(headers.get("checked_in_at", ""), "") or "").strip(),
            )
        )
    return people


def parse_links_text(text: str) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for raw in text.splitlines():
        link = raw.strip()
        if not link or link.startswith("#"):
            continue
        if link in seen:
            continue
        seen.add(link)
        links.append(link)
    return links


def assign_pairs(people: list[Person], links: list[str]) -> list[tuple[Person, str]]:
    if not people:
        raise ValueError("No people found in the CSV.")
    if len(links) < len(people):
        raise ValueError(
            f"Not enough links. Need {len(people)}, have {len(links)}."
        )
    return list(zip(people, links))


def load_people(csv_path: Path) -> list[Person]:
    if not csv_path.exists():
        raise SystemExit(f"CSV not found: {csv_path}")
    try:
        return parse_people_text(csv_path.read_text(encoding="utf-8-sig"))
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc


def load_links(links_path: Path) -> list[str]:
    if not links_path.exists():
        raise SystemExit(
            f"Links file not found: {links_path}\n"
            "Add one unique URL per line, then run again."
        )
    return parse_links_text(links_path.read_text(encoding="utf-8"))


def write_assignments(path: Path, pairs: list[tuple[Person, str]], append: bool = False) -> None:
    exists = path.exists() and path.stat().st_size > 0
    mode = "a" if append and exists else "w"
    with path.open(mode, newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        if mode == "w":
            writer.writerow(["email", "first_name", "last_name", "link", "checked_in_at"])
        for person, link in pairs:
            writer.writerow(
                [person.email, person.first_name, person.last_name, link, person.checked_in_at]
            )


def build_email(person: Person, link: str, subject: str, mail_from: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = mail_from
    message["To"] = person.email
    message["Subject"] = subject
    message.set_content(
        f"Hi {person.display_name},\n\n"
        f"Here is your unique link:\n{link}\n\n"
        "This link is only for you — please do not share it.\n"
    )
    message.add_alternative(
        f"""<p>Hi {person.display_name},</p>
<p>Here is your unique link:</p>
<p><a href="{link}">{link}</a></p>
<p>This link is only for you — please do not share it.</p>""",
        subtype="html",
    )
    return message


def send_emails(
    pairs: list[tuple[Person, str]],
    subject: str,
    delay: float,
    *,
    user: str = "",
    password: str = "",
    mail_from: str = "",
    host: str = "",
    port: int | None = None,
) -> tuple[int, int]:
    host = host or os.environ.get("SMTP_HOST", "smtp.gmail.com")
    port = port if port is not None else int(os.environ.get("SMTP_PORT", "587"))
    user = user or os.environ.get("SMTP_USER", "")
    password = password or os.environ.get("SMTP_PASS", "")
    mail_from = mail_from or os.environ.get("MAIL_FROM", user)

    if not user or not password or not mail_from:
        raise ValueError(
            "Set SMTP_USER, SMTP_PASS, and MAIL_FROM before using --send.\n"
            "Example (PowerShell):\n"
            '  $env:SMTP_USER = "you@gmail.com"\n'
            '  $env:SMTP_PASS = "your-app-password"\n'
            '  $env:MAIL_FROM = "you@gmail.com"'
        )

    context = ssl.create_default_context()
    sent = 0
    failed = 0

    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls(context=context)
        smtp.login(user, password)
        for index, (person, link) in enumerate(pairs, start=1):
            try:
                smtp.send_message(build_email(person, link, subject, mail_from))
                sent += 1
                print(f"[{index}/{len(pairs)}] sent {person.email}")
            except Exception as exc:  # noqa: BLE001
                failed += 1
                print(f"[{index}/{len(pairs)}] FAILED {person.email}: {exc}", file=sys.stderr)
            if index < len(pairs) and delay > 0:
                time.sleep(delay)

    return sent, failed


def main() -> None:
    args = parse_args()

    if args.one:
        if not args.link:
            raise SystemExit("Pass --link with --one, for example:\n  python send_links.py --one person@email.com --link https://...")
        person = Person(email=args.one.strip(), first_name="", last_name="", checked_in_at="")
        pairs = [(person, args.link.strip())]
        write_assignments(args.out, pairs, append=True)
        print(f"Extra assignment: {person.email} -> {args.link.strip()}")
        if not args.send:
            print("Dry run only. Re-run with --send to email this link.")
            return
        try:
            sent, failed = send_emails(pairs, args.subject, args.delay)
        except ValueError as exc:
            raise SystemExit(str(exc)) from exc
        print(f"\nDone. Sent {sent}, failed {failed}.")
        return

    people = load_people(args.csv)
    links = load_links(args.links)

    print(f"People in CSV: {len(people)}")
    print(f"Unique links:  {len(links)}")

    try:
        pairs = assign_pairs(people, links)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if len(links) > len(people):
        unused = len(links) - len(people)
        print(f"Warning: {unused} extra link(s) will not be used.")
    write_assignments(args.out, pairs)

    print("\nAssignment preview (one link per person):")
    for person, link in pairs:
        print(f"  {person.email:40} -> {link}")
    print(f"\nWrote {args.out}")

    if not args.send:
        print("Dry run only. Re-run with --send to email each person their link.")
        return

    try:
        sent, failed = send_emails(pairs, args.subject, args.delay)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    print(f"\nDone. Sent {sent}, failed {failed}.")


if __name__ == "__main__":
    main()
