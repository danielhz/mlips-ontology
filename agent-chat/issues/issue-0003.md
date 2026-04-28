# Issue 0003: Wikidata sweep on `MaterialSystem` instances in the corpus

**Status:** open
**Assignee:** developer
**Created:** 2026-04-28
**Blocks:** none
**Blocked by:** none

## Summary

The corpus has 21 `mlips:MaterialSystem` instances across the 20
papers (lysogorskiy2021ace covers two systems, Cu and Si). Of those,
~9 carry `mlips:sameAsWikidata` triples -- about 43% coverage.
Sweep the remaining 12 and add `sameAsWikidata` where a Wikidata
entry exists.

## Background

Section 5.1 (Seeded KG) cites the corpus's diversity of material
systems (elemental crystals, intermetallics, Laves phases, magnetic
oxides, water, organic molecules, ...). Most of these have Wikidata
entries -- elements always do, common compounds usually do, well-
studied alloys (Ti-Al, Ni-Al, TiCr2) often do, dataset-derived
systems (QM9 benchmark, ANI-1 dataset) sometimes have entries via
their underlying chemistry rather than the dataset itself.

## Scope

The 21 `MaterialSystem` instances span:

- Elemental crystals: Si, Cu, Fe, W (all easy: Wikidata has element
  entries).
- Binary alloys/intermetallics: Ti-Al, Ti3Al, Ni-Al, TiCr2 Laves.
- Multicomponent: Ti-Al-V, Ti-Nb-Zr (related), Ni-Al alloys with
  defects, refractory HEA TaVCrW.
- Oxides: MnO (magnetic), water/ice polymorphs.
- Molecular: organic molecules over GDB-11/QM7-X chemical space.
- Universal: foundation-model coverage of Materials Project (MACE-MP-0,
  CHGNet, M3GNet) -- this last one has no single Wikidata entry by
  nature, treat as not-applicable.

## Acceptance criteria

1. For each of the 21 `MaterialSystem` instances, look up Wikidata
   for the chemical formula or material name. If a unique entry
   exists, add `mlips:sameAsWikidata <http://www.wikidata.org/entity/Q...>`.
2. For ambiguous cases (e.g., "TiAl" returns multiple entries
   covering the gamma phase, the alloy in general, etc.), pick the
   most generic appropriate entry and note the choice in
   `rdfs:comment`.
3. For "no entry exists" cases (e.g., the universal Materials Project
   coverage of foundation models), add `rdfs:comment` noting that no
   single Wikidata entry applies.
4. Round-trip on all 20 paper canonicals PASS.
5. After the sweep, target coverage: at least 18 of 21 `MaterialSystem`
   instances carry `sameAsWikidata`. (The three exceptions are likely
   the universal foundation-model coverage entries.)

## Notes

- The existing `kumar2025` MaterialSystem links to Q15724720 (Laves
  phase). That's a good sanity-check on the IRI format and the
  sameAsWikidata predicate.
- Element entries are typically the most reliable: Q670 for Si,
  Q753 for Cu, Q677 for Fe, Q2329 for W.
- Compound entries: some alloy entries are weak. For TaVCrW or
  similar HEAs, the entry may not exist; falling back to
  `sameAsWikidata` on individual element constituents is overkill --
  prefer to skip and note.
- If a search turns up several QIDs for the same physical thing (a
  common case for compounds), pick the chemistry-canonical one
  (instance-of "chemical compound") not a process-of-discovery or
  patent-holder one.
