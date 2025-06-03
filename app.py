from flask import Flask, request, render_template, redirect, url_for, flash
import os
import pickle
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ['https://www.googleapis.com/auth/drive']
CREDENTIALS_FILE = "credentials.json"
TOKEN_FILE = "token.pickle"
FOLDER_ID = "1zO2qTb3CBj10M9SZycJCVFKbIgvCSBpE"  # <--- WICHTIG: hier die ID deines Google Drive Zielordners eintragen!

app = Flask(__name__)
app.secret_key = "supersecretkey"

def get_drive_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, 'rb') as token:
            creds = pickle.load(token)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(TOKEN_FILE, 'wb') as token:
            pickle.dump(creds, token)
    return build('drive', 'v3', credentials=creds)

def list_drive_videos(name, pin):
    service = get_drive_service()
    try:
        query = f"'{FOLDER_ID}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            fields="nextPageToken, files(id, name, webViewLink, webContentLink, mimeType)"
        ).execute()
        files = results.get('files', [])
        # Filter nach Name & PIN im Dateinamen (wie vorher!)
        matches = []
        for f in files:
            fname = f.get("name", "")
            if fname.lower().startswith(name.lower()) and pin in fname:
                # Freigabelink erzeugen
                matches.append((fname, f['id']))
        return matches
    except HttpError as e:
        print("Fehler bei Google Drive:", e)
        return []

def get_share_link(file_id):
    service = get_drive_service()
    # Freigabe einstellen: Jeder mit Link kann herunterladen
    permission = {
        "type": "anyone",
        "role": "reader"
    }
    try:
        service.permissions().create(fileId=file_id, body=permission).execute()
        # Hole WebContentLink (direkter Downloadlink)
        file = service.files().get(fileId=file_id, fields="webContentLink").execute()
        return file.get("webContentLink")
    except HttpError as e:
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
