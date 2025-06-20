from flask import Flask, request, render_template, redirect, url_for, flash
import os
from googleapiclient.discovery import build
from google.oauth2 import service_account

SCOPES = ['https://www.googleapis.com/auth/drive']
SERVICE_ACCOUNT_FILE = (
    "/etc/secrets/service-account.json"
    if os.path.exists("/etc/secrets/service-account.json")
    else "service-account.json"
)
FOLDER_ID = "1GK0SNOvUuhY6DpfgwCq3b5qA41YmZap4"

app = Flask(__name__)
app.secret_key = "supersecretkey"

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build('drive', 'v3', credentials=creds)

def list_drive_videos(name, pin):
    service = get_drive_service()
    try:
        print(f"\nDEBUG: Suche in Google Drive Ordner {FOLDER_ID} nach Name='{name}', PIN='{pin}'")
        query = f"'{FOLDER_ID}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            fields="files(id, name, webContentLink)"
        ).execute()
        files = results.get('files', [])
        print("Alle Dateien im Google-Drive-Ordner:")
        for f in files:
            print("  -", f.get("name", ""))
        matches = []
        for f in files:
            fname = f.get("name", "")

            # ⛔️ Ignoriere Dateien, die mit "." oder "._" beginnen (macOS-Dateien)
            if fname.startswith(".") or fname.startswith("._"):
                print(f"Ignoriere Datei: {fname}")
                continue

            print(f"Check: '{fname}'  name={name} pin={pin}")
            name_in_file = name.lower().strip() in fname.lower()
            pin_in_file = pin.strip() in fname
            print(f"   -> name_in_file={name_in_file}, pin_in_file={pin_in_file}")

            if name_in_file and pin_in_file:
                matches.append((fname, f['id']))
        print(f"Gefundene Matches: {[m[0] for m in matches]}")
        return matches
    except Exception as e:
        print("Fehler bei Google Drive:", e)
        return []

def get_share_link(file_id):
    service = get_drive_service()
    permission = {
        "type": "anyone",
        "role": "reader"
    }
    try:
        service.permissions().create(fileId=file_id, body=permission, fields="id").execute()
        file = service.files().get(fileId=file_id, fields="webViewLink").execute()
        return file.get("webViewLink")
    except Exception as e:
        print("Fehler beim Link erzeugen:", e)
        return None

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        pin = request.form.get("pin", "").strip()
        try:
            files = list_drive_videos(name, pin)
            links = []
            for fname, fileid in files:
                url = get_share_link(fileid)
                if url:
                    links.append((fname, url))
        except Exception as e:
            flash(f"Fehler bei der Google-Drive-Abfrage: {e}", "danger")
            return redirect(url_for("index"))

        if links:
            return render_template("results.html", matches=links)
        else:
            flash("Kein passendes Video gefunden.", "danger")
            return redirect(url_for("index"))
    return render_template("form.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
