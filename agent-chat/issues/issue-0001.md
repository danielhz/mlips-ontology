# Issue 0001: Wikidata sweep on the controlled vocabulary (`mlips-vocab.ttl`)

**Status:** open
**Assignee:** developer
**Created:** 2026-04-28
**Blocks:** none
**Blocked by:** none

## Summary

The named individuals in `artifacts/kg/mlips-vocab.ttl`
(`mlips:PBE`, `mlips:HSE06`, `mlips:PAW`, `mlips:CCSDT`, etc.) are
referenced by every paper in the corpus but currently carry no
external identifiers. Add `mlips:sameAsWikidata` triples wherever a
Wikidata entry exists. One-time edit, applies forever, every paper
inherits the alignment transitively.

## Background

A cross-corpus audit found the entire `mlips-vocab.ttl` file has zero
`sameAsWikidata` triples. Section 5.1 (Seeded Knowledge Graph) of the
paper claims the corpus is part of the Linked Open Data cloud; without
vocabulary-level Wikidata alignment that claim is thin.

## Scope

The named individuals to consider:

- **`XCFunctional`**: PBE, PBE0, HSE06, LDA, SCAN, PW91, omegaB97X
  (and variant `wB97X`).
- **`PseudopotentialType`**: PAW, ultrasoft, norm-conserving.
- **`WfMethod`**: HF, MP2, CCSD, CCSDT, DLPNO_CCSDT, CASPT2, NEVPT2.
- **`DftBasisSet`**: NAO families, LAPW.

Not every concept will have a Wikidata QID; an individual without a
match is left without a `sameAsWikidata` triple (acceptable). The
target is "every QID-eligible individual is linked", not "every
individual is linked".

## Acceptance criteria

1. For each named individual in `mlips-vocab.ttl` that has a Wikidata
   entry, add a `mlips:sameAsWikidata <http://www.wikidata.org/entity/Q...>`
   triple.
2. For each named individual that does not have a clear Wikidata
   entry, add an `rdfs:comment` line stating "no Wikidata entry as
   of YYYY-MM-DD" so future curators don't waste time re-checking.
3. Round-trip on all 20 paper canonicals still PASS (the change
   touches only the vocabulary file, not the per-paper canonicals,
   so this should be automatic).
4. `mlips-vocab.ttl` parses cleanly with `rapper -i turtle`.

## Notes

- Wikidata QIDs to start from (sanity-check before committing):
  PBE could be Q4926830 (verify), PAW could be Q3358437 (verify),
  CCSD(T) is "coupled cluster" entry. Use Wikidata search; do not
  trust these from memory.
- If unsure between two QIDs, prefer the one that is the *concept*
  (the functional/method itself) rather than its inventor or its
  primary citation.
- This issue is independent of the per-paper corpus, so the
  developer can work on it in isolation without coordinating
  with the rest of the catalogue.
