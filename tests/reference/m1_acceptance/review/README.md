# Separate independent AI review, 2026-11-21

The [review report](../../../../docs/M1_FINAL_AI_REVIEW.md) conditionally
approves the pinned engineering candidate's source and historical evidence.
Fresh integrated-source physical results and their final review remain
required; `full_m1_accepted` is false.

`verify_review_inputs.py` independently checks existing observations and
source/provenance identities without importing production reducers, compiling,
running tests/evolutions, or controlling REANA. It checks the original packet
manifest entries, the 94-file iterative archive, 226 scientific files against
the frozen development revision, fresh preflight artifacts/logs, 214 actual A
receipts/records/final CSV hashes, current-source applicability test logs,
eight independently refitted wave ladders and prescribed-source dependencies.
`input_verification.json` retains those results and exact file/input hashes.

Reproduction from the repository root, with the retained ignored REANA
downloads present, uses a **fresh output path**:

```sh
python3 tests/reference/m1_acceptance/review/verify_review_inputs.py tests/reference/m1_acceptance/review/input_verification_again.json
```

`rerun_{waves,medium,mean,physics_boost,shock,vortex}.json` are fresh reviewer
executions of the six supplied independent reducers after inspecting their
source. All six returned zero, and all resulting reports are logically
identical to the provisional packet reports. The wave rerun used no cached
case/pair results. Only compact reports are retained here; input hashes and
the original immutable artifacts identify the observations.

The supplied parent `verify_packet.py` passed before this subpacket existed.
At review creation its closed recursive file inventory failed at line 23 because it included
these added reviewer files. No original manifest entry changed. The original
manifest/verifier were deliberately left unchanged; final packaging needs a
separately hashed review subpacket boundary or a verifier that covers both.
This is an identified packaging issue, not evidence of a physical failure.

The self-excluding `review_sha256.json` inventories the retained reviewer
script and reports. It does not amend the original evidence manifest.

Coordinator packaging resolution: the parent verifier now checks this exact
subpacket inventory and pins its manifest separately. The original review
observations and source-verification report are retained. This resolves the
inventory finding without changing any scientific source or threshold.
