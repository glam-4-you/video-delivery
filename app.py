# app.py
from flask import Flask, request, render_template, redirect, url_for, flash
import os
import dropbox
from dropbox.files import FileMetadata
import sys

# === Konfiguration ===
DROPBOX_TOKEN = os.getenv("DROPBOX_TOKEN")

# Dropbox-Client initialisieren
if not DROPBOX_TOKEN:
    raise ValueError("DROPBOX_TOKEN is not set")
db = dropbox.Dropbox(DROPBOX_TOKEN)

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
    Listet alle Dateien im Ordner 'Apps/glam4you_Videos' auf,
    und filtert nach Name (am Dateianfang) und PIN.
    Gibt eine Liste von (Dateiname, Link)-Tuples zurück.
    """
    found_links = []
    folder_path = "/Apps/glam4you_Videos"
    try:
        # Verbindungscheck
        try:
            acc = db.users_get_current_account()
            print(f"✅ Verbunden mit Dropbox-Konto: {acc.name.display_name}", file=sys.stderr)
        except Exception as e:
            print(f"❌ Keine Verbindung zu Dropbox: {e}", file=sys.stderr)

        # Debug-Ausgabe der Suchparameter
        print(f"Suche in Dropbox-Ordner: {folder_path} nach Name='{name}', PIN='{pin}'", file=sys.stderr)

        # Dateien im spezifischen Ordner auflisten (nicht rekursiv)
        result = db.files_list_folder(folder_path)
        entries = list(result.entries)
        while result.has_more:
            result = db.files_list_folder_continue(result.cursor)
            entries.extend(result.entries)

        # Debug-Ausgabe aller Einträge
        print("Gefundene Einträge:", file=sys.stderr)
        for entry in entries:
            if isinstance(entry, FileMetadata):
                fname = entry.name
                print(f" - {fname}", file=sys.stderr)
                # Prüfungen
                name_match = fname.lower().startswith(name.lower())
                pin_match = pin in fname
                print(f"   -> name_match={name_match}, pin_match={pin_match}", file=sys.stderr)
                if name_match and pin_match:
                    try:
                        links = db.sharing_get_shared_links(path=entry.path_lower).links
                        if links:
                            url = links[0].url
                        else:
                            link_meta = db.sharing_create_shared_link_with_settings(entry.path_lower)
                            url = link_meta.url
                        url = url.replace("?dl=0", "?dl=1")
                        found_links.append((fname, url))
                    except Exception as e:
                        print(f"Fehler beim Link-Generieren für {fname}: {e}", file=sys.stderr)

        # Debug-Ausgabe der Treffer
        print(f"Matches: {found_links}", file=sys.stderr)
    except Exception as e:
        print("Dropbox-Fehler:", e, file=sys.stderr)
    return found_links

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
