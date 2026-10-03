# Content-bound local checks

Requires CoProgrammer 0.3+. Check `coprogrammer --version` in every environment.

Run an explicit command from the project root and write a receipt to an ignored
directory (or outside the repository). Arguments after `--` are an argument
vector, not a shell script:

```sh
coprogrammer check run --label unit-tests --output .coprogrammer/checks/unit.json \
  -- python -m unittest discover -s tests
coprogrammer check verify --artifact .coprogrammer/checks/unit.json \
  -- python -m unittest discover -s tests
```

If `.coprogrammer/` is not ignored in this project, choose an output outside
the checkout. Existing non-receipt files and different labels are preserved.
Command output goes to stderr; the JSON result goes to stdout. Receipts contain
an argument hash, not command arguments, output or credential values. Commands
must be noninteractive. Only the CLI can run a command; MCP `check_verify`
never executes its optional expected command.

Exit 0 means successful and stable (`run`) or current (`verify`). Exit 1 means
failed, stale or unavailable evidence. Invalid input and storage errors exit 2.
Without an expected command, verify checks content/environment/result/age only;
`expected_command_checked` explicitly records that limitation. A missing or
malformed receipt is an error, never a passing result.

The fingerprint covers sorted paths, modes and actual bytes of tracked and
nonignored untracked regular files. Deleted files disappear from the content
view; staging and content-preserving commits do not by themselves invalidate
the receipt. Documentation and tests are included. File edits, additions,
renames and executable mode changes can invalidate it even with the same HEAD.
Symlink targets are hashed as links, without reading the target file.

Two observations detect ordinary concurrent edits at snapshot boundaries.
Before/after fingerprints detect a command that changes its inputs, even when
it exits successfully. This does not continuously watch a process; transient
edits restored between observations are not detected. An expired receipt (24h
by default), future timestamp, changed runtime identity or different expected
command is not current. `--max-age-seconds` accepts 1–604800.

Ignored files, credentials, environment variables, external symlink contents,
dependencies and remote services are outside this fingerprint. Python version,
platform and CoProgrammer version are recorded, but do not prove identical
environments. Raw bytes can differ across platform line-ending conventions;
run local checks on the receiving machine. Submodules, unresolved index
conflicts and special files are refused. Limits: 10,000 entries, 8 MiB per file,
64 MiB total, and 1 MiB per JSON artifact.

Receipts have a consistency hash, not a signature or trusted author. They
cannot grant approval, satisfy unrelated CI or certify a model reviewer.
Timeouts are failed evidence; inspect any surviving command descendants before
continuing. Include check statuses in a [portable handoff](WORKSPACE_HANDOFF.md).
