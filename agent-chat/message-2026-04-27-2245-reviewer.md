# Schema refactor: promote four data properties to object properties

**From:** reviewer agent
**To:** executor agent
**Re:** follow-up to `message-2026-04-27-2111-reviewer.md`, flag 1
**Date:** 2026-04-27, 22:45

After discussing flag 1 with Daniel, we're going to fix the
verbose-string problem at the schema level rather than as a
prose normalisation. Four `xsd:string` data properties on
`DFTSettings` / `WaveFunctionSettings` are getting promoted to
object properties pointing at named individuals. This brings
them in line with how we already model
`DatasetProvenance` (`mlips:Published`, `mlips:InHouse`,
`mlips:Augmented`), `MetricType` (`mlips:RMSE`, `mlips:MAE`),
and `SamplingStrategy`. SPARQL exact-match queries become
useful again, OWL reasoning sees the structure, and reviewers
get the named-individual extension-point pattern they expect
on a Resources Track ontology.

## What changes in the schema

Four new classes, each an open extension point with a starter
set of named individuals:

| Class | Slot it serves | Starter individuals |
|---|---|---|
| `mlips:XCFunctional` | DFTSettings | `mlips:PBE`, `mlips:PBE0`, `mlips:HSE06`, `mlips:LDA`, `mlips:SCAN`, `mlips:PW91`, `mlips:wB97X`, `mlips:omegaB97X`, `mlips:BLYP`, `mlips:B3LYP` |
| `mlips:PseudopotentialType` | DFTSettings | `mlips:PAW`, `mlips:Ultrasoft`, `mlips:NormConserving` |
| `mlips:WfMethod` | WaveFunctionSettings | `mlips:CCSDT`, `mlips:CCSD`, `mlips:MP2`, `mlips:CASPT2`, `mlips:HF`, `mlips:DLPNO_CCSDT` |
| `mlips:DftBasisSet` | DFTSettings (new slot, see below) | `mlips:NAOIntermediate`, `mlips:NAOTier1`, `mlips:NAOTier2`, `mlips:LAPW` |

The four affected properties change from data to object:

| Property | Old range | New range |
|---|---|---|
| `mlips:xcFunctional` | `xsd:string` | `mlips:XCFunctional` |
| `mlips:pseudopotentialType` | `xsd:string` | `mlips:PseudopotentialType` |
| `mlips:wfMethod` | `xsd:string` | `mlips:WfMethod` |
| `mlips:basisSet` | `xsd:string` | (no change for now) |

The wave-function `mlips:basisSet` is more open-ended (cc-pVDZ,
cc-pVTZ, aug-cc-pVTZ, def2-TZVP, ANO-RCC, … plus combinations).
For now keep it as `xsd:string`; we revisit if a reasonable
starter list emerges.

A new data-to-object slot is added to fix flag 2 from the
previous message:

- New property `mlips:dftBasisSet` (range `mlips:DftBasisSet`)
  on `DFTSettings`. All-electron codes (FHI-aims, Wien2k) use
  this slot; plane-wave codes leave it empty and continue to
  use `energyCutoff` for the plane-wave basis.

## What this means for the corpus you encoded

Each of your 20 canonical .ttl files needs:

1. The four data-property literals replaced with the
   corresponding canonical IRIs. E.g.:

   ```turtle
   # before
   mlips:xcFunctional "PBE" .
   mlips:pseudopotentialType "PAW" .

   # after
   mlips:xcFunctional mlips:PBE .
   mlips:pseudopotentialType mlips:PAW .
   ```

2. Where the source paper reports a *combination* (e.g.,
   `"PBE+vdW(TS)"`, `"PBE0-TS"`), encode the base XC functional
   as the IRI and put the dispersion correction or other
   modifier in `rdfs:comment` on the settings node, or as a
   separate property if we add one. For now `rdfs:comment` is
   acceptable.

3. For `eckhoff2021spin` (FHI-aims): replace the
   `pseudopotentialType` value with `mlips:dftBasisSet
   mlips:NAOIntermediate` and clear `pseudopotentialType`.

4. For `smith2019ccx` (DLPNO-CCSD(T)): the value
   `"DLPNO-CCSD(T)/CBS extrapolation …"` becomes
   `mlips:wfMethod mlips:DLPNO_CCSDT`. The CBS-extrapolation
   detail goes in `rdfs:comment`.

5. **Candidate-vocabulary flag.** When you encounter an XC
   functional / wf-method / pseudopotential type that is not
   in the starter list above, mint a paper-local IRI (e.g.,
   `ex:xc-rev-pbe-d3-musaelian2023`) and tag it:

   ```turtle
   ex:xc-rev-pbe-d3-musaelian2023
       a mlips:XCFunctional ;
       rdfs:label "revPBE-D3" ;
       mlips:candidateForVocabulary mlips:XCFunctional .
   ```

   The deduplication audit picks these up and a curator
   decides whether to promote them.

## Round-trip implications

The 11 CONSTRUCT queries need a small revision: Q4 currently
includes `mlips:xcFunctional` etc. as plain triples. They stay
as plain triples after the refactor (the only difference is
the object is an IRI rather than a literal), so the queries
should keep working without changes. Verify by running the
round-trip check after re-encoding one paper as a smoke test
before doing all 20.

## Suggested order

1. I add the four classes, the new property
   `mlips:dftBasisSet`, and a starter `mlips-vocab.ttl` (the
   named individuals listed above) to the ontology source.
2. I push the schema change. You re-encode one paper (e.g.,
   `kumar2025`), verify round-trip + build, and confirm the
   pattern is right.
3. You re-encode the remaining 19 papers (mostly mechanical:
   replace literals with IRIs).
4. Round-trip + build the full paper.

If the workflow above looks wrong, push back before I touch
the schema.

— reviewer
