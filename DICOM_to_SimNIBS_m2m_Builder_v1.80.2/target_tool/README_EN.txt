Runtime logs, progress, elapsed-time notifications and tool-generated errors use English regardless of UI language. Existing language choices are retained; new users default to English. Third-party output and user paths are passed through unchanged.

This standalone Cz folder: Start_Cz_Tool.vbs. DICOM conversion requires the separate Builder package.

DISTRIBUTION REVISION 2 — NEW COMPUTER SETUP
Application versions: Builder 1.80.2 / Cz tool 2.4.2. Geometry algorithms are unchanged.

1. Install SimNIBS 4.6 on EACH Windows 10/11 computer using its own installer.
   Use its bundled simnibs_env\python.exe. Copying this tool ZIP does not install SimNIBS.
   Builder also requires dcm2niix.exe; copy it to C:\dcm2niix.exe or select another location in Builder.
   SimNIBS, dcm2niix, Python environments and model weights are not included in this package.
2. Extract ALL files to a folder you can read, for example C:\SimNIBS_Tools or D:\Tools\SimNIBS_Tools.
   Keep all subfolders together. Do not run directly inside the ZIP or copy only a VBS file.
   Use a writable folder for data/output. Paths containing spaces are quoted by the launchers.
3. Start the appropriate English-named launcher in File Explorer:
   Builder: Start_Builder.vbs. Target/distance tool: Start_Cz_Tool.vbs.
   The suite root contains both; each standalone app contains its own launcher.
   Optional direct scalp-repair launch: scalp_repair\Start_Scalp_Repair.vbs.
   launch_hidden.vbs is an equivalent launcher inside Builder/Cz app folders.
4. Python discovery checks SIMNIBS_PYTHON, saved per-user settings, Program Files, C:\SimNIBS-4.6,
   the current user's SimNIBS-4.6 folder and simnibs_python on PATH. If needed, a file dialog opens.
   Select <your SimNIBS installation>\simnibs_env\python.exe, not a generic Python/Conda installation.
   The launcher verifies that Python can import simnibs and remembers the selection on this computer.
5. In Builder select your DICOM folder, writable output root and dcm2niix.exe.
   Initial suggestions: C:\SimNIBS_Data\DICOM, C:\SimNIBS_Data\Projects and C:\dcm2niix.exe.
   These are editable defaults, not required folders. If C:\ is not writable, select a user-writable
   folder or another drive. Your paths are saved for the next launch. New installations default to English; Traditional Chinese remains selectable.
   In Cz tool, manually select a complete m2m folder; no sample patient is preloaded.
6. Scalp repair: install its optional dependencies using the subtool's first-run button on this computer.
   This step may require internet access. Then load your own T1/T2 or reviewed repair work.
   For existing reviewed work use step 5: leave the cut blank, width 4 mm and a new empty output folder.
   Review the hybrid report and recomputed EEG, then reopen the original m2m to select Hybrid scalp.

SETTINGS AND MOVING TO ANOTHER COMPUTER
Settings are per Windows user, outside the extracted program folder:
  Shared Python/DICOM/output/converter: %LOCALAPPDATA%\SimNIBS_HeadBuilder\settings.json
  Scalp repair preferences/dependencies: %LOCALAPPDATA%\SimNIBS_ScalpRepair
  Cz recent-folder and display preferences: Qt QSettings for this Windows user.
Distribute the program ZIP only, not your AppData, registry preferences, MRI, patient models or environments.
On a new PC, install the dependencies and select local paths again. Do not edit source code to change paths.
Moving the program folder on the same PC works through relative launcher paths; application settings remain.
Move patient projects separately: copy the ENTIRE m2m folder, including repair_assets, EEG and toMNI files.
Repair bindings use relative paths inside m2m. Reviewed-work manifests may still contain absolute source paths;
reselect or recreate that work if referenced source MRI files are unavailable after the move.
Do not put output data inside the program distribution when preparing a ZIP for other users.

TROUBLESHOOTING
- Use start_builder.bat or start_cz_tool.bat to view the startup log if a hidden launcher fails.
- Startup logs: %TEMP%\SimNIBS_HeadBuilder_startup.log, SimNIBS_TargetTool_startup.log,
  or SimNIBS_ScalpRepair_startup.log. Scalp job log: %LOCALAPPDATA%\SimNIBS_ScalpRepair\last_run.log.
- If VBS is disabled by the computer's policy, use the BAT launcher or ask the administrator about scripting support.
  BAT launchers intentionally show a command window; VBS launchers hide it.
- A wrong or removed Python path is skipped; select the installed SimNIBS Python when prompted.
- No simnibs import: choose the correct bundled environment or repair the SimNIBS installation.
- Missing data: check your selected local paths and the extraction structure.
- To reset shared path settings, close all tools and rename settings.json to settings.backup.json.
  This does not delete project data. Clear SIMNIBS_PYTHON if you no longer want that override.

FILES
Getting_Started.html: this setup guide in English and Traditional Chinese.
README_EN.txt / README.txt: detailed English / Traditional Chinese workflows.
Targets_and_Methods.html (Cz): target coordinates, references and measurement-method notes.
All packaged VBS/HTML filenames use ASCII English names. Generated report filenames (review.html,
hybrid_report.html, results.html and charm_report.html) were already English and retain their names.
The bilingual UI and scientific methods are retained. Hybrid scalp is a localization surface; volume FEM is unchanged.


----- DETAILED WORKFLOW -----

SimNIBS Cz distance tool v2.4.2 | SimNIBS Tools Suite v1.80.2
Hybrid scalp v1.80.2
Original T1/m2m scalp remains selectable. Choose Create hybrid scalp, load reviewed repair work,
then Build hybrid scalp + recompute EEG. Select the original full head FEM, reviewed donor PLY/MSH
and anatomical fiducial CSV. The original standard cap provides default fiducials; verify anatomy.
Original lower vertices / fully retained triangles stay unchanged; only the local seam and cap are new.
Automatic cutting searches locally in the superior region; manual RAS Z is not shifted automatically.
After seam checks, EEG is recomputed on the hybrid. Do not reuse the old donor-surface cap as final hybrid EEG.
If imported into the original m2m, reopen it and select Hybrid scalp + recomputed EEG.
Original T1/m2m scalp + original EEG remains available; switching updates the matched cap.
Legacy whole repaired surface bindings remain supported and retain their repaired-surface label.
Review hybrid_report.html, hybrid_preview.png and hybrid_seam.geo. Volume FEM remains unchanged.
See MANUAL_MASK_WORKFLOW.txt / MANUAL_MASK_WORKFLOW_EN.txt for the complete workflow.

Bidirectional scalp switching (Suite / Builder v1.80.2, Cz tool v2.3.0)
Use the Scalp model selector in the Cz panel:
  Original scalp + original EEG: original m2m scalp surface and default EEG cap.
  Repaired scalp + new EEG: imported repaired surface and its matched recomputed cap.
After one import, switch back and forth without importing again. The repaired option is disabled without a pair.
Each m2m remembers its selected mode. Standalone launch remains blank and never auto-opens a subject.
Switching updates scalp display, clicks/normals, TMS placement surface, measurement inputs and the matched EEG.
Current Position, paths and results are cleared. Double-click again or recalculate the MNI target.
Existing TMS table points are not automatically retargeted to a new cap; recheck position, angle and distance.
Gray matter and the volume FEM solver geometry are unchanged. The TES restriction in repaired overlay mode remains.
Triangle count and mean unique edge length compare surface sampling, not source MRI anatomical resolution.
More triangles cannot recover anatomy absent from the original images.


Patch v1.7.1 / Cz v2.2.1 (2026-10-19)
- Extract only tag-1005 triangles; other tissue surfaces are no longer included by OR-style selectors.
- Tiny islands may be removed from the new localization import copy only when their combined area is
  <=50 mm² AND <=0.1% of total scalp area. No vertex movement/welding/bridging; larger components still fail.
- Every EEG point must remain within 3 mm of the retained scalp. Required landmarks keep >=5 mm boundary
  clearance. An EEG point on a discarded island causes failure; it is never silently ignored.
- Source MSH/mask/EEG/FEM are retained. The original FEM reference may contain multiple scalp components
  and is not cleaned. Statistics are recorded in validation.surface_cleanup and shown after successful import.
- Retry the same paired scalp_surface_ONLY.msh and EEG10-10_recomputed.csv. No DICOM/registration/CHARM
  rerun or preliminary EEG recomputation is needed. New failure messages identify the source path and area.
Thresholds are implementation checks, not clinical accuracy specifications.

Windows 10/11; installed SimNIBS 4.6 required. See VERSION.json and VALIDATION.json.

START AND LANGUAGE
Extract all files. Double-click launch_hidden.vbs or Start_Cz_Tool.vbs; use start_cz_tool.bat for troubleshooting.
Startup log: %TEMP%\SimNIBS_TargetTool_startup.log. Uses SimNIBS's Python; first tries SIMNIBS_PYTHON,
the saved Builder Python, Program Files\SimNIBS-4.6 or C:\SimNIBS-4.6, then asks for a path.
This opens a native SimNIBS GUI with the targeting panel; it cannot attach to another running GUI.
Select English under Language / 語言. Manual launch starts blank; load a model or explicitly open the recent m2m.
Builder can explicitly hand off the selected model. Language and recent paths are per user, not embedded patient defaults.

REPAIRED SCALP AND NEW EEG
Load the complete original m2m. Select Import repaired scalp / EEG; choose the same m2m and the paired
scalp_surface_ONLY.msh / EEG10-10_recomputed.csv from the same successful EEG_recomputed_... output.
Verify same subject, scanner RAS mm and anatomy. MNI, LPS and voxel indices are not interchangeable.
Checks include tag 1005, triangle topology/connectivity, required Cz/Nz/Iz/LPA/RPA, all cap-to-scalp residuals
<=3 mm, required-landmark boundary clearance >=5 mm and plausible fiducial alignment to the volume FEM.
Thresholds are software checks, not clinical accuracy specifications; they cannot establish subject identity.
Copies and a normalized one-row-per-name cap are saved in m2m\repair_assets\import_...; repair_binding.json
stores relative paths and hashes. Original volume mesh/default cap are retained. Move the complete m2m together.
Load the m2m again to apply the saved repair. Replaced/edited assets invalidate hashes and require reimport.
Display, scalp clicks, normals and tape measurements use the repaired surface; Cz comes from the new cap.
MNI still uses the full m2m\toMNI warps, not the localization-surface directory.
The Scalp model selector switches both ways without deleting the saved pair; reopening uses the selected mode.
While the repair is active, the native File cap selector cannot replace it independently: import a new reviewed pair.

TMS SIMULATION IN THE NATIVE GUI
The GUI scalp is replaced for localization; session.eeg_cap points to the new cap while fnamehead stays the original FEM.
The native TMS table computes matsimnibs against this repaired surface, including normal, orientation and coil distance.
Run solves fields in the original volume FEM. This updates localization, not missing conductive tissue geometry.
Existing TMS table points are not retargeted automatically; select positions again using the new cap and verify orientation.
TES electrode sessions are blocked in overlay mode because electrodes require a consistent conducting volume mesh.
Save MAT to keep FEM/cap/TMS matrices. Ordinary SimNIBS can read the MAT but does not automatically display this overlay;
use the companion for repaired display. For a repaired volume FEM, use Builder v1.80.2's edited-tissue-label remeshing,
review the new FEM and EEG, then load the new m2m here. Surface-only MSH and CSV cannot restore skull/CSF compartments.

MANUAL MASK WORKFLOW
Builder → T2 scalp repair → load manifest.json → review T1_union/T2_registered_union and the draft binary envelope
→ edit a 0/1 mask on exactly the same union grid → load edited mask and export → verify fiducials in scanner RAS mm
→ recompute EEG → import the paired MSH and CSV here. See MANUAL_MASK_WORKFLOW.txt for full bilingual instructions.
Duplicate Iz: fiducials take priority; conflicting coordinates at equal priority require review.
Remaining non-manifold edges require mask editing. A landmark >5 mm from scalp requires anatomical review on MRI;
nearest-surface projection is only a candidate, not proof of the correct inion.

CURRENT POSITION AND MNI
Select Scalp and double-click. Reads GUI intersect_point directly, not OCR or the TMS table.
The MNI tab offers 12 research targets and blank custom X/Y/Z fields in MNI world mm (RAS).
MNI → native brain using SimNIBS nonlinear warps → nearest triangular scalp point → three measurement methods.
Exports original MNI, native brain, scalp coordinates, projection gap and MNI round-trip error.
This geometric projection is not an optimized electric-field target or an individual functional hotspot.
A complete m2m with toMNI is required for nonlinear transformations. A mesh and CSV alone are insufficient.
Sources and limitations: targets.json, TMS_MNI_targets.csv and the target-method HTML.
Group DLPFC/language/swallowing coordinates do not establish the individual's optimal treatment target.
Swallowing hotspots require individual TMS/MEP localization.

THREE METHODS
1. Cz lateral then anterior/posterior. LPA→RPA defines left/right; Nz→Iz is orthogonalized for the AP axis.
   Follow the scalp section through Cz normal to the AP axis, then the target's parasagittal section to the target.
   The AP section is perpendicular to LPA–RPA, not an EEG network chain and not necessarily an MRI sagittal plane.
2. Generalized BEAM-style X/Y. The circumference plane uses Fpz–Oz and the Nz–Cz–Iz reference plane.
   X runs along head circumference from Fpz toward the target side to the radial footpoint; Y runs from Cz along
   the radial section to the target. This is not the original Beam F3 / adjusted Beam F3 prediction.
   Additional approximate mean F3 references: X≈0.1154 HC; Y≈0.2637 (NI+TT)/2; not the complete Beam algorithm.
3. Individual SGP/CPC. Reference arc Nz→Cz→Iz; active plane through LPA, RPA and target s; upper intersection s′.
   pNZ=(Nz→s′)/(Nz→Cz→Iz); pAL=(LPA→s)/(LPA→s→RPA).
   Reports Nz/Cz→s′ and LPA/RPA→target tape distances in mm/cm. Individual Cz is not forced to 50% of the reference arc.
   These are individual geometric proportions, not the authors' population MNI2CPC probability mapping.
All methods measure plane/scalp intersection arcs, not unrestricted shortest-geodesic XYZ components.
Disconnected sections, inconsistent landmarks or missing coverage cause that method to fail rather than return a straight line.
External MNI2CPC tab accepts authors' tool proportions pNZ/pAL in 0–1, not percent. Verify their correspondence to MNI yourself.

EXPORT
JSON records actual scalp MSH, EEG CSV, volume FEM, geometry mode, coordinates and paths. An additional Electrode CSV
contains native scalp coordinates; do not treat it as MNI and transform again. Displayed paths are lifted 0.4 mm for
visibility only; computed distances remain on the actual scalp. Patient files are not automatically uploaded.

VALIDATION
See VALIDATION.json. Unit and offscreen Qt checks were run; Windows/OpenGL integration, actual nonlinear warps
and a complete electromagnetic solve still require testing in the installed SimNIBS environment.

v1.80.2: tested with the actual uploaded reference case original FEM and reviewed donor
Six original tag-1005 boundary contacts have degree four, 108–130 mm below the selected cut.
Allow existing contacts at least 10 mm below the cut only when their coordinates, complete incident-face stars
and every original boundary edge are preserved exactly. No filling, welding or vertex movement is applied.
Non-manifold edges, duplicate/degenerate faces, disconnected sources and contacts near/above the cut remain rejected.
Original LPA/RPA are about 3 mm from existing boundaries. A fiducial exception requires an identical original
10 mm triangle patch and projection onto the original surface. New/changed boundaries and Cz never receive this exception.
This is a locally verified hybrid, not a claim that the full source scalp has become globally manifold.
Actual-pair test: 1,283 seam triangles, zero open seam attachments, zero seam self-intersections and zero non-manifold seam vertices.
57,376 original whole lower faces and all 876 original boundary edges were preserved.
The stored SimNIBS EEG algorithm produced 91 positions through a mesh-array adapter; native Windows CLI remains untested.
Reload reviewed manifest, leave cut blank, use 4 mm width and a NEW empty output folder, then run step 5.
No conversion/registration/mask rerun is needed. Automatic h=126.7683566815 is an oblique-plane offset, NOT manual RAS Z.
Diagnostics remain in topology_diagnostics.json, topology_boundary_vertices.csv and hybrid_manifest.json.
Original volume FEM, original/hybrid switching and bilingual UI are retained.
