# Credits link sender

Write an email, paste a list of recipients, add a Cursor credits link, preview the message, then send it from Gmail.

## Setup

You need Python 3.

```powershell
pip install -r requirements.txt
```

To send mail you also need:

- A Gmail account with [2-Step Verification](https://myaccount.google.com/security)
- A Gmail [App Password](https://myaccount.google.com/apppasswords) (not your normal login password)

Do not commit App Passwords. Do not paste them into chat.

## Start the app

```powershell
python app.py
```

Open [http://127.0.0.1:5050](http://127.0.0.1:5050).

## How to send credits

1. **Recipient emails** — paste one address per line.

   ```
   one@email.com
   two@email.com
   ```

   Optional name on the same line:

   ```
   one@email.com,Alex
   Alex <two@email.com>
   ```

2. **Credits link** — paste the redeem URL, for example `https://cursor.com/redeem/event/...`

3. **Email subject** — write the subject yourself.

4. **Email body** — write the full email yourself.

   Placeholders you can use:

   | Placeholder | Replaced with |
   | --- | --- |
   | `{link}` | the credits link |
   | `{name}` | the person's name, or `there` if you did not add one |
   | `{email}` | the recipient address |

   Example:

   ```
   Hi {name},

   Thanks for joining the meetup.

   Here is your Cursor credits redeem link:
   {link}

   Open the link, sign in to Cursor, and redeem your credits.
   ```

5. Click **Preview email** and check the rendered message plus the recipient list.

6. Enter your **Gmail address** and **Gmail App Password**.

7. Click **Send emails**. Confirm the dialog. Each person gets their own copy of the email.

One credits link is sent to everyone. If you paste several unique links instead (one per line in a links file via the CLI), each person still gets exactly one link.

## Optional: people CSV

If you do not want to paste emails, open **Or upload a people CSV** and upload a file with an `email` column.

Luma exports work. Useful columns: `email`, `first_name`, `last_name`, `checked_in_at`.

The CSV is used only when the recipient box is empty.

## Downloads

After a preview or send, the page can export:

- `assigned.csv` — each email paired with the link
- `emails.csv` — email addresses only

These files stay local and are gitignored.

## Command line (optional)

Assign links from a CSV without opening the browser:

```powershell
python send_links.py --csv people.csv --links links.txt --out assigned.csv
```

Send with a custom subject and body:

```powershell
$env:SMTP_USER = "you@gmail.com"
$env:SMTP_PASS = "your-16-char-app-password"
$env:MAIL_FROM = "you@gmail.com"
python send_links.py --send --subject "Your Cursor credits" --body "Hi {name},`n`nHere is your link:`n{link}"
```

Send one extra email:

```powershell
python send_links.py --one "person@email.com" --link "https://cursor.com/redeem/..." --subject "Your Cursor credits" --body "Hi {name},`n`n{link}" --send
```

Without `--send`, the script only writes `assigned.csv`.

## Environment variables

| Variable | Required for send | Default | Meaning |
| --- | --- | --- | --- |
| `SMTP_USER` | yes | | Gmail address that sends |
| `SMTP_PASS` | yes | | 16-character App Password |
| `MAIL_FROM` | yes | same as `SMTP_USER` | From address |
| `SMTP_HOST` | no | `smtp.gmail.com` | SMTP server |
| `SMTP_PORT` | no | `587` | SMTP port |

## Files

| File | Purpose |
| --- | --- |
| `app.py` | Local web UI |
| `send_links.py` | Assign links and send email |
| `templates/index.html` | The compose / preview page |
| `requirements.txt` | Python dependencies (`flask`) |
