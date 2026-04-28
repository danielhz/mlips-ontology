# Issue 0002: Promote software libraries to canonical IRIs and add Wikidata links

**Status:** open
**Assignee:** developer
**Created:** 2026-04-28
**Blocks:** none
**Blocked by:** none

## Summary

The corpus has 39 `mlips:Library` instances across the 20 paper
canonicals -- mostly common simulation software (VASP, MLIP-2,
PySCF, ORCA, GPAW, FHI-aims, LAMMPS, Quantum Espresso, MACE, NequIP,
Gaussian, etc.) -- and currently zero of them carry Wikidata links.
Most of these packages have well-established Wikidata entries.

This issue does two things:
1. Promote software packages to canonical IRIs in `mlips-vocab.ttl`
   (e.g., `mlips:VASP`, `mlips:MLIP2`, `mlips:PySCF`, ...).
2. Add `mlips:sameAsWikidata` to each canonical software IRI.

Combined with the existing per-paper `Implementation` nodes (which
record the version), this gives "the software is X, the version is
2.1" structure: the canonical software is shared across papers and
links to Wikidata; the per-paper Implementation node carries the
specific version literal.

## Background

The same software is currently re-instantiated paper-by-paper as
`ex:lib-vasp`, `ex:lib-vasp-foo2024`, `ex:lib-mlip`, etc. This is a
case-1 entity-identity split: the same real-world software is being
represented by different IRIs across papers. See
`sections/appendix-internal-entity-iris.tex` for the broader
discussion of split vs collision.

Promoting to canonical IRIs solves both problems (Wikidata
alignment + entity-identity split) in one pass.

## Scope

Software packages currently appearing in the corpus -- check the
`Library` instances under each `usedDFTCode` / `usedReferenceCode` /
`implementedIn` link:

- DFT codes: VASP, GPAW, FHI-aims, Quantum Espresso, CASTEP,
  Gaussian (the molecular code, not Carl).
- Wave-function codes: ORCA, PySCF, Molpro.
- MLIP packages: MLIP-2 (Novikov), MACE, NequIP, Allegro, ANI/TorchANI,
  SchNetPack, DeePMD-kit, M3GNet, CHGNet, GAP/QUIP, ACE/PACE.
- MD/glue: LAMMPS, ASE.

Most of these are in Wikidata. The promotions go into a new section
in `mlips-vocab.ttl` ("Software packages") with each IRI carrying
`a mlips:Library`, `rdfs:label`, `rdfs:comment`, and
`mlips:sameAsWikidata <http://www.wikidata.org/entity/Q...>` where
applicable.

## Acceptance criteria

1. Add a "Software packages" section to `mlips-vocab.ttl` with one
   canonical IRI per software package observed in the corpus. Each
   carries: `a mlips:Library`, `rdfs:label`, optional
   `mlips:sameAsWikidata`, optional `rdfs:comment`.
2. Sweep the 20 paper canonicals: replace paper-local
   `ex:lib-<name>-<paper-id>` (or `ex:lib-<name>`) IRIs with the
   canonical `mlips:<Name>` IRIs from the vocabulary.
3. Per-paper `Implementation` nodes keep their per-paper IRIs and
   their version literals: only the *implementedIn* target changes
   from a paper-local Library to the canonical one.
4. Round-trip on all 20 paper canonicals PASS.
5. `make paper && make draft` clean.

## Notes

- A package without a Wikidata entry is fine; just skip
  `sameAsWikidata` and add `rdfs:comment "no Wikidata entry as of
  YYYY-MM-DD"` so curators don't re-check repeatedly.
- The `Implementation` -> `Library` distinction the ontology already
  carries is exactly the right shape: the *Library* is the canonical
  thing in the vocabulary (with a Wikidata link); the *Implementation*
  is per-paper and per-version.
- Watch out for software with multiple Wikidata QIDs (Gaussian the
  software vs Gaussian the family of basis functions). Pick the
  software entry, not the math object.
