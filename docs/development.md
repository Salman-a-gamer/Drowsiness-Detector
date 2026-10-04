# Development and manual verification

## Files

- `app.py`: dark desktop shell, monitoring controls, activity polling, calibration and trigger integration.
- `camera.py`: OpenCV and MediaPipe on a worker thread; GUI never runs camera reads or inference.
- `detection.py`: pixel-correct EAR and closure timing, independently tested.
- `monitoring.py`: one scene per closure, cooldown after dismissal, and open-eye rearming.
- `scene.py`: phrase list, draft previews, asynchronous audio preparation, scene cancellation and playback.
- `overlay.py`: rush, eye flicker, shake, grain, VHS bands, irregular flashes, temporary in-memory mss capture.
- `speech.py` / `soundscape.py`: hashed stereo Piper speech and synthesized horror sound bed.
- `config.py`: versioned phrase catalog, migration, settings and assets.
- `activity.py`: foreground window title; excludes this app's own windows.

## Behavior

Settings migrate from the earlier project-local config into APPDATA. Version 2 adds all requested phrases without deleting custom phrases. Existing all-disabled preferences remain disabled. Every playable line appears in the list. If no enabled/resolved audio is available, the scene has no speech. When only the previously spoken line is eligible, that scene is silent; the next scene may speak it again.

`{app}` is the latest external foreground window title, shortened to 32 characters to keep lines within 80 characters. `{seconds}` is actual observed closure rounded to one decimal; `{closed_seconds}` is equivalent. Test scare never invents closure duration. Resolved text over 80 characters is skipped. Titles may survive in locally cached audio, which you can delete from APPDATA/WakeyMonster/cache.

Context changes may require fresh speech: that runs in a worker before the overlay begins. Stop cancels pending automatic scares and all scene playback. During a scare, detector updates cannot enqueue another. After dismissal, reopen eyes and wait for cooldown.

## Manual checklist

1. Start on the front camera. Calibrate fully open. Verify EAR and open/closed labels.
2. Blink normally: no scare. Close past the threshold: exactly one scene.
3. Dismiss with any key or mouse movement. Verify no delayed voice returns after dismissal.
4. Hold closed: no repeat. Reopen and wait for cooldown, then close again.
5. Lose tracking or unplug the webcam: timer resets or clear camera error, with responsive UI.
6. Test scare without a webcam. Leave untouched: 15-second maximum; speech starts at 2 seconds.
7. Disable every phrase: visuals/music only. Re-enable one: only that line is ever spoken.
8. Preview an unsaved edit, save, restart, and verify settings. Attach a valid recording.
9. Switch to another app, then close eyes: a relevant title can populate `{app}`. No made-up `{seconds}` in manual previews.
10. Stop while speech prepares: no scene appears later. Check actual speakers and all monitors.

Secure Windows prompts and some exclusive fullscreen apps cannot be covered. Mixed DPI capture placement and actual sound quality need hardware checks. The eye-flicker mask is tuned for the supplied character; other images may need different relative coordinates.

## Exercise

Change cooldown to 5 seconds. Trigger a scare, keep your eyes closed past cooldown, then reopen and close again. Notice how open-eye rearming prevents repeated scares from one closure.
