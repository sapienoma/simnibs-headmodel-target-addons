# Public release preparation audit — 2026-10-27

Project: simnibs-headmodel-target-addons; public candidate: 1.0.0-rc.1. Based on internal Suite 1.80.2 distribution revision 4.

All 76 executable source/launcher files are byte-identical to the input dist4 archive. No numerical or application behavior changes. All 56 Python files parse using Python 3.11 grammar. LICENSE remains byte-identical to dist4. Local Markdown links, ZIP CRC and SHA-256 checksums were checked.

Duplicate historical VALIDATION.json/PACKAGING_VALIDATION.json records were consolidated with original paths in docs/HISTORICAL_VALIDATION.json. Root README pointers, public version metadata, changelog and publishing instructions were rewritten to avoid obsolete distribution-version claims. Application-specific VERSION.json and comprehensive workflow instructions remain intact.

Filename/extension and limited credential-pattern scans found no clinical image/mesh/model-weight files, private keys or common GitHub tokens. Only program target-catalog CSVs are included. This limited scan is not a proof that all possible sensitive content is absent.

Prior revision 3 recorded 10 core/preferences tests; dist4 recorded unchanged Python ASTs after license-comment insertion. These are historical checks, not newly executed Windows tests. Native Windows/Qt/CHARM/FEM acceptance remains pending; see WINDOWS_ACCEPTANCE.md. Historical source provenance is not independently certified. Third-party rights and notices remain applicable.

The duplicate integrated target_tool and scalp_repair directories are runtime dependencies and intentionally retained. SHA256SUMS.txt covers all files except itself.
