"""Create original default audio and convert generated icon to Windows ICO."""
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from drowsy_guard.config import PROJECT
from drowsy_guard.soundscape import build_soundscape


def main():
    for kind in ('monsters', 'backgrounds', 'music', 'icons'):
        (PROJECT / 'assets' / kind).mkdir(parents=True, exist_ok=True)
    shutil.copy2(PROJECT / 'assets/monster.svg', PROJECT / 'assets/monsters/shadow-monster.svg')
    source = build_soundscape(PROJECT / 'cache/default-audio')
    shutil.copy2(source, PROJECT / 'assets/music/midnight-signal.wav')
    image = PROJECT / 'assets/icons/wakey-icon.png'
    if image.exists():
        from PIL import Image
        with Image.open(image) as icon:
            icon.convert('RGBA').save(image.with_suffix('.ico'),
                sizes=[(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
    print('Original default audio and monster prepared; icon converted when present.')


if __name__ == '__main__':
    main()
