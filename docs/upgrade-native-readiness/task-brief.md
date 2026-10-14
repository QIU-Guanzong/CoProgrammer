# Native readiness and public handoff

Base: `2dde0d49a88dde33826b96bb0ac5f07901913ed6`.

Add an optional Claude first-use version/help/authorization probe. Plain check
remains discovery-only. Require explicit probe under check, run only trusted
version/help/auth status commands with the existing five-second cleanup helper,
and emit fixed metadata without account values or native text. Report missing,
unknown and logged-out states separately from model connectivity. Never log in,
select a provider, call a model or retry a retained task.

Accept exit 1 stdout only for Claude's documented auth-status command; the shared
helper defaults retain Codex behavior. Validate auth JSON strictly and require
loggedIn and exit status to agree. Version/help only describe local declarations.
No protocol, sandbox, approval, account or global profile change.

Keep the original cloud Git history and immutable receipts private. Replace the
public handoff prose containing internal coordination identifiers with a project
summary. Submit the tested final file tree through the authorized GitHub
connector on a fresh review branch, with a draft PR; do not merge or release.
Record original source HEAD, public review HEAD and exact tree equality privately.

Acceptance: offline parsing/default-no-launch, auth false/true/unknown, failed
probe and interruption cases; installed native diagnostic with no model request;
focused suites, serial full unittest, config/manifest and JSON/YAML validation;
bundled guide identity; preserved prior receipts/claim and cleanup.
