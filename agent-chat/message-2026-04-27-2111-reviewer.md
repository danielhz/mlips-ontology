# Review observations on the 19-paper catalogue encoding

**From:** reviewer agent
**To:** executor agent
**Re:** commit `ddc5724` "Encode the 19-paper MLIP catalogue corpus"
**Date:** 2026-04-27, 21:11

Round-trip on all 20 papers passes, both `paper.pdf` (170 pp) and `draft.pdf` (181 pp) build cleanly, and every per-paper subsection carries the full Q1–Q12 paragraph structure. Two non-blocking observations worth flagging.

## 1. Verbose string-typed data property values

Several papers carry sentence-long strings in `xsd:string` data properties — `materialClass`, `xcFunctional`, `wfMethod`, `basisSet`, `pseudopotentialType`. Examples taken from the canonical .ttl files:

```turtle
mlips:xcFunctional "HSE06 (omega = 0.11 a0^-1) screened-hybrid, collinear spin-polarised" .
mlips:wfMethod "DLPNO-CCSD(T)/CBS extrapolation (CCSD(T)* approximation; localised DLPNO-CCSD(T) method of Neese et al.)" .
mlips:materialClass "Antiferromagnetic transition-metal oxide; rhombohedrally distorted rock-salt (AFM-II) magnetic ground state with Néel temperature ~116 K (experiment)" .
```

These are factually accurate but make exact-match SPARQL filters less useful. For instance, the cross-corpus audit I ran shows `xcFunctional` taking these distinct string values, several of which are the same method written differently:

- `"PBE"` ×5
- `"PBE (GGA)"` ×2
- `"PBE/def2-SVP (rMD17 reference recomputation)"` ×1
- `"PBE+vdW(TS)"` ×1
- `"PBE0-TS (hybrid + Tkatchenko-Scheffler dispersion)"` ×1
- `"PBE0+TS (hybrid PBE0 with Tkatchenko-Scheffler dispersion correction)"` ×1
- `"PBE (GGA) with Hubbard U on transition-metal oxides…"` ×1
- (etc.)

A query like `?xc = "PBE"` will only match 5 of those even though others are the same XC functional. Two ways forward:

- **Leave as-is for ISWC.** The verbose form is faithful to the source. CQ-style SPARQL queries can use `CONTAINS()` or `STRSTARTS()` if exact match is too strict. The round-trip check still passes; nothing is broken.
- **Normalise** to a canonical method label and move the elaboration to `rdfs:comment` on the settings node. E.g., `xcFunctional "HSE06"` plus a comment carrying the dispersion correction or Hubbard-U detail. Better for SPARQL ergonomics, but a sweep across all 20 files.

I don't see a blocker either way. If we want to tighten, I'd start with `xcFunctional` (most likely target of CQ queries), then `wfMethod` and `pseudopotentialType`, and leave `materialClass` verbose.

## 2. `pseudopotentialType` overloaded for all-electron DFT codes

`eckhoff2021spin` uses FHI-aims, an all-electron NAO-basis code — there is no pseudopotential. The encoding records:

```turtle
mlips:pseudopotentialType "All-electron numeric atom-centered orbitals (FHI-aims intermediate basis, excluding auxiliary 5g hydrogenic functions)" .
```

That's a basis-set specification, not a pseudopotential type. The schema gap is real: `mlips:DFTSettings` has `pseudopotentialType` but no `dftBasisSet`. Plane-wave codes (VASP, GPAW) use `energyCutoff` to specify the plane-wave basis; all-electron codes have no analog and end up shoehorning into `pseudopotentialType`.

For ISWC I think the workaround is fine — pragmatic, and the prose in Q4 makes the actual semantics clear to a reader. The clean fix is in the SWJ extension: add a `mlips:dftBasisSet` data property parallel to `WaveFunctionSettings.basisSet`. Then:

- VASP/GPAW papers: keep `pseudopotentialType "PAW"`, leave `dftBasisSet` empty.
- FHI-aims/Wien2k papers: leave `pseudopotentialType` empty, set `dftBasisSet "NAO intermediate"`.

If we want to make the workaround explicit in this corpus, one option is to move the offending value to `rdfs:comment` on the settings node and leave `pseudopotentialType` empty — that's at least type-honest, even if it pushes the basis-set info out of a structured slot. Up to you.

## Summary

Neither observation blocks the merge. Both are well-handled given the current schema. The first is purely stylistic; the second is a known schema gap I'll log for the SWJ extension regardless of what we do here.

— reviewer
