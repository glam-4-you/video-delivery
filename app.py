from flask import Flask, request, render_template, redirect, url_for, flash
import os
import googleapiclient.discovery
import googleapiclient.errors
from google.oauth2 import service_account

# ---- Google Drive Einstellungen ----
FOLDER_ID = "1zO2qTb3CBj10M9SZycJCVFKbIgvCSBpE"  # <-- Passe hier ggf. an!
SERVICE_ACCOUNT_FILE = "service-account.json"     # Der Dateiname deines Service-Accounts
SCOPES = ["https://www.googleapis.com/auth/drive"]  # NICHT readonly!

# ---- Flask App ----
app = Flask(__name__)
app.secret_key = "supersecretkey"

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = googleapiclient.discovery.build("drive", "v3", credentials=creds)
    return service

def ensure_public_permission(service, file_id):
    try:
        # Versucht, jedem Lesezugriff zu geben (Fehler, wenn schon vorhanden = egal)
        service.permissions().create(
            fileId=file_id,
            body={'type': 'anyone', 'role': 'reader'},
        ).execute()
    except Exception as e:
        print(f"(Warnung: {e})")  # Meist harmlos, wenn Permission schon existiert

def list_drive_videos(name, pin):
    service = get_drive_service()
    matches = []
    try:
        results = service.files().list(
            q=f"'{FOLDER_ID}' in parents and trashed = false",
            fields="files(id, name, webViewLink)",
            pageSize=1000
        ).execute()
        files = results.get("files", [])
        print(f"Gefundene Dateien im Ordner: {[f.get('name') for f in files]}")   # <-- Neue Zeile

        for f in files:
            fname = f.get("name", "")
            file_id = f.get("id", "")
            webview_link = f.get("webViewLink", "")

            name_in_file = fname.lower().startswith(name.lower())
            pin_in_file = pin in fname

            if name_in_file and pin_in_file:
                ensure_public_permission(service, file_id)
                matches.append((fname, webview_link))

    except Exception as e:
        print(f"Fehler bei der Google-Drive-Abfrage: {e}")
        return []

    return matches

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        pin = request.form.get("pin", "").strip()
        matches = list_drive_videos(name, pin)

        if matches:
            return render_template("results.html", matches=matches)
        else:
            flash("Kein passendes Video gefunden.", "danger")
            return redirect(url_for("index"))

    return render_template("form.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
