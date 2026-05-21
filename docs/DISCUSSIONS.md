# Discussions

CoProgrammer should keep open-ended research and architecture debate out of
implementation PRs. Use GitHub Discussions for questions, research leads,
architecture proposals, and product direction before converting them into
issues or PRs.

## Repository Setup

GitHub Discussions must be enabled in repository settings. This cannot be
fully enabled by committing files alone.

Recommended categories:

| Category | Format | Purpose |
| --- | --- | --- |
| General | Open-ended discussion | Broad project questions and coordination. |
| Ideas | Open-ended discussion | Product, protocol, and workflow ideas. |
| Q&A | Question and Answer | Questions with a concrete answer. |
| Research Leads | Open-ended discussion | Similar projects, papers, tools, and small reusable features. |
| Architecture Decisions | Open-ended discussion | Design tradeoffs before they become ADRs or issues. |

GitHub's default categories usually include General, Ideas, and Q&A. Custom
categories such as Research Leads and Architecture Decisions should be created
manually after Discussions are enabled.

## Discussion Templates

This repository includes discussion category form templates under
`.github/DISCUSSION_TEMPLATE/`.

These templates follow GitHub's category form convention: the filename must
match a discussion category slug. For example, `ideas.yml` applies to the
Ideas category.

Current templates:

- `general.yml`
- `ideas.yml`
- `q-a.yml`
- `research-leads.yml`
- `architecture-decisions.yml`

## When to Use Discussions

Use Discussions when:

- the topic is exploratory;
- the answer needs community input;
- a tool or project should be compared before implementation;
- the architecture impact is not clear yet;
- the idea may later turn into multiple issues.

Use Issues when:

- there is an executable task;
- acceptance criteria are clear;
- the work needs assignment, labels, milestones, or PR tracking.

## Research Lead Flow

1. Open a Research Leads discussion with source links.
2. Classify the item as direct competitor, adjacent capability, reusable
   component, or research-only.
3. Identify what CoProgrammer can reuse, integrate, or intentionally avoid.
4. Convert to an issue only when a concrete action exists.

Structured research leads can also be stored as JSON using
`schemas/research-lead.schema.json`; the current seed file is
`research/open-source-leads.json`.

## Maintainer Checklist

- [ ] Enable GitHub Discussions.
- [ ] Create Research Leads category.
- [ ] Create Architecture Decisions category.
- [ ] Confirm discussion templates render.
- [ ] Link active research discussions from `docs/OPEN_SOURCE_SCAN.md`.

## References

- [GitHub Docs: Discussions](https://docs.github.com/en/discussions)
- [GitHub Docs: Managing categories for discussions](https://docs.github.com/en/discussions/managing-discussions-for-your-community/managing-categories-for-discussions)
- [GitHub Docs: Syntax for discussion category forms](https://docs.github.com/en/discussions/managing-discussions-for-your-community/syntax-for-discussion-category-forms)
- [GitHub Docs: Syntax for issue forms](https://docs.github.com/en/communities/using-templates-to-encourage-useful-issues-and-pull-requests/syntax-for-issue-forms)
