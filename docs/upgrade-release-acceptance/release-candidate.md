# Release candidate checklist

This is a locally reviewed cloud candidate based on `5b3f7aa`, not a published
package. The final full Git SHA, branch, wheel/sdist/bundle/patch hashes and
validation evidence belong to the private release-acceptance receipt.

Completed acceptance:

- Cumulative adapter, first-use discovery/probe, runner diagnostics and
  interruption inspection reviewed together with actual installed CLI help.
- Missing guide distribution repaired using existing package-data/catalog paths;
  canonical copies remain synchronized and installed users can read them.
- Clean exported source builds a wheel and sdist offline; rebuilding from the
  sdist preserves all runtime/resource payloads, excluding private state.
- Fresh virtual environment runs entry points, resources, setup editions and
  generated Codex/Claude MCP launchers outside the source checkout.
- Baseline configuration remains compatible; failure/interruption inspection
  preserves claims, edits and Manager bytes without replay.
- Focused checks and one serial full regression pass. Actual Linux synthetic
  child cleanup passes. Temporary fixtures/install environments are removed.
- Existing bounded watcher, singlewatcher, scope/claim protections, native
  OpenClaw validation and isolated profiles retain their previous behavior.

Remaining release gates:

1. Assign an agreed new candidate/release version and build provenance. Metadata
   still says `0.3.0a7`; it must not be mistaken for a newly published package or
   used to overwrite that public version. Build and smoke-check the final version
   when that change and publication are authorized.
2. Verify the same final artifact on the intended supported Python/OS matrix.
   This receipt covers Linux/Python3.12, not native Windows signals/processes or
   every advertised Python version. WorkBuddy GUI remains deferred.
3. For a claim of real Codex collaboration, separately authorize a small native
   task with existing account/configuration and bounded scope. Version/help and
   offline fixtures cannot establish model access or task correctness. No such
   call was made here.
4. Resolve delivery authorization/access separately. GitHub integration403 and
   Library failure are historical delivery blockers; no retry occurred in the
   preceding round or this round. No branch, PR, merge or release was created.

The next most useful engineering target is one Windows clean-install acceptance
of the final identified artifact, including scoped synthetic execution, failures,
interruption cleanup and read-only outcome inspection. It would close a concrete
platform gap and make support claims reviewable. Keep further small features
paused until this candidate has a unique version and the installation matrix is
accepted. A real-client acceptance is a separate later authorization step.

The documentation example under `docs/examples/interrupt_inspection.py` remains
explicitly a source-checkout synthetic fixture. The packaged guide is readable
after installation; it does not claim that this source-only script is installed.
