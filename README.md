# Drowsiness Detector — WakeyMonster

A Windows desktop app that detects sustained eye closure and wakes you with a customizable monster scene. Python, OpenCV, MediaPipe, PySide6, and local Piper speech.

![Desktop UI](docs/screenshots/desktop.png)

## Run

Python 3.13, Windows, and a webcam are required for monitoring. Test scare works without a camera.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python tools/setup_models.py
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python -m drowsy_guard
```

Choose your laptop camera, start monitoring, and calibrate with eyes fully open. Short blinks are ignored. Sustained closure triggers one scare; eyes must reopen and the cooldown must finish before another. Move the mouse or press any key to dismiss; every scene ends within 15 seconds. Music begins after half a second; speech after two seconds.

**Scene studio** shows every phrase. Add/edit/delete, enable/disable, preview a draft before saving, or attach your own recording. **All phrases unchecked means music and visuals only**; no hidden phrases are substituted. A single enabled phrase alternates with a silent scene to avoid consecutive repeats.

The [15 requested phrases](docs/phrases.md) support `{time}`, `{app}`, and `{seconds}` (`{closed_seconds}` is an alias). The Windows foreground title supplies app context; actual observed closure supplies seconds. Unknown values are skipped. New contextual speech is prepared asynchronously before the scene opens; nothing freezes while Piper runs.

## Privacy

Everything runs on the PC. **No webcam video is saved or uploaded.** Temporary desktop-glitch pixels are discarded in memory. Foreground titles have no activity log, although locally cached speech can contain a title. Configuration and WAVs live in `%APPDATA%/WakeyMonster/`. Model setup downloads files; normal operation needs no internet.

## Desktop build and demo

```powershell
.\.venv\Scripts\python -m pip install -r requirements-build.txt
.\.venv\Scripts\python tools/build_app.py
```

Launch `dist/WakeyMonster/WakeyMonster.exe`; keep the whole folder together. Models are bundled, so Python is not required on the destination Windows PC. [60-second demo](demo/demo-60s.mp4) uses simulated eye readings and real UI/overlay rendering; it records no personal webcam or desktop. Recreate it with `tools/make_demo.py`.

## Checks

```powershell
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python -m unittest discover -s tests -v
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python tests/scene_smoke.py
.\.venv\Scripts\python tests/desktop_smoke.py
Remove-Item Env:QT_QPA_PLATFORM
```

See [manual checks and file guide](docs/development.md), [demo pitch](demo/pitch.md), and [asset/dependency notices](THIRD_PARTY.md). Physical camera, sound, and multi-monitor behavior require manual checks. This is a hackathon prototype; it has not been medically validated.
