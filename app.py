# app.py
from flask import Flask, request, render_template, redirect, url_for, flash
import os
import dropbox

# === Konfiguration ===
DROPBOX_TOKEN = os.getenv("DROPBOX_TOKEN")

db = dropbox.Dropbox(DROPBOX_TOKEN)

app = Flask(__name__)
app.secret_key = "supersecretkey"

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        name = request.form["name"].strip()
        pin = request.form["pin"].strip()

        matches = search_dropbox_videos(name, pin)

        if matches:
            return render_template("results.html", matches=matches)
        else:
            flash("Kein passendes Video gefunden.", "danger")
            return redirect(url_for("index"))

    return render_template("form.html")

def search_dropbox_videos(name, pin):
    found_links = []
    try:
        response = db.files_list_folder("/App/glam4you_Videos")
        for entry in response.entries:
            if entry.name.startswith(name) and pin in entry.name and entry.name.endswith(".mp4"):
                shared_link = db.sharing_create_shared_link_with_settings(entry.path_lower)
                url = shared_link.url.replace("?dl=0", "?dl=1")
                found_links.append((entry.name, url))
    except Exception as e:
        print("Dropbox-Fehler:", e)
    return found_links

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
