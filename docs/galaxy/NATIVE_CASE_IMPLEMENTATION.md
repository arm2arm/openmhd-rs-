# Native one-leaf cases: implementation delivery, not approval

2026-11-22. This author implemented the native caller repair and practical
preflight-transfer/case/output pipeline following the independent source review
at `bba2db5`. **No new module was imported, test executed, binary built, adapter
called or workflow submitted in this task.** The accompanying
`IDENTITY_RESTORE_AND_SUBMISSION_REVIEW.md` independently reviews only the root's
two earlier deltas. It does not approve this implementation. M1 acceptance at
`309ae41` remains limited to its named fixed/rigid 2.5D profile.

## Durable native caller

`reana/galaxy_test_case.py` persists actual runtime/result metadata and then an
atomic `command.json` launch intent before entering the unchanged held-leader
supervisor. The intent binds actual argv/cwd and snapshot/case/payload/runtime/
binary/runner/supervisor hashes, with unknown writer/reap state. An escaping
exception retains typed `unknown_closure` (or the earlier pending intent if
publication fails), null finish time, and required external terminal evidence.
It never invents a PID or signals an unowned group. A validation failure before
intent remains `not_launched`. Atomic publication is observable ordering, not a
power-loss or inaccessible-storage recovery guarantee. Failed output hashes
are observations of retained bytes; they cannot establish stopped writers.

The job's default architecture check remains mandatory. Preparation calls the
same metadata validator with `check_architecture=False`, so a Darwin client
does not masquerade as the parent Linux architecture. The actual job records
its machine, Python/runtime visibility and literal one-thread environment.
It uses the unchanged supervisor's Linux private PID/PGID/SID/starttime,
held-leader and writable-log-FD contract, including its deliberately limited
cooperative-process scope. Detached nonwriters, UID changes, infrastructure or
interpreter loss are not universally contained. Child wait timeouts do not
bound input parsing, transfer, extraction or total workflow time.

## Concrete source interfaces

`scripts/prepare_galaxy_cases.py` is the thin command interface to
`tools/galaxy_evidence/pipeline.py`. These commands are **written interfaces**;
they have not been invoked. Do not use them until independent source review,
coherent freeze and the required real REANA prerequisites pass.

- `acquire-preflight --source <original-prepared-source> --submission
  <original-receipt> --workflow <original-name.1> --output <fresh-directory>`
  retains original snapshot/specification/upload parts/submission bytes and
  captures authoritative before/after observations plus actual UUID-linked GET
  bodies. It obtains parent execution/runtime/artifact/catalog/export/journal
  files, all prerequisite and compile/list logs, and every exported archive
  part. The original immutable source preflight must be finished. Source,
  helper and original-input fences precede closure. Failed attempts retain
  their partial bytes and typed failed acquisition; retries require a fresh
  directory and cannot submit or restart anything.
- `prepare --preflight <closed-acquisition> --coverage <reviewed-contract.json>
  --prefix <fresh-prefix> --output <fresh-case-directory>` creates one immutable
  JSON-as-YAML workflow and chunked executable per exact selector/profile. It
  retains the entire original parent acquisition as context. No method runs.
- `collect --cases <original-cases> --submission <original-submission.json>
  --output <fresh-packet>` captures originals and, independently per workflow,
  observe/eight-download/observe receipts. Failed/stopped/pending/partial rows
  remain nonpassing; a failed whole catalog retains its closed forensic packet
  and the strict verifier does not return success.
- `verify-results --packet <closed-packet>` is an offline native-schema and
  actual-body/link check. It invokes no test binary or network. It requires
  every exact planned leaf to have run successfully and does not trust summary
  flags. It must use the exact frozen helper source checkout; it is not a
  claim of arbitrary future-checkout portability.

There is deliberately no submit/retry/recovery command here. The plan entries
retain the existing `scripts/reana_cases.py` submission interface
(`directory`, `specification`, `workflow`, payload/spec hashes). That executor
can schedule all ready methods concurrently. Its original SDK/uncertain
mutation history is not upgraded to the new GET TLS policy. An original
submission can remain uncertain even when later authoritative observations
resolve execution. Keep original submission and any UUID recovery/transport
receipts immutable and separate; place closed history under the case directory
before output acquisition when it must be retained in that packet. Recovery
decisions remain operator/coordinator actions, never automatic new workflows.

## Reviewed catalog contract

The mandatory data-only contract schema is
`openmhd.galaxy-reviewed-catalog.v1`, with `component_accepted:false` and
`targets:[...]`. Each target contains:

```text
component: identity | geometry | gravity
manifest, source, target_kind:[test|lib], target_name
selectors:[full Rust libtest names, unique and complete for the selected route]
source_sha256:{every component Rust/Cargo.toml path: exact source hash}
review_path, review_sha256: original independent review document pin
resources:{threads:1, memory:2Gi|1Gi, timeout_seconds:180|300}
```

This is a proposed implemented client interface, awaiting independent review.
Hashing a review document cannot prove its recommendation; the coordinator
must ensure its actual scope supports these exact source pins and portability.
No real approved contract or numerical fixture has been fabricated here.
The source/catalog checks require both profiles and all 26 identity leaves,
24 geometry integration leaves plus exactly these four library leaves:

```text
three_d::exact::tests::exact_cancellation_retains_below_binary64_ulp_terms
three_d::exact::tests::dyadic_subnormal_and_signed_zero_decode_exactly
three_d::exact::tests::integer_product_carry_matches_binomial_identity
three_d::exact::tests::determinant_orientation_and_exact_coplanar_contact
```

All 39 delivered gravity names (9 library, 30 integration) must also be
selected. Their source-only author inventory at `8fe7342` is a catalog input,
not independent portability approval. The delivered gravity review `3e525cc`
supports short preflight; its protected-step source corrections still need
final exact source/review pins before the contract. Geometry's repairs are
committed at `feb5a5b`, retaining its 28 names; use those repaired source bytes
and their applicable review, not the superseded initial bytes. This yields **186 native
workflows**, 93 per profile, only if the final reviewed counts remain unchanged.
Missing/extra target leaves, wrong profile/source/binary/selector or omitted
gravity targets are rejected. Naming a crate is not sufficient for release.

The moving-mesh library route selects only the four exact-arithmetic names;
the binary's *full* discovered selector count remains the expected filtered
count in its libtest witness. Other old moving-mesh/restart tests embedding
`CARGO_BIN_EXE` paths remain excluded. The new target route runs one exact
standalone binary leaf, never an aggregate binary command.

## Transfer and output boundary

`reana/galaxy_preflight.py` retains its original executable archive and now
also exports ordered nonempty one-MiB `export.partNNNN` chunks and an exact
regular-member map. The archive identity is checked before safe member
extraction; extracted catalog/binary identities must also match the direct
catalog and actual parent output manifest. No archive is regenerated to stand
in for the original. The bound is 4096 archive parts and 512 MiB per member;
native case executables use at most 512 one-MiB parts. Exceeding a bound is an
explicit unsupported path, never silent target omission.

The new `tools/galaxy_evidence/readonly_adapter.py` reuses the **unchanged**
old adapter's normal CA/hostname TLS, no-proxy/no-redirect GET transport,
pagination consistency, exclusive no-follow partial publication and 16-MiB
per-body bound. Its narrow additional preflight allowlist is new reviewed
source, not an extension of the accepted adapter's historical certification.
It emits UUID-bearing observations and static credential-safe diagnostics.
Calls use an absolute credential-free adapter path; every attempt is journaled
before launch with source/argv/cwd/time/return/output/log/UUID linkage.
Valid diagnostic stdout/stderr bytes are retained exactly; unexpected arbitrary
messages are represented only by their byte count/hash. Original partials and
failure histories remain. Private settings are accessed only during actual
future adapter calls, never at import or in this source task.

GET observation/stream checkpoints remain cooperative 120-second/15-second
idle controls; every direct adapter call has a 300-second timeout. They are not
an absolute transfer-duration or descendant-containment theorem. Source
preflight catalog/log metadata over 16 MiB remains unsupported by this first
route; binary archives bypass that limit only through bounded parts. REANA's
original workspace must retain those parts/logs; listing an archive in YAML
alone is not evidence they can actually be downloaded. Capability is a future
real acquisition gate.

Native results deliberately use the old eight output filenames, with distinct
native-result and libtest-witness schemas. Validation checks artifact hashes,
actual input/source/binary/runtime links, exact argv/cwd/timeout, held-leader
cleanup, raw stdout equality, one named passing test and the full target's
filtered count. Python-unittest envelopes, merely finished workflows, unknown
closure and failure/ignored/aggregate summaries cannot pass. Native runtime
visibility/cgroups and declared labels remain separate observations. Neither
a leaf nor a whole-catalog pass sets component or physical acceptance true.

## Written controls, checks and remaining gates

The original 16 Python controls in `scripts/test_galaxy_preflight.py` remain;
two additions cover an exception escaping supervision after durable intent
(with a failed outer packet) and true prelaunch failure. The new
`scripts/test_galaxy_cases.py` has 16 inert metadata controls for transfer paths,
regular/archive identity, nested closure, input changes, UUID/version/status,
actual transport/body linkage, uncertainty, one-job declarations, native schema
rejection and complete/negative catalog policies. These are **34 written,
unexecuted** controls, not passing scientific/native executions. The synthetic
catalog control uses actual source names with explicitly invented compiler
metadata; it does not fabricate a finished physical/preflight packet.

Only static Python AST parsing, original-body comparison, hashes, JSON/source
inspection, links, whitespace and manual call-flow review occurred. Source
inspection corrected an initial memory-request assumption to the root
wrapper's actual memory-limit field, and narrowed log paths to actual exporter
and bootstrap filenames. Nonexistent-filename discovery exits and truncated
displays are recorded in the retained receipt boundary; no test failure or
success is inferred from them.

Before execution: independent review of this authored code; resolved identity/
geometry/gravity source reviews and root workspace/lock integration; a coherent
immutable source/import/format/strict-Clippy/build/compile/list REANA preflight;
real finished parent output/transport review; exact reviewed catalog contract;
and separately declared per-method metadata and native REANA workflows with
independent output review. Native initial requests are identity 1 CPU/2 GiB/
180 s, geometry 1 CPU/2 GiB/300 s, gravity 1 CPU/1 GiB/180 s. There is no aggregate
CPU cap. Actual limits/capabilities must be observed, not inferred from YAML.
Independent gravity high-precision/long-orbit evidence, moving topology/MHD,
gravity/source/domain/galaxy gates remain separate. This delivery accepts no
new component or deforming 3D merger.
