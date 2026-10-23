# Fixed failure diagnostics and manual recovery

Base: `9ee26c90a31afaa55b7ef39b603fbb47052f519a`.

Problem: execution diagnostics can remain at `reading_packet` after malformed
input, while a stdin OSError can escape as a traceback. Local storage and process
I/O failures omit useful OS error categories. A prior native exit cannot be
explained retrospectively when its stderr was not retained.

Scope: Codex adapter, focused synthetic tests, canonical/bundled guide, and this
brief/manifest/validation. Record terminal input rejection stages and a bounded
allowlist of OS error names without persisting exception text, filenames, native
stderr or prompts. Keep native subprocess argv, task/result contracts, explicit
execute opt-in and private diagnostics opt-in unchanged. Document inspection
steps without automatic task retries, claim release, ACK or lease takeover.

Acceptance: malformed/oversized/unreadable input never launches the native client;
fixed diagnostic fields contain no injected private markers; local setup/read/
process I/O errors retain correct observed startup state; unknown errors stay
unknown. Native nonzero exit is not attributed to network, account or quota.
Run focused synthetic checks, serial full unittest, config/manifest and JSON/YAML
validation. Preserve original private evidence. No real model calls, CLI installs,
credentials/sessions access, public writes, CI trigger, merge or package release.
