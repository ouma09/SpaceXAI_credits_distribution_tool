#!/usr/bin/env python3
"""Local web UI: upload a people CSV, paste links, preview, and send."""

from __future__ import annotations

from io import StringIO
import csv

from flask import Flask, make_response, render_template, request

from send_links import (
    DEFAULT_OUTPUT,
    assign_pairs,
    parse_links_text,
    parse_people_text,
    send_emails,
    write_assignments,
)

app = Flask(__name__)


def read_upload(field: str) -> str:
    uploaded = request.files.get(field)
    if uploaded and uploaded.filename:
        return uploaded.read().decode("utf-8-sig")
    return ""


def build_pairs():
    csv_text = read_upload("csv_file")
    links_text = request.form.get("links", "")
    links_file = read_upload("links_file")
    if links_file:
        links_text = f"{links_text}\n{links_file}"

    if not csv_text.strip():
        raise ValueError("Upload a CSV that includes an email column.")
    people = parse_people_text(csv_text)
    links = parse_links_text(links_text)
    pairs = assign_pairs(people, links)
    extra = max(0, len(links) - len(people))
    return people, links, pairs, extra


def pairs_as_rows(pairs):
    return [
        {
            "email": person.email,
            "name": person.display_name,
            "link": link,
        }
        for person, link in pairs
    ]


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/preview")
def preview():
    try:
        people, links, pairs, extra = build_pairs()
    except ValueError as exc:
        return render_template("index.html", error=str(exc), links=request.form.get("links", ""))

    write_assignments(DEFAULT_OUTPUT, pairs)
    return render_template(
        "index.html",
        rows=pairs_as_rows(pairs),
        people_count=len(people),
        links_count=len(links),
        extra_links=extra,
        links=request.form.get("links", ""),
        message=f"Assigned {len(pairs)} unique links. Saved to assigned.csv.",
    )


@app.post("/send")
def send():
    try:
        people, links, pairs, extra = build_pairs()
    except ValueError as exc:
        return render_template("index.html", error=str(exc), links=request.form.get("links", ""))

    write_assignments(DEFAULT_OUTPUT, pairs)
    user = request.form.get("smtp_user", "").strip()
    password = request.form.get("smtp_pass", "").strip()
    mail_from = request.form.get("mail_from", "").strip() or user
    subject = request.form.get("subject", "").strip() or "Your unique link"

    try:
        sent, failed = send_emails(
            pairs,
            subject,
            0.8,
            user=user,
            password=password,
            mail_from=mail_from,
        )
    except ValueError as exc:
        return render_template(
            "index.html",
            error=str(exc),
            rows=pairs_as_rows(pairs),
            people_count=len(people),
            links_count=len(links),
            extra_links=extra,
            links=request.form.get("links", ""),
        )
    except Exception as exc:  # noqa: BLE001
        return render_template(
            "index.html",
            error=f"Send failed: {exc}",
            rows=pairs_as_rows(pairs),
            people_count=len(people),
            links_count=len(links),
            extra_links=extra,
            links=request.form.get("links", ""),
        )

    return render_template(
        "index.html",
        rows=pairs_as_rows(pairs),
        people_count=len(people),
        links_count=len(links),
        extra_links=extra,
        links=request.form.get("links", ""),
        message=f"Sent {sent} emails. Failed {failed}.",
    )


@app.get("/assigned.csv")
def download_assigned():
    if not DEFAULT_OUTPUT.exists():
        return "No assigned.csv yet. Preview first.", 404
    response = make_response(DEFAULT_OUTPUT.read_text(encoding="utf-8"))
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=assigned.csv"
    return response


@app.get("/emails.csv")
def download_emails():
    if not DEFAULT_OUTPUT.exists():
        return "No assigned.csv yet. Preview first.", 404
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["email"])
    seen: set[str] = set()
    with DEFAULT_OUTPUT.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            email = (row.get("email") or "").strip()
            if email and email.lower() not in seen:
                seen.add(email.lower())
                writer.writerow([email])
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=emails.csv"
    return response


if __name__ == "__main__":
    print("Open http://127.0.0.1:5050")
    app.run(host="127.0.0.1", port=5050, debug=False)
