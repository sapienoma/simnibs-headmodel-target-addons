# Dependencies and reproducibility

Use the Python environment supplied by the installed SimNIBS 4.6 distribution. A generic pip-installed Python is not a replacement for that environment. Install dcm2niix separately and select its executable in Builder.

Observed Python integrations include SimNIBS, PyQt5, PyOpenGL, NumPy, SciPy, nibabel, Matplotlib and optional brainnet resource lookup. Scalp repair also uses SimpleITK and scikit-image. The existing scalp_repair/requirements.txt records its version ranges and is retained unchanged.

Use the scalp-repair first-run installation interface as described in the application instructions. There is no newly added root requirements.txt: installing a broad replacement dependency set could disturb the SimNIBS-managed environment.

The suite is not a locked/reproducible Python environment. For a validated Windows installation, record Windows version, SimNIBS version, converter version and the installed package versions with the acceptance results. External downloads are not included in this archive.
