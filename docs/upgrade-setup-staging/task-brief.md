# Audit unresolved publication boundaries and preserve foreign staging names

Base: f3055293b79dc9e2fb1f972c4873f4c06821837f.

Use deterministic probes to distinguish unconfirmed publication, optimistic
pre-registration and writes after the final observation. Do not infer completed
ownership from intended content or promise portable filesystem CAS. Document
manual recovery using existing v1 receipts without deleting/rewriting evidence.

Investigate the adjacent concrete cleanup defect: _replace unlinks its temporary
pathname without comparing its original staged inode, unlike _create. Reproduce
replacement with different/identical bytes, symlink replacement and unavailable
identity. If proven, reuse the existing identity helper, retain unconfirmed names,
and keep normal cleanup and interrupt semantics. No new persistent recovery
format, signal mask, service, permission, account or model call.

Acceptance: red/green focused tests, actual synthetic CLI SIGINT, setup and full
serial regression, offline installed tests, and independent review of frozen
commit and probe conclusions. Preserve f305 and older Library evidence. Keep
main/PR11/PR12 untouched; carry the cumulative increment and exact tree proof.
