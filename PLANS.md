# Wakey Wakey lil bro: Drowsiness Detector — milestone plan

## Milestone 1 (implemented)

- Build a local-only PySide6 window.
- Read webcam frames with OpenCV on a timer.
- Detect face landmarks with MediaPipe Face Landmarker.
- Display the camera image, eye landmarks, both EAR values, calibration controls, and a clear status.
- Use a time-based eye-closure state machine so short blinks do not trigger an alert.
- Handle a missing model, camera, or face without crashing.
- Keep tests focused on the closure state machine; camera hardware is tested manually.

## Milestone 2 (implemented, manual preview)

- Topmost overlay on all screens until mouse/key input, with a 15-second maximum and cancelled delayed playback on dismissal.
- Desktop glitch held in memory briefly; half-second rush, larger monster, eye flicker, shake, grain, VHS bands, and uneven white/red/black flashes.
- Creepster horror font with OFL license and a custom font picker.
- Random assets from Characters and Backgound Music folders, configurable backgrounds.
- One background source (original procedural bed or selected music), cached stereo speech delayed by two seconds.
- Editable enabled phrases, maximum 80 characters, no consecutive repeats; all disabled means no voice.
- Placeholders such as `{app}` supported; unresolved phrases skipped.
- Worker-thread synthesis, text/voice/effect cache hashes, and stale-result protection.
- QListWidget phrase editor, recording overrides, unsaved voice preview, and stable phrase ids.
- Preferences in APPDATA/WakeyMonster/config.json with migration; default phrases in JSON and cached audio beside config.
- Real time placeholder prepared in advance; other unknown facts skipped. Detection stays independent.

## Milestone 3 (implemented)

- Connected sustained closure to one scene with cooldown and open-eye rearming.
- Camera reads/inference run on a worker; Stop cancels pending scene/audio.
- Clean Monitor, Scene studio and Privacy tabs plus Test scare.
- Real foreground title and closure seconds supply contextual phrases.
- All playable phrases visible; all disabled means no voice, without hidden fallback.
- All 15 requested lines, Windows executable, CI, short README and 60-second synthetic demo.
- Public GitHub: Salman-a-gamer/Wakey-Wakey-lil-bro.

## Desktop polish (implemented)

- Shared branding and generated PNG/ICO app icon.
- Optional configurable Windows global scare shortcut with conflict detection.
- Select/unselect all phrases, optional local name context and editable account-name autofill.
- Writable default monster/background/music folders and original CC0 BGM.
- Targeted inference packaging, no private media or optional training/server/dev tools.
- Camera inference capped at 15 fps; elapsed-time detection remains unchanged.

## Release preparation (remaining)

- Follow docs/release-readiness.md: clean-PC/hardware tests, cache/CPU/RAM soak tests,
  license/model notices, pinned builds, versioning, signing/installer strategy and release ZIP.
- Stronger calibration/pose handling and voice performance remain future improvements.
