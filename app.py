# app.py
from flask import Flask, request, render_template, redirect, url_for, flash
import os
import dropbox
from dropbox.files import FileMetadata
import sys
import requests

# === Konfiguration über Umgebungsvariablen ===
APP_KEY = os.getenv("DROPBOX_APP_KEY")
APP_SECRET = os.getenv("DROPBOX_APP_SECRET")
REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN")

# === Access Token aus Refresh Token erzeugen ===
def get_access_token():
    token_url = "https://api.dropbox.com/oauth2/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": REFRESH_TOKEN,
        "client_id": APP_KEY,
        "client_secret": APP_SECRET
    }
    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        return response.json()["access_token"]
    except Exception as e:
        print("❌ Fehler beim Erzeugen des Access Tokens:", e, file=sys.stderr)
        raise

# === Dropbox-Client initialisieren ===
access_token = get_access_token()
db = dropbox.Dropbox(access_token)

# Flask-App
app = Flask(__name__)
app.secret_key = "supersecretkey"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        pin = request.form.get("pin", "").strip()

        matches = search_dropbox_videos(name, pin)

        if matches:
            return render_template("results.html", matches=matches)
        else:
            flash("Kein passendes Video gefunden.", "danger")
            return redirect(url_for("index"))

    return render_template("form.html")


def search_dropbox_videos(name, pin):
    """
    Sucht im Ordner 'Apps/glam4you_Videos' nach Videos, die mit dem Namen anfangen
    und den PIN enthalten. Gibt eine Liste von (Dateiname, Link)-Tuples zurück.
    """
    found_links = []
    folder_path = "/Apps/glam4you_Videos"
    try:
        acc = db.users_get_current_account()
        print(f"✅ Verbunden mit Dropbox-Konto: {acc.name.display_name}", file=sys.stderr)
        print(f"Suche in Dropbox-Ordner: {folder_path} nach Name='{name}', PIN='{pin}'", file=sys.stderr)

        result = db.files_list_folder(folder_path)
        entries = list(result.entries)
        while result.has_more:
            result = db.files_list_folder_continue(result.cursor)
            entries.extend(result.entries)

        print("Gefundene Einträge:", file=sys.stderr)
        matching_entries = []

        for entry in entries:
            if isinstance(entry, FileMetadata):
                fname = entry.name
                name_match = fname.lower().startswith(name.lower())
                pin_match = pin in fname
                print(f" - {fname}\n   -> name_match={name_match}, pin_match={pin_match}", file=sys.stderr)
                if name_match and pin_match:
                    matching_entries.append(entry)

        for entry in matching_entries:
            try:
                links = db.sharing_get_shared_links(path=entry.path_lower).links
                if links:
                    url = links[0].url
                else:
                    link_meta = db.sharing_create_shared_link_with_settings(entry.path_lower)
                    url = link_meta.url

                url = url.replace("?dl=0", "?dl=1")
                found_links.append((entry.name, url))

            except dropbox.exceptions.ApiError as e:
                if e.error.is_shared_link_already_exists():
                    try:
                        url = e.error.get_shared_link_already_exists().url
                        url = url.replace("?dl=0", "?dl=1")
                        found_links.append((entry.name, url))
                    except Exception as inner:
                        print(f"⚠️ Konnte URL aus shared_link_already_exists nicht extrahieren: {inner}", file=sys.stderr)
                else:
                    print(f"Fehler beim Link-Generieren für {entry.name}: {e}", file=sys.stderr)

        print(f"Matches: {found_links}", file=sys.stderr)
    except Exception as e:
        print("Dropbox-Fehler:", e, file=sys.stderr)
    return found_links

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
