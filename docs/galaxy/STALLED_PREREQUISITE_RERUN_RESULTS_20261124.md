# Three stalled prerequisite methods: rerun results

2026-11-24. **All three requested replacements passed on REANA.** Each ran
one exact Python test with zero failures, errors, skips, expected failures or
unexpected successes. These are execution-control tests, not new geometry
evolutions or M2a acceptance.

The owner requested rerunning the stalled jobs. Fresh normal-TLS observations
at 15:56:11 UTC still showed originals 0123/0125 queued and 0180 pending.
Immediately before submission, two coherent all-version scans per original
confirmed those same unique UUIDs and states, and two scans per replacement
name confirmed absence. No original job was restarted, stopped or overwritten.

| Method index | Original UUID | New version-1 UUID | Acquired verdict |
| --- | --- | --- | --- |
| 0123 | `ceb8d3ab-de2a-4112-a2c5-c4a81ea8b6f2` | `c0b3392e-a300-4411-b10c-e4a81deec464` | passed |
| 0125 | `63224758-14f6-43ac-acb1-64af7fa77285` | `5fa93966-2073-486b-babe-2020e697eb4d` | passed |
| 0180 | `218c9734-b666-4638-ac4d-d72856913a17` | `d1d16a58-5f30-42d2-8452-51e5d83c69f6` | passed |

Replacement workflow names are `openmhd-m216-r1-20261124-<index>.1`. Their
selectors are, respectively:

- `scripts.test_galaxy_recovered_native.RecoveredNativePythonProofTests.test_original318_fixed_generation_cannot_be_replaced_by_recovered_later_proof`
- `scripts.test_galaxy_recovered_native.RecoveredNativePythonProofTests.test_provider_source_authentication_precedes_external_execution`
- `scripts.test_galaxy_workspace_case.WorkspaceCaseMetadataTests.test_unexpected_existing_output_is_never_overwritten`

The original source revision is
`0bc9e50beb987f4e8d0fbc7f27674fc05ec4912f`, with snapshot SHA256
`50cf56ecaf2cd220c3644f4d89e289867e350104637601594b8543d85e0f9c57`.
The original import certificate, uploaded job, source archive, snapshot,
image and REANA specification were retained byte for byte. Only each
`case.json.workflow` and its digest in `payload.json` changed. Each independent
job declared **1 CPU, 2 GiB and a 180-second child timeout**.

All three concurrent submissions returned zero after starting at
15:59:52 UTC. By 16:01:18 UTC the server reported all three unique version-1
identities finished. The single subsequent acquisition returned zero at
16:02:07 UTC: **24 output artifacts and 30 successful transports**, including
before/after observations and eight downloads per method.

The original source-pinned validators checked the actual retained result,
runtime, command, child envelope, raw child, output manifest and transport
bytes. A separate offline pass returned zero at 16:03:14 UTC, rederived all
three strict verdicts, checked every acquisition body hash, all 30 diagnostic
UUID links, original/replacement input hashes and durable host-command logs.
No test method was executed locally. One progress-display inspection used an
incorrect receipt key; its correction and lack of effect on execution or
verdicts are recorded in the audit bundle.

The [offline result](results/stalled_prerequisite_rerun_20261124/offline_verification.json),
[retained-body manifest](results/stalled_prerequisite_rerun_20261124/retained_files.json)
and compact [audit bundle](results/stalled_prerequisite_rerun_20261124/audit.tar.gz)
preserve the actual inputs, original/replacement mappings, submission receipts,
source-pinned validators and acquired outputs. Common input bytes are stored
once under `shared/`. This is a coordinator execution and offline validation
record; no new independent review or component acceptance is claimed.

The original whole216 submission and its stalled identities remain historical
evidence. This explicit three-method replacement packet is separate from its
whole-catalog validator. The larger workspace regression batch and M2a G02–G04
requirements remain open, as recorded in the
[M2a completion checklist](M2A_FINALIZATION_STATUS.md).
