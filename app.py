from flask import Flask, render_template, request, redirect, url_for, flash
from google.oauth2 import service_account
from googleapiclient.discovery import build
import re

app = Flask(__name__)
app.secret_key = "supersecretkey"

SERVICE_ACCOUNT_FILE = "service-account.json"
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]
FOLDER_ID = "1GK0SNOvUuhY6DpfgwCq3b5qA41YmZap4"  # <- Dein Google Drive Ordner

def get_drive_service():
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    return build("drive", "v3", credentials=creds)

def extract_number_from_name(name):
    match = re.search(r"_(\d{2})_", name)
    return int(match.group(1)) if match else 0

def list_drive_videos(name, pin):
    service = get_drive_service()
    try:
        print(f"\nDEBUG: Suche in Google Drive Ordner {FOLDER_ID} nach Name='{name}', PIN='{pin}'")
        query = f"'{FOLDER_ID}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            fields="files(id, name, webViewLink)"
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

        # ✅ Sortiere die Matches nach Nummer im Dateinamen (z. B. _01_)
        matches.sort(key=lambda x: extract_number_from_name(x[0]))

        print(f"Gefundene Matches: {[m[0] for m in matches]}")
        return matches
    except Exception as e:
        print("Fehler bei Google Drive:", e)
        return []

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        pin = request.form.get("pin", "").strip()

        if not name or not pin:
            flash("Bitte gib Name und PIN ein.", "error")
            return redirect(url_for("index"))

        matches = list_drive_videos(name, pin)
        if matches:
            links = []
            for fname, file_id in matches:
                url = f"https://drive.google.com/uc?id={file_id}&export=download"
                links.append((fname, url))
            return render_template("results.html", matches=links)
        else:
            flash("Keine passenden Videos gefunden. Bitte prüfe Name und PIN.", "error")
            return redirect(url_for("index"))

    return render_template("form.html")

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=True)
