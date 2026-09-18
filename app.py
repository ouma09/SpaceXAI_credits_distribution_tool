#!/usr/bin/env python3
"""Local web UI: write an email, add recipients, add a credits link, preview, and send."""

from __future__ import annotations

from io import StringIO
import csv

from flask import Flask, make_response, render_template, request

from send_links import (
    DEFAULT_OUTPUT,
    assign_pairs,
    parse_emails_text,
    parse_links_text,
    parse_people_text,
    render_body,
    send_emails,
    write_assignments,
)

app = Flask(__name__)


def read_upload(field: str) -> str:
    uploaded = request.files.get(field)
    if uploaded and uploaded.filename:
        return uploaded.read().decode("utf-8-sig")
    return ""


def form_state(**extra):
    data = {
        "emails": request.form.get("emails", ""),
        "link": request.form.get("link", ""),
        "subject": request.form.get("subject", ""),
        "email_body": request.form.get("email_body", ""),
        "smtp_user": request.form.get("smtp_user", ""),
        "mail_from": request.form.get("mail_from", ""),
        "error": None,
        "message": None,
        "rows": None,
        "people_count": 0,
        "preview_to": "",
        "preview_subject": "",
        "preview_body": "",
    }
    data.update(extra)
    return render_template("index.html", **data)


def build_pairs():
    emails_text = request.form.get("emails", "")
    csv_text = read_upload("csv_file")
    link_text = request.form.get("link", "")

    if emails_text.strip():
        people = parse_emails_text(emails_text)
    elif csv_text.strip():
        people = parse_people_text(csv_text)
    else:
        raise ValueError("Paste a list of emails, or upload a CSV.")

    if not people:
        raise ValueError("No valid email addresses found.")

    links = parse_links_text(link_text)
    if not links:
        raise ValueError("Add the credits link.")

    pairs = assign_pairs(people, links)
    return people, links, pairs


def pairs_as_rows(pairs):
    return [
        {
            "email": person.email,
            "name": person.display_name,
            "link": link,
        }
        for person, link in pairs
    ]


def preview_payload(pairs, subject, email_body):
    person, link = pairs[0]
    return {
        "rows": pairs_as_rows(pairs),
        "people_count": len(pairs),
        "preview_to": person.email,
        "preview_subject": subject or "(no subject)",
        "preview_body": render_body(email_body, person, link),
    }


@app.get("/")
def index():
    return form_state()


@app.post("/preview")
def preview():
    subject = request.form.get("subject", "").strip()
    email_body = request.form.get("email_body", "")
    try:
        _people, _links, pairs = build_pairs()
    except ValueError as exc:
        return form_state(error=str(exc))

    write_assignments(DEFAULT_OUTPUT, pairs)
    return form_state(
        message=f"Ready to send to {len(pairs)} recipient(s). Check the preview below.",
        **preview_payload(pairs, subject, email_body),
    )


@app.post("/send")
def send():
    subject = request.form.get("subject", "").strip()
    email_body = request.form.get("email_body", "")
    try:
        _people, _links, pairs = build_pairs()
    except ValueError as exc:
        return form_state(error=str(exc))

    if not subject:
        return form_state(error="Write an email subject.", **preview_payload(pairs, subject, email_body))
    if not email_body.strip():
        return form_state(error="Write the email body.", **preview_payload(pairs, subject, email_body))

    write_assignments(DEFAULT_OUTPUT, pairs)
    user = request.form.get("smtp_user", "").strip()
    password = request.form.get("smtp_pass", "").strip()
    mail_from = request.form.get("mail_from", "").strip() or user
    extra = preview_payload(pairs, subject, email_body)

    try:
        sent, failed = send_emails(
            pairs,
            subject,
            0.8,
            body=email_body,
            user=user,
            password=password,
            mail_from=mail_from,
        )
    except ValueError as exc:
        return form_state(error=str(exc), **extra)
    except Exception as exc:  # noqa: BLE001
        return form_state(error=f"Send failed: {exc}", **extra)

    return form_state(message=f"Sent {sent} emails. Failed {failed}.", **extra)


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
