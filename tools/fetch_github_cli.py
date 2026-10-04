"""Fetch a portable GitHub CLI into the ignored .tools folder."""
import io
import json
from pathlib import Path
import urllib.request
import zipfile
root = Path(__file__).resolve().parents[1] / '.tools'
root.mkdir(exist_ok=True)
with urllib.request.urlopen('https://api.github.com/repos/cli/cli/releases/latest', timeout=30) as response:
    release = json.load(response)
asset = next(asset for asset in release['assets'] if asset['name'].endswith('windows_amd64.zip'))
with urllib.request.urlopen(asset['browser_download_url'], timeout=60) as response:
    archive = zipfile.ZipFile(io.BytesIO(response.read()))
name = next(name for name in archive.namelist() if name.endswith('/bin/gh.exe') or name == 'bin/gh.exe')
(root / 'gh.exe').write_bytes(archive.read(name))
print('Portable GitHub CLI:', release['tag_name'])
