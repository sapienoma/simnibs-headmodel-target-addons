# Clean-machine Windows acceptance — NOT YET EXECUTED

Use a new Windows account or computer with no existing toolkit settings. Record date, Windows version, SimNIBS version, dcm2niix version and actual results. Use a consented local test dataset; keep images and detailed output private.

- [ ] Install SimNIBS 4.6 and dcm2niix; extract the complete suite to a path containing spaces.
- [ ] Start each root VBS launcher; confirm hidden console, English initial UI and successful environment selection.
- [ ] If VBS is disabled, confirm the application's BAT diagnostic launcher works.
- [ ] Select DICOM/converter/output locations; close and reopen; verify saved settings.
- [ ] Switch language and restart; confirm the selection persists and runtime messages remain English.
- [ ] Convert DICOM, inspect NIfTI/JSON, select T1 and optional T2, and finish a CHARM job.
- [ ] Confirm completion dialog, elapsed time, output report and mesh; review tissue segmentation.
- [ ] Exercise manual-mask import, hybrid seam review and EEG recomputation with known local test data.
- [ ] Load the original m2m in the Cz tool; switch original/hybrid surfaces and corresponding EEG assets; verify landmarks and distances visually.
- [ ] Confirm hybrid localization does not silently substitute the original volume FEM.
- [ ] Move the program folder, restart, and verify relative launcher paths still resolve.

Result: pending. Static Python syntax checks and Linux unit tests do not satisfy this checklist.
