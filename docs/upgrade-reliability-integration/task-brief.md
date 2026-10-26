# Integrate reviewed reliability fixes

Base: PR12 merge `95239fee0137a997faa1cfbb6aed5306f331090c`, tree
`02855b6a1e03562585d6a992aaab751f0c754960`.

Carry the existing cumulative candidate into one separate review branch. Preserve
the tested runtime and tests from `c2a6248c710d049aa3f06c47cfe013cb8c9f69cc`;
clarify historical validation records so old remote status cannot be mistaken for
current status. No new execution behavior, version bump or package release.
Earlier task briefs describe their individual implementation slices; their
no-remote-write scopes are historical and are not a current integration decision.

The increment covers protected explicit retries, conservative setup publication
and interruption recovery, interrupted-watch evidence, and notification preflight.
Reuse completed independent reviews and the full/installed acceptance on the exact
runtime bytes. Verify remote base/tree and every changed file blob before handing
off a Draft PR. Review publication contents independently, including diagnostics
and examples; exclude private execution records and untracked work materials.

Normal GitHub checks and required reviews remain authoritative. Do not override
protection, fabricate approval, retry models or alter accounts and permissions.
Windows native signal behavior and filesystem race limits stay explicit.
