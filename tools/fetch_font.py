"""Fetch Creepster and its SIL Open Font License from Google Fonts."""
import urllib.request
from pathlib import Path

folder = Path(__file__).resolve().parents[1] / "assets/fonts"
folder.mkdir(parents=True, exist_ok=True)
for name in ("Creepster-Regular.ttf", "OFL.txt"):
    url = "https://raw.githubusercontent.com/google/fonts/main/ofl/creepster/" + name
    with urllib.request.urlopen(url, timeout=30) as response:
        (folder / name).write_bytes(response.read())
print("Font assets:", [file.name for file in folder.iterdir()])
