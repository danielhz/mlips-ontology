# Issue 0004: ORCID identifiers for authors (`ScholarlyArticle` decomposition)

**Status:** blocked
**Assignee:** unassigned
**Created:** 2026-04-28
**Blocks:** none
**Blocked by:** schema change to break authors out of `ScholarlyArticle.schema:name` into separate `schema:Person` nodes (planned, not yet started)

## Summary

The corpus's 20 `ScholarlyArticle` nodes record author names as a
single `schema:name` string ("Kumar, Körmann, Grabowski, Ikeda"
etc.), with no structured per-author entity that could carry an
ORCID. Authors of MLIP papers commonly have ORCIDs (we already do
for the running example: Daniel Hernández, Yuji Ikeda, etc., on
the ISWC paper itself), so this is high-quality alignment if we can
expose it.

This issue is **blocked** on a schema change that decomposes
`ScholarlyArticle` into a node carrying explicit `schema:author`
links to one or more `schema:Person` nodes, each of which can carry
`schema:identifier` (with an ORCID URI), `rdfs:label`, and other
metadata. Once the schema is in place, this issue becomes a
mechanical sweep across the 20 papers: for each paper, look up its
authors' ORCIDs (most are public on the publisher's page) and
encode them.

## Background

The decision on whether this lands for ISWC or for the SWJ extension
is deferred. The schema change is real work -- 20 paper canonicals,
the appendix tables, the SPARQL queries that touch `schema:author`
-- and the deadline pressure is the gating factor. The expected
order is:

1. Reviewer agent does the `ScholarlyArticle` schema decomposition
   (when scheduled): adds `schema:Person` instances, `schema:author`
   object property, `schema:identifier` data property convention.
2. After commit lands and the schema is in `mlips.xhtml`, this
   issue unblocks. Developer can then sweep the 20 papers.

## Out of scope

- ORCIDs for the *current paper's* authors (Daniel + co-authors).
  Those are already in `main.tex` via `\orcidlink`. This issue is
  about the cited papers' authors, not us.
- Author affiliations -- handled by the parallel ROR issue
  (`issue-0005.md`).

## Acceptance criteria (for when this unblocks)

1. Each `ScholarlyArticle` in the corpus has a `schema:author` link
   to one or more `schema:Person` nodes.
2. For each `schema:Person` whose ORCID can be looked up, record
   `schema:identifier <https://orcid.org/0000-...>`.
3. For authors without an ORCID (or where the ORCID is not
   publicly findable), add `rdfs:comment` noting it.
4. Round-trip on all 20 paper canonicals PASS.
5. Update the worked example in
   `sections/appendix-examples.tex` (Kumar 2025) to show the
   author block in its new structured form.

## Notes

- ORCIDs for cited papers' authors are usually findable on the
  publisher landing page (Crossref's API also returns them).
- ANI/ANI-1ccx authors (Justin Smith, Adrian Roitberg, Olexandr
  Isayev) are easy targets: they all have ORCIDs in the public
  literature.
- The Behler-Parrinello, Csányi, Drautz authors all have ORCIDs.
