from flask import Flask, request, render_template, redirect, url_for, flash
import os
import requests

# === pCloud-Konfiguration ===
PCLOUD_TOKEN = os.getenv("PCLOUD_TOKEN")
PCLOUD_API = "https://eapi.pcloud.com"
FOLDER_PATH = "/glam4you/g4y_export"

app = Flask(__name__)
app.secret_key = "supersecretkey"

def list_pcloud_videos():
    """Listet alle Dateien im glamour4you-Export-Ordner auf."""
    url = f"{PCLOUD_API}/listfolder"
    params = {
        "access_token": PCLOUD_TOKEN,
        "path": FOLDER_PATH
    }
    r = requests.get(url, params=params)
    result = r.json()
    if result.get("result") != 0:
        raise Exception(f"pCloud API Fehler: {result.get('error', result)}")
    return result.get("metadata", {}).get("contents", [])

def get_public_link(fileid):
    """Erstellt einen neuen Public-Link oder holt den bestehenden."""
    url = f"{PCLOUD_API}/publink/create"
    params = {
        "access_token": PCLOUD_TOKEN,
        "fileid": fileid
    }
    r = requests.get(url, params=params)
    result = r.json()
    if result.get("result") != 0:
        raise Exception(f"pCloud PublicLink Fehler: {result.get('error', result)}")
    return result.get("link")

def filter_files(files, name, pin):
    """Filtert nach Name und PIN im Dateinamen."""
    matches = []
    for f in files:
        fname = f.get("name", "")
        if fname.lower().startswith(name.lower()) and pin in fname:
            matches.append((fname, f["fileid"]))
    return matches

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        pin = request.form.get("pin", "").strip()

        try:
            files = list_pcloud_videos()
            hits = filter_files(files, name, pin)
            links = []
            for fname, fileid in hits:
                url = get_public_link(fileid)
                links.append((fname, url))
        except Exception as e:
            flash(f"Fehler bei der pCloud-Abfrage: {e}", "danger")
            return redirect(url_for("index"))

        if links:
            return render_template("results.html", matches=links)
        else:
            flash("Kein passendes Video gefunden.", "danger")
            return redirect(url_for("index"))
    return render_template("form.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
