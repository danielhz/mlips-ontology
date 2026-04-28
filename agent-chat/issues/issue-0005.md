# Issue 0005: ROR identifiers for institutions

**Status:** blocked
**Assignee:** unassigned
**Created:** 2026-04-28
**Blocks:** none
**Blocked by:** same schema change as `issue-0004.md` (ScholarlyArticle/Person decomposition); ROR linking is a follow-up that adds `schema:Organization` nodes for affiliations.

## Summary

After the `ScholarlyArticle` -> `schema:Person` decomposition (see
`issue-0004.md`), a parallel decomposition can attach
`schema:affiliation` from each `schema:Person` to a
`schema:Organization` carrying a ROR identifier (Research
Organization Registry, https://ror.org). Wikidata also has entries
for major research institutions, but ROR is the dedicated registry
for research orgs and is what publishers and funders are
standardising on.

## Background

Institutions in the corpus are dominated by a small set: University
of Stuttgart (IMW + KI), ICAMS Ruhr-Universität Bochum, Cambridge
(Csányi group), CalTech (Bartók-Kondor), University of Florida
(ANI/Roitberg group), Los Alamos (Smith/Nebgen), Argonne, KIST,
Cambridge, Bochum. Most of these have ROR IDs.

This issue is structurally identical to `issue-0004.md` but for
institutions instead of people. They share the same blocker.

## Out of scope

- The current paper's institutions (Stuttgart KI + IMW, ICAMS
  Bochum). Those are in `main.tex` via the LNCS `\institute` block.
  This issue is about cited papers' institutions.

## Acceptance criteria (for when this unblocks)

1. Each `schema:Person` in the corpus has at least one
   `schema:affiliation` link to a `schema:Organization`.
2. For each `schema:Organization` whose ROR ID can be looked up,
   record `schema:identifier <https://ror.org/...>`.
3. Common institutions are promoted to canonical IRIs in
   `mlips-vocab.ttl` (or a sibling `mlips-orgs-vocab.ttl`) so the
   same institution doesn't get re-instantiated per paper -- same
   pattern as `issue-0002.md` for software.
4. Round-trip on all 20 paper canonicals PASS.

## Notes

- ROR IDs are short and stable: `https://ror.org/04vnq7t77` is
  University of Stuttgart, etc. Lookup via https://ror.org/search.
- Wikidata also covers these (e.g., University of Stuttgart is
  Q151075 on Wikidata) -- the encoding can carry both
  `schema:identifier <ror>` AND `mlips:sameAsWikidata <wd:Q...>`,
  giving cross-registry alignment.
- Sequencing: do not start this issue until both `issue-0004.md`
  is done AND the canonical-institution vocabulary section in
  `mlips-vocab.ttl` exists.
