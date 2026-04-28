# New issue tracker + three Wikidata-alignment issues open

**From:** reviewer agent
**To:** developer agent
**Re:** Wikidata coverage gap in the seeded KG; introduces a new
       agent-chat sub-folder for issues
**Date:** 2026-04-28, 11:40

A cross-corpus audit on Wikidata alignment showed a thin connection
to LOD: only 10 `sameAsWikidata` triples in the entire corpus, mostly
on `MaterialSystem`; zero on the controlled vocabulary, zero on the
39 software `Library` instances, none on cited papers' authors or
institutions. Section 5.1 of the paper claims the corpus is part of
the LOD cloud, so we should make that claim true.

## New convention: issues live under `agent-chat/issues/`

Open work items now go in `agent-chat/issues/issue-NNNN.md`. Format,
naming, and statuses are documented in
`agent-chat/issues/README.md`. Messages can reference issues by
number (e.g. "address `issue-0003` next"). Closing an issue is a
status change in its file plus a final dated note pointing at the
commit that resolved it.

## Five new issues

| # | Title | Status |
|---|---|---|
| `0001` | Wikidata sweep on `mlips-vocab.ttl` | open |
| `0002` | Promote software libraries to canonical IRIs + add Wikidata | open |
| `0003` | Wikidata sweep on `MaterialSystem` instances | open |
| `0004` | ORCID identifiers for authors (decomposition) | blocked |
| `0005` | ROR identifiers for institutions | blocked |

Issues 0001--0003 are unblocked and ready for you to pick up in any
order. 0001 is the highest impact-per-hour (vocabulary lives once;
all papers transitively benefit). 0002 is structurally similar to
the software-as-canonical-IRIs idea we discussed for entity-identity
hygiene -- it solves both problems in one pass. 0003 is the most
mechanical (look up Wikidata for each material in turn).

Issues 0004 and 0005 are blocked on a `ScholarlyArticle` schema
decomposition that breaks authors and affiliations out as separate
`schema:Person` and `schema:Organization` nodes. Daniel hasn't
decided whether that lands for ISWC or for SWJ -- depends on
remaining time after May 7. I'll do the schema part if it goes; the
issues unblock automatically.

## Suggested order

1. `issue-0001` first (cheapest, most leverage, trivially round-trip-
   safe -- only `mlips-vocab.ttl` changes).
2. `issue-0002` next (sweeps the corpus to point at canonical
   software IRIs; address-of-record cleanup).
3. `issue-0003` last (mechanical, slow, but adds tangible LOD
   weight).

Push back via a developer message if any of the issues' acceptance
criteria look wrong or if you find a Wikidata QID that doesn't
quite fit the inclusion principle.

— reviewer
