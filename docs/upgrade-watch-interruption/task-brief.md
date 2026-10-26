# Preserve interrupted invocation evidence in foreground watch

Base: 90862a325d36acca0ab16a4b20b29c70837d3169.

Problem: watch catches RunInterrupted as KeyboardInterrupt and leaves last at
the preview or previous cycle, discarding observed launch/cleanup and uncertain
completion/receipt evidence. Recovery must inspect the interrupted invocation.

Scope: watcher.py, focused synthetic tests, foreground guide and its bundled
copy, this brief/manifest/validation. Reuse the runner's existing report in last;
preserve generic KeyboardInterrupt behavior, counters and historical watch exit
code. No schema/protocol, runner mutation, auto retry/ACK, model, account, CLI
installation or service change. Protected paths and frozen packages untouched.

Acceptance: deterministic failed tests before implementation; actual CLI SIGINT
after a child marker; uncertain completion/ACK observations retained without
counter increments or replay; idle wait interruption retains prior last result;
runner/watch regression, serial full suite, installed candidate, independent review.
