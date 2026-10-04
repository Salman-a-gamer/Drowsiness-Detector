# Repository Guidelines

## Structure

Application modules live in `src/drowsy_guard/`. `app.py` integrates the desktop UI, `camera.py` performs worker-thread inference, `detection.py` calculates EAR, `monitoring.py` gates scares, `activity.py` reads local foreground titles, and `scene.py` manages the studio and audio. `overlay.py`, `speech.py`, `soundscape.py`, `config.py`, and `scene_input.py` handle their respective concerns. Tests live in `tests/`, models in `models/`, defaults/fonts in `assets/`, documentation in `docs/`, and the synthetic demo in `demo/`.

User assets in `Characters/` and `Backgound Music/` stay local; preserve filenames. Runtime config is `%APPDATA%/WakeyMonster/config.json`, with generated WAVs in its `cache/speech/` subfolder. Earlier `settings/scene.json` migrates without modifying the original. Tests use isolated workspace directories. Update this guide when structure or commands change.

## Commands

Prerequisites: Windows and Python 3.13. Use PowerShell in the root; quote paths with spaces. Inspect with `Get-ChildItem -Force`. No formatter/linter is configured.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python -m pip install -r requirements.txt
.\.venv\Scripts\python tools/setup_models.py
$env:PYTHONPATH = "$PWD\src"
.\.venv\Scripts\python -m drowsy_guard
.\.venv\Scripts\python -m unittest discover -s tests -v
```

The toolchain is OpenCV, MediaPipe, PySide6, NumPy, Piper, mss and unittest. Font refresh: `.\.venv\Scripts\python tools/fetch_font.py`. Piper requires matching .onnx and .onnx.json files.

```powershell
.\.venv\Scripts\python -m pip install -r requirements-build.txt
.\.venv\Scripts\python tools/build_app.py
.\.venv\Scripts\python tools/make_demo.py
.\.venv\Scripts\python tools/make_readme_preview.py
```

The desktop build is `dist/DrowsinessDetector/DrowsinessDetector.exe`; preserve the entire folder. Build uses PyInstaller windowed onedir mode. Demos use simulated eye readings and original/generated media, never a personal webcam recording. README preview is a six-second GIF/MP4 with 1.5 seconds of the home UI then the scare. Portable GitHub CLI may live in ignored `.tools/`. Public repo: Salman-a-gamer/Drowsiness-Detector.

## Style and invariants

Use four-space indentation, snake_case functions/modules and PascalCase classes. Keep pure logic separate from widgets. Use descriptive lowercase asset names for new files and preserve existing ones. Generate speech/effects on workers, never during scare playback. Camera reads and inference run on a QThread. Store phrases as JSON, display every playable phrase, and never inject hidden fallback speech. All disabled means no voice. Cooldown requires reopening eyes. Stop cancels pending scene/audio, and dismissal stops every scene timer/player.

Webcam frames are processed locally without recording/upload. Desktop glitch pixels remain in memory briefly. Key state polling never logs keys. Window titles remain local without an activity history, though contextual WAVs can contain them; disclose that in privacy docs. Unknown placeholder facts are skipped. `{seconds}` aliases actual `{closed_seconds}`. Keep asset licenses and avoid uploading user recordings/music/images or credentials.

## Testing

Startup camera scan must run off the UI thread. Keep at least four phrase rows visible and let short/high-DPI windows scroll instead of squeezing controls. Play exactly one background source plus speech; never mix selected BGM with the procedural fallback. Voice effect version changes must invalidate cache hashes.

Use unittest test_*.py for timing, cooldown, migration, phrase selection, cache invalidation and audio. No coverage threshold. Run offscreen integration checks with PYTHONPATH set:

```powershell
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python tests/scene_smoke.py
.\.venv\Scripts\python tests/desktop_smoke.py
Remove-Item Env:QT_QPA_PLATFORM
```

The executable supports `--self-test --data-dir <isolated workspace folder>` with QT_QPA_PLATFORM=offscreen; inspect self-test.json. Actual camera, speaker quality, mixed DPI and Windows focus behavior require manual checks. Preserve sources on failed builds, report limits honestly, and don't claim synthetic demo input is real hardware testing.

## Git and contributions

Git is initialized on main. Use concise imperative commits. Keep changes focused and PR descriptions concrete, with validation and screenshots when useful. Stage source, tests, original fallback assets, licensed fonts, docs and the synthetic demo. Virtual environments, models, build output, local config/cache, user media and portable CLI binaries are ignored. Credentials must never enter commits.
