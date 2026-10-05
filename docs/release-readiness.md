# Before a public binary release

The current build is a tested prototype, not yet a production release. The repo
contains the source and demos; no release binary has been published.

1. Test on a clean Windows PC without Python: camera scanning, front camera,
   calibration, closure, tracking loss, audio files, shortcuts/conflicts, restart,
   mixed DPI, multiple monitors, and Stop while audio prepares.
2. Measure startup time, idle/detection CPU, RAM, and cache growth over a long run.
   Keep the required inference libraries; verify model inference and real audio
   after every packaging reduction. Add a cache size policy before a broad release.
3. Decide the application license and include dependency licenses/model cards.
   Piper is GPL-3.0; Qt and voice/model redistribution terms must be addressed.
   Use only original/appropriately licensed defaults, never private FNAF/user media.
4. Pin the tested dependency versions, assign a version, and prepare a reproducible
   release build, checksums, changelog, and installation/uninstall instructions.
5. Add Windows executable metadata and consider code signing so users can verify
   the publisher. Do not imply that an unsigned prototype is a signed installer.
6. Publish a tagged GitHub release with the complete app folder in a ZIP only
   after these checks pass. Keep configuration in app data across upgrades.

## Old folders

`dist/WakeyMonster` and `dist/DrowsinessDetector` are generated older builds.
They can be removed after the replacement is manually verified and any media
referenced inside them is copied into the writable asset folders. Keep the source
checkout, models, and settings. The sibling `Drowsiness Detection Project` folder
contains a different OpenCV/dlib prototype; do not treat it as a duplicate checkout.

## Current optimization evidence

The uncompressed folder decreased from 536.2 MiB to 526.4 MiB. Most remaining
weight is required OpenCV/Qt/inference libraries and the voice model. Optional
training/server/dev modules and private media are excluded. Matplotlib/Pillow
remain because MediaPipe imports them. Only the contrib OpenCV wheel is installed;
MediaPipe requires it. The camera worker caps inference at 15 fps and continues
using monotonic timestamps for closure detection; real camera delivery/inference
was checked. This is not yet a CPU/RAM benchmark or long-duration soak test.
