# Credits link sender

Assign one unique Cursor referral link to each person in a Luma CSV, then optionally email that link.

The script is standalone. It does not use the parent hackathon app.

## Files

| File | Purpose |
| --- | --- |
| `app.py` | Local web UI for CSV upload, preview, and send |
| `send_links.py` | Reads people + links, assigns one link per person, can send email |
| `links.txt` | Unique referral URLs, one per line |
| `assigned.csv` | Output: each email paired with its link |
| `emails.csv` | Email-only export from `assigned.csv` |
| `recipients.csv` | Sample people file (`email`, `name`) |

Default people file: `c:\Users\DELL\Downloads\luma-10am-2pm.csv`

Expected Luma columns: `email`, `first_name`, `last_name`, `checked_in_at`

## Web interface

Upload the people CSV in the browser instead of using the command line.

```powershell
pip install -r requirements.txt
python app.py
```

Then open [http://127.0.0.1:5050](http://127.0.0.1:5050).

1. Choose the Luma people CSV
2. Paste or upload unique links (one per line)
3. Click **Preview assignments** to pair one link per person
4. Optionally enter Gmail + App Password and click **Send emails**

The preview writes `assigned.csv`. You can also download `emails.csv` from the page.

## Requirements

- Python 3
- `pip install -r requirements.txt` (for the web UI)
- Gmail account with [2-Step Verification](https://myaccount.google.com/security)
- A Gmail [App Password](https://myaccount.google.com/apppasswords) (not your normal login)

## Assign links (dry run)

Puts one unique link on each person and writes `assigned.csv`. Does not send mail.

```powershell
python send_links.py
```

Or with explicit paths:

```powershell
python send_links.py --csv "c:\Users\DELL\Downloads\luma-10am-2pm.csv" --links links.txt --out assigned.csv
```

You need at least as many links in `links.txt` as people in the CSV.

## Send all assigned emails

```powershell
$env:SMTP_USER = "oessarhi@gmail.com"
$env:SMTP_PASS = "your-16-char-app-password"
$env:MAIL_FROM = "oessarhi@gmail.com"
python send_links.py --send
```

Optional:

```powershell
python send_links.py --send --subject "Your Cursor referral link" --delay 1
```

## Send one extra email

```powershell
python send_links.py --one "person@email.com" --link "https://cursor.com/referral?code=XXXX" --send
```

Without `--send`, this only appends the row to `assigned.csv`.

## Environment variables

| Variable | Required | Default | Meaning |
| --- | --- | --- | --- |
| `SMTP_USER` | yes, for `--send` | | Gmail address that sends |
| `SMTP_PASS` | yes, for `--send` | | 16-character App Password |
| `MAIL_FROM` | yes, for `--send` | same as `SMTP_USER` | From address |
| `SMTP_HOST` | no | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | no | `587` | SMTP port |

Do not commit App Passwords. Do not paste them into chat.

## One-link-per-person rule

- Each person gets exactly one link
- Duplicate emails in the people CSV are skipped
- Duplicate links in `links.txt` are skipped
- Extra unused links are left unused
- If there are fewer links than people, the script stops
