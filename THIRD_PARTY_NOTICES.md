# Third-party source and dependency inventory

Updated 2026-10-27. Toolkit contributions are GPL-3.0-only as declared in LICENSE_STATUS.md. This is an inventory, not a complete license-compliance certification. The archive contains companion-tool source and data tables; it does not bundle the external application environments/binaries below. Historical authorship of toolkit functions remains unverified.

| Component | Observed use | Upstream source / license location |
|---|---|---|
| SimNIBS | Python imports, CHARM and eeg_positions CLI | https://github.com/simnibs/simnibs ; LICENSE.txt (upstream identifies GPL v3 / GPL-3.0-only) |
| dcm2niix | External DICOM converter | https://github.com/rordenlab/dcm2niix/blob/master/license.txt (BSD and component-specific terms) |
| PyQt5 | Desktop interface | https://www.riverbankcomputing.com/software/pyqt/ ; use installed distribution's license |
| NumPy | Arrays and geometry | https://github.com/numpy/numpy |
| SciPy | Sparse graphs and numerical methods | https://github.com/scipy/scipy |
| nibabel | NIfTI and image headers | https://github.com/nipy/nibabel |
| SimpleITK | Image registration/resampling | https://github.com/SimpleITK/SimpleITK |
| scikit-image | Mask/surface processing | https://github.com/scikit-image/scikit-image |
| Matplotlib | Plotting | https://github.com/matplotlib/matplotlib |
| PyOpenGL | 3D rendering | https://github.com/mcfletch/pyopengl |
| brainnet | Optional SimNIBS-associated model resource lookup | Resolve from the actual installed SimNIBS environment; no model weights are bundled |
| Python / Tk | Runtime and dialogs | https://www.python.org/ ; use the installed runtime's notices |

The bundled targets.json and TMS_MNI_targets.csv are program target catalogs, not patient EEG coordinates. Their source references are retained in the catalogs and Targets_and_Methods.html. Reference presence is not a new scientific validation or a full content-rights review.

Do not remove notices from external software when installing or redistributing it. If a future package bundles wheels, executables, model weights or copied source, add the exact component versions, full required notices and relevant redistribution terms before shipping it.
