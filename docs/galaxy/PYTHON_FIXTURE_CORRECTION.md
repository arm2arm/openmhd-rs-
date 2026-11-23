# Recovered-native negative fixture correction

The first complete89 REANA campaign at source
`7576269f6bb29aa2d29513aa15488a39ccad6158` exposed two fixture incompatibilities.
Original case0004 (`fd4a5138-f916-4d15-820a-1fac48429b30`) omitted the legacy
release schema and raised `KeyError` before its intended proof-hash rejection.
Original case0024 (`c804c97f-1d53-4616-8cd1-42b4f7c58599`) changed only one shared
provider pin and correctly hit the earlier descriptor-consistency guard instead
of its expected provider-source authentication guard. Both actual failures,
original source, submissions and artifacts remain unchanged in the separate
original controls worktree.

The correction supplies the explicit legacy-v2 schema in the first negative
fragment and makes both descriptor pins consistently wrong in the second. It
preserves the expected error assertions and the assertion that external
execution is never called. The separate unequal-provider control is unchanged.
All26 methods retain their selector names;24 method ASTs and all production
source are unchanged. The exact proposed test SHA256 is
`85efe69bbded66657f961d68a597e4224ad30de73d0317fa1a98234996598bb5`.

The source-only candidate and causal inspection are retained under root
`results/galaxy_complete89_fixture_repair_v2_20261123`, with closed manifest
`31018f0b690b4bf12aa01caed1a221df027fe4e4ac05ebcfb37cc911ad751853`.
Own stdlib AST/hash/data inspection is not a test execution or passing result.

This isolated checkout permits preparing the corrected generation while the
original campaign finishes; it does not modify that campaign's frozen working
source or helper/input fences. A new immutable REANA import parent and actual
independent method outputs remain required. No transport recovery may outvote
either original genuine failed test. Scoped periodic fixed/rigid 2.5D M1
acceptance is unchanged; native/3D geometry/gravity/moving-MHD/ISM/merger acceptance
remains open.
