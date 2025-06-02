import os
import requests
from flask import Flask, request, render_template, redirect, url_for, flash

# App-Config
PCLOUD_USERNAME = os.getenv("PCLOUD_USERNAME")
PCLOUD_PASSWORD = os.getenv("PCLOUD_PASSWORD")
PCLOUD_API = "https://eapi.pcloud.com"
FOLDER_PATH = "/glam4you/g4y_export"

app = Flask(__name__)
app.secret_key = "supersecretkey"

def get_pcloud_token():
    """Holt einen temporären auth-Token mit Username/Passwort."""
    r = requests.get(f"{PCLOUD_API}/userinfo", params={
        "getauth": 1,
        "username": PCLOUD_USERNAME,
        "password": PCLOUD_PASSWORD
    })
    data = r.json()
    if data.get("result") == 0 and "auth" in data:
        return data["auth"]
    raise Exception(f"Kein gültiger pCloud-Token: {data.get('error', data)}")

def list_pcloud_videos(token):
    url = f"{PCLOUD_API}/listfolder"
    params = {
        "access_token": token,
        "path": FOLDER_PATH
    }
    r = requests.get(url, params=params)
    result = r.json()
    if result.get("result") != 0:
        raise Exception(f"pCloud API Fehler: {result.get('error', result)}")
    return result.get("metadata", {}).get("contents", [])

def get_public_link(token, fileid):
    url = f"{PCLOUD_API}/publink/create"
    params = {
        "access_token": token,
        "fileid": fileid
    }
    r = requests.get(url, params=params)
    result = r.json()
    if result.get("result") != 0:
        raise Exception(f"pCloud PublicLink Fehler: {result.get('error', result)}")
    return result.get("link")

def filter_files(files, name, pin):
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
            token = get_pcloud_token()
            files = list_pcloud_videos(token)
            hits = filter_files(files, name, pin)
            links = []
            for fname, fileid in hits:
                url = get_public_link(token, fileid)
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
