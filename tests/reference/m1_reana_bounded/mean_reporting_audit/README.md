# Verified supplemental mean-report correction

REANA workflow `openmhd-m1-mean-report-audit-20261110.1`, UUID
`9fb39416-290c-4028-b199-8aa0e0248d18`, finishes successfully at
2026-11-10 01:17:44 UTC, after the main compute workflow was stopped.
Snapshot SHA256 `becbff01b4671d52de3e597093ded7d7f3bcc5d862d241318961ce5e61874dc5`.

All **68 Python regressions pass**, including the two tests added by `c6cda9d`.
The corrected mean report changes only `mean_refinement`; all other fields
remain identical. The four candidate spatial/time observation rows are present
and all mean checks pass. Their roundoff-size boost residuals and negative
fitted orders are preserved; no physical convergence requirement is invented
for these residual observations. No MHD evolution was repeated.

The original report remains in `../mean/summary.json.gz` and is also a pinned
input here. `corrected-mean-summary.json.gz` is the separately labelled
corrected copy. Inputs, exact 80-file source export, driver, remote report,
test log, output manifest and independent archive checksums are retained.
The driver's private synthetic Git commit serves unit-test fixtures only;
the true source revision `c6cda9d907a143294242c6fb89b244fd8487519c` and every
source hash are recorded separately. This is a reporting fix, not M1 acceptance.
