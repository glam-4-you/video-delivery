from flask import Flask, request, render_template, redirect, url_for, flash
import os
import dropbox
from dropbox.files import FileMetadata
import sys
import requests
import json
import datetime
from io import BytesIO

# === Konfiguration ===
APP_KEY = os.getenv("DROPBOX_APP_KEY")
APP_SECRET = os.getenv("DROPBOX_APP_SECRET")
REFRESH_TOKEN = os.getenv("DROPBOX_REFRESH_TOKEN")

# === Access Token erzeugen ===
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

# === Dropbox-Client ===
access_token = get_access_token()
db = dropbox.Dropbox(access_token)

# === Flask App ===
app = Flask(__name__)
app.secret_key = "supersecretkey"

# === Konstanten ===
LINK_FOLDER = "/Apps/glam4you_Videos/Links"
DAYS_TO_KEEP = 7

def load_cached_links():
    """Lädt alle links-*.json Dateien der letzten 7 Tage aus Dropbox."""
    cached_links = {}
    today = datetime.date.today()
    try:
        res = db.files_list_folder(LINK_FOLDER)
        for entry in res.entries:
            if isinstance(entry, FileMetadata) and entry.name.startswith("links-") and entry.name.endswith(".json"):
                try:
                    date_str = entry.name[6:-5]  # links-YYYY-MM-DD.json
                    file_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
                    if (today - file_date).days <= DAYS_TO_KEEP:
                        _, res = db.files_download(entry.path_lower)
                        data = json.load(res.raw)
                        cached_links.update(data)
                except Exception as parse_err:
                    print(f"⚠️ Konnte Datei {entry.name} nicht verarbeiten: {parse_err}", file=sys.stderr)
    except Exception as e:
        print(f"⚠️ Fehler beim Laden von Link-Dateien: {e}", file=sys.stderr)
    return cached_links

def save_today_links(today_links):
    """Ergänzt das heutige JSON in Dropbox (anstatt es zu überschreiben)."""
    today_str = datetime.date.today().isoformat()
    filename = f"links-{today_str}.json"
    path = f"{LINK_FOLDER}/{filename}"
    try:
        existing_data = {}
        try:
            _, res = db.files_download(path)
            existing_data = json.load(res.raw)
        except dropbox.exceptions.ApiError as e:
            if e.error.get_path().is_not_found():
                print(f"ℹ️ Keine bestehende Datei gefunden, erstelle neue: {filename}", file=sys.stderr)
            else:
                raise

        existing_data.update(today_links)
        json_bytes = json.dumps(existing_data, indent=2).encode("utf-8")
        db.files_upload(json_bytes, path, mode=dropbox.files.WriteMode.overwrite)
        print(f"✅ Ergänzte Link-Datei: {filename}", file=sys.stderr)
    except Exception as e:
        print(f"❌ Fehler beim Speichern von {filename}: {e}", file=sys.stderr)

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

def force_direct_download(url):
    if url.endswith("dl=0"):
        return url[:-1] + "1"
    return url

def search_dropbox_videos(name, pin):
    folder_path = "/Apps/glam4you_Videos"
    link_cache = load_cached_links()
    today_links = {}
    found_links = []
    try:
        result = db.files_list_folder(folder_path)
        entries = list(result.entries)
        while result.has_more:
            result = db.files_list_folder_continue(result.cursor)
            entries.extend(result.entries)

        for entry in entries:
            if isinstance(entry, FileMetadata):
                fname = entry.name
                name_match = fname.lower().startswith(name.lower())
                pin_match = pin in fname
                if name_match and pin_match:
                    if fname in link_cache:
                        url = force_direct_download(link_cache[fname])
                        found_links.append((fname, url))
                    else:
                        try:
                            link_meta = db.sharing_create_shared_link_with_settings(entry.path_lower)
                            url = force_direct_download(link_meta.url)
                            found_links.append((fname, url))
                            today_links[fname] = url
                        except dropbox.exceptions.ApiError as e:
                            if e.error.is_shared_link_already_exists():
                                try:
                                    error_info = e.error.get_shared_link_already_exists()
                                    if hasattr(error_info, "metadata") and hasattr(error_info.metadata, "url"):
                                        url = force_direct_download(error_info.metadata.url)
                                        found_links.append((fname, url))
                                        today_links[fname] = url
                                except Exception as inner:
                                    print(f"⚠️ Konnte URL aus shared_link_already_exists nicht extrahieren: {inner}", file=sys.stderr)
                            else:
                                print(f"❌ Fehler beim Erzeugen des Links für {fname}: {e}", file=sys.stderr)

        if today_links:
            save_today_links(today_links)

    except Exception as e:
        print(f"Dropbox-Fehler: {e}", file=sys.stderr)

    return found_links

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
