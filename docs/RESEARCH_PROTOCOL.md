# Research Protocol

This protocol keeps CoProgrammer research actionable.

## Research Loop

1. **Capture**
   - Add source links to a Research Leads discussion or issue.
   - Add structured entries to `research/open-source-leads.json` when the lead
     has lasting value.

2. **Classify**
   - Direct competitor.
   - Adjacent capability.
   - Reusable component.
   - Research reference.
   - Needs verification.

3. **Evaluate**
   - What capability does it prove?
   - What should CoProgrammer borrow?
   - What should CoProgrammer integrate instead of building?
   - What gap remains?
   - Does it change architecture or roadmap priority?

4. **Decide**
   - Build.
   - Integrate.
   - Watch.
   - Archive.
   - Avoid.

5. **Convert**
   - Discussion becomes issue only when there is a concrete implementation or
     research task.

## Required Fields

Every durable research lead should include:

- name;
- links;
- category;
- capabilities;
- useful ideas;
- gap versus CoProgrammer;
- status;
- notes.

Use:

- `schemas/research-lead.schema.json`
- `templates/research-lead.json`

## Decision Labels

Use these decision labels in docs and discussions:

- `borrow`: adopt a pattern or small feature;
- `integrate`: depend on the tool or platform;
- `watch`: track because it may become competitive or reusable;
- `avoid`: intentionally do not copy;
- `archive`: no longer relevant.

## Quality Bar

Good research notes are short but specific.

Weak:

> Tool X does AI code review.

Strong:

> Tool X provides diff-aware inline diagnostics with multiple reporters. We can
> borrow the reporter abstraction for branch digest findings. It does not
> extract branch intent or generate integration records.

## Update Cadence

- Weekly: add and triage new research leads.
- Biweekly: update `docs/FEATURE_GAP_MATRIX.md`.
- Monthly: revisit `docs/COMPREHENSIVE_RESEARCH_PLAN.md` and MVP scope.

## Anti-Patterns

Avoid:

- collecting tool names without decisions;
- treating marketing pages as verified architecture;
- confusing code review with semantic integration;
- copying broad AI-company metaphors without narrowing them to software state;
- adding more agent autonomy before decision records and audit trails exist.
