# app.py
from flask import Flask, request, render_template, redirect, url_for, flash
import os
import dropbox
import smtplib
from email.mime.text import MIMEText

# === Konfiguration ===
DROPBOX_TOKEN = os.getenv("DROPBOX_TOKEN")  # Setze als Umgebungsvariable
EMAIL_HOST = os.getenv("EMAIL_HOST")        # z. B. smtp.mailgun.org
EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587))
EMAIL_HOST_USER = os.getenv("EMAIL_USER")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_PASS")
EMAIL_FROM = os.getenv("EMAIL_FROM")        # z. B. "noreply@deine-domain.de"

db = dropbox.Dropbox(DROPBOX_TOKEN)

app = Flask(__name__)
app.secret_key = "supersecretkey"  # für Flash-Messages

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form["name"].strip()
        nummer = request.form["nummer"].strip()
        pin = request.form["pin"].strip()
        email = request.form["email"].strip()

        base_filename = f"{name}_{nummer}_{pin}_"
        result = search_dropbox_video(base_filename)

        if result:
            send_email(email, result)
            flash("Link zum Video wurde an die angegebene E-Mail-Adresse gesendet.", "success")
        else:
            flash("Kein Video mit diesen Angaben gefunden.", "danger")

        return redirect(url_for("index"))

    return render_template("form.html")

def search_dropbox_video(prefix):
    try:
        response = db.files_list_folder("")  # Root-Verzeichnis
        for entry in response.entries:
            if entry.name.startswith(prefix) and entry.name.endswith(".mp4"):
                shared_link = db.sharing_create_shared_link_with_settings(entry.path_lower)
                return shared_link.url.replace("?dl=0", "?dl=1")  # Direktdownload
    except Exception as e:
        print("Dropbox-Fehler:", e)
    return None

def send_email(to_address, video_link):
    subject = "Dein persönliches Video ist verfügbar"
    body = f"Hier ist dein persönliches Video-Link: {video_link}"

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = to_address

    try:
        with smtplib.SMTP(EMAIL_HOST, EMAIL_PORT) as server:
            server.starttls()
            server.login(EMAIL_HOST_USER, EMAIL_HOST_PASSWORD)
            server.sendmail(EMAIL_FROM, [to_address], msg.as_string())
    except Exception as e:
        print("E-Mail-Fehler:", e)

if __name__ == "__main__":
    app.run(debug=True)
