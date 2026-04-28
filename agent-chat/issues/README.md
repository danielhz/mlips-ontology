# Issues

Open work items in the paper repo, complementary to the per-message
threads in `agent-chat/`.

## Convention

- One file per issue, named `issue-NNNN.md` where `NNNN` is a four-
  digit zero-padded sequence number, allocated in creation order.
- Each issue has a small front-matter block (status, assignee, dates,
  blocking relationships) followed by free-form content. See any
  existing issue for the template.
- Statuses: `open`, `in progress`, `blocked`, `done`, `wontfix`.
- When an issue is closed, mark its status and append a final dated
  note explaining the resolution (or pointer to the commit).
- Messages in `agent-chat/message-*.md` may reference issues by
  number (e.g. "address issue-0003 next").

## Index

| # | Title | Status | Assignee |
|---|---|---|---|
| 0001 | Wikidata sweep on the controlled vocabulary (`mlips-vocab.ttl`) | open | developer |
| 0002 | Promote software libraries to canonical IRIs and add Wikidata links | open | developer |
| 0003 | Wikidata sweep on `MaterialSystem` instances in the corpus | open | developer |
| 0004 | ORCID identifiers for authors (`ScholarlyArticle` decomposition) | blocked | unassigned |
| 0005 | ROR identifiers for institutions | blocked | unassigned |

(Update this table when an issue lands.)
