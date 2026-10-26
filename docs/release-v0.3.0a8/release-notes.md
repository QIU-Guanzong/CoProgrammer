# CoProgrammer 0.3.0a8 prerelease candidate

This candidate packages the code merged through PRs #11, #12 and #13. Its runtime
base is main commit `5fe9fba51960bed513132dbc84bc2e24998be753`, tree
`1ae4979d97cd06cca0e682773eb739ce3085b246`. This release preparation changes version
metadata and documentation only. It does not claim that PyPI publication has
already happened.

## Included changes since a7

- Explicit Codex and Claude task-only native harnesses, first-use discovery and
  optional native capability probes, with bundled installation and recovery guides.
- Optional protected retries that detect recorded workspace changes before launch.
- More conservative setup publication and interruption recovery, preserving changed
  or ambiguous user files and retaining the original interruption on cleanup errors.
- Foreground preflight and interrupted-watch reports that distinguish unknown
  finish/message acknowledgement outcomes from confirmed completion.

Native execution requires explicit opt-in and existing authorized client settings.
Client discovery and GLM/DeepSeek session labels do not establish model access.
Task-only harnesses do not automatically acknowledge messages or retry failures.
Filesystem checks do not lock external editors or eliminate all syscall races;
ambiguous recovery can require inspection. Windows CI coverage includes platform
skips and is not Windows native-client/model acceptance. WorkBuddy GUI remains
deferred. See the bundled guides for the supported boundaries.

## Normal release and installation

After this version preparation passes the repository's ordinary review/checks and
is merged, publish the `v0.3.0a8` tag at that exact merged commit. The existing
`Release to PyPI` workflow builds, tests and publishes through Trusted Publishing.
Confirm that workflow succeeds and both distribution files appear on PyPI before
announcing availability. Create the matching GitHub prerelease using these notes;
do not reuse a7 artifacts or overwrite its tag.

Once publication is verified, install the exact prerelease in the intended environment:

```sh
python -m pip install --upgrade 'coprogrammer==0.3.0a8'
python -c "import coprogrammer; print(coprogrammer.__version__)"
python -m coprogrammer.codex_harness --check
python -m coprogrammer.claude_harness --check
coprogrammer knowledge show templates/INTERRUPTED_RUN_INSPECTION
```

In each existing project, preview `coprogrammer setup --client codex --upgrade`
(or `--client claude`) before adding `--apply`. Customized files remain conflicts.
Reload the client and complete its normal project/MCP trust flow. If upgrading
fails, retain the project files and receipt, inspect the reported conflict and
avoid automatically retrying tasks or acknowledging unknown messages.

The stable MCP registry metadata is a separate distribution channel and is not
changed by this prerelease preparation.
