# SimNIBS Headmodel & Target Add-ons

Companion Windows tools for DICOM conversion, SimNIBS head-model workflows, reviewed hybrid scalp repair, EEG landmarks and scalp-based targeting.

**Public release:** 1.0.0-rc.1 (release candidate). **License:** [GPL-3.0-only](LICENSE).
Independent companion project; not an official SimNIBS distribution.

## Download and requirements

Open **Releases** on this repository and download `simnibs-headmodel-target-addons-v1.0.0-rc.1.zip` from the release assets. Extract the complete archive before launching.

- Windows 10/11 and an installed [SimNIBS 4.6](https://simnibs.github.io/simnibs/) environment.
- [dcm2niix](https://github.com/rordenlab/dcm2niix/releases) for DICOM conversion.
- Additional scalp-repair dependencies installed through the first-run interface; see [dependencies](DEPENDENCIES.md).

SimNIBS, dcm2niix, Python environments, model weights and patient data are not included. This is a source-based toolkit with launch scripts, not a standalone EXE installer.

## Quick start

1. Extract all files to a folder such as `C:\SimNIBS_Tools` and keep the directory structure intact.
2. Start `Start_Builder.vbs` for conversion/model workflows or `Start_Cz_Tool.vbs` for targeting and distances.
3. If prompted, select `<SimNIBS installation>\simnibs_env\python.exe`.
4. Select your own DICOM folder, output root and converter. Suggested defaults are `C:\SimNIBS_Data\DICOM`, `C:\SimNIBS_Data\Projects` and `C:\dcm2niix.exe`; all are editable. Preferences are saved per Windows user.
5. For startup diagnosis, use `start_builder.bat` or `start_cz_tool.bat` inside the corresponding application folder. These diagnostic launchers display a console.

English is the default UI language; Traditional Chinese is available. Tool-generated runtime messages use English. See [setup guide](Getting_Started.html), [detailed English Builder guide](DICOM_to_SimNIBS_m2m_Builder_v1.80.2/README_EN.txt) and [Cz tool guide](SimNIBS_Cz_distance_tool_v2.4.2/README_EN.txt).

## Features

- DICOM-to-NIfTI conversion and sequence inspection; CHARM workflow management.
- Reviewed manual-mask import and hybrid scalp surfaces, preserving original geometry outside the repair region.
- EEG landmark recomputation and selection of original/repaired scalp and EEG assets.
- Subject-specific MNI projection and scalp measurements relative to Cz, with BEAM/SPG method outputs.

See [manual-mask instructions](SimNIBS_Cz_distance_tool_v2.4.2/MANUAL_MASK_WORKFLOW_EN.txt), [Traditional Chinese instructions](SimNIBS_Cz_distance_tool_v2.4.2/MANUAL_MASK_WORKFLOW.txt) and [target/method references](SimNIBS_Cz_distance_tool_v2.4.2/Targets_and_Methods.html).

## Validation and limitations

This release candidate awaits clean-machine Windows acceptance. Read [current validation](RELEASE_AUDIT.md) and [Windows checklist](WINDOWS_ACCEPTANCE.md). Historical test records are consolidated in [development validation](docs/HISTORICAL_VALIDATION.json); they are not new Windows execution results.

A repaired scalp is a localization surface: importing it and an EEG CSV does not reconstruct or validate the existing volume FEM. Review segmentation, geometry and matching coordinate spaces before using results. Target lists and distances are model-dependent research aids, not validated clinical treatment prescriptions.

## Version history

First public version: 1.0.0-rc.1, based on internal Suite 1.80.2 distribution revision 4, Builder 1.80.2 and Cz Tool 2.4.2. Internal application versions remain for traceability. See [changelog](CHANGELOG.md).

The Builder's `target_tool` folder is required by its integrated launcher. Its overlap with the standalone Cz tool is intentional; do not delete it from the distributed suite.

## License and contributions

Toolkit contributions are licensed under [GNU GPL version 3 only](LICENSE). See [distribution/source instructions](DISTRIBUTION.md), [license scope](LICENSE_STATUS.md) and [third-party notices](THIRD_PARTY_NOTICES.md). External components retain their own terms; historical code provenance is not independently certified.

For bug reports, use the repository's Issues tab. Include versions and redacted errors; do not upload patient images, head models, patient EEG coordinates or unredacted logs. See [contribution guide](CONTRIBUTING.md).
