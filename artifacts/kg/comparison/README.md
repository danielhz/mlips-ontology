# Comparator Coverage Mapping

Per-cell justification for Table 4 of the paper (§8.4
"Comparison with Existing Ontologies"). For each
(CQ, comparator) pair, this file records which classes and
properties of the comparator a SPARQL query would need in order
to answer the CQ, and which of those the comparator actually
declares.

The classification is TBox-level: we ask "does this comparator's
vocabulary support a query that would answer this CQ?", not
"does any deployed dataset against this comparator answer this
CQ?". A cell is **answerable** (●) when every required term is
declared, **partially answerable** (○) when superclass reasoning
approximates the question (e.g., a generic `Calculation` class
subsumes our `DFTCalculation` but does not declare DFT-specific
data properties), and **not answerable** (—) when the required
terms are absent.

## Comparators

| Short name | Full name | Source |
|---|---|---|
| ML-Schema | W3C Machine Learning Schema | <http://www.w3.org/ns/mls#> |
| MDO | Materials Design Ontology | <https://w3id.org/mdo/core/> |
| CMSO/ASMO | Crystallographic + Atomistic Simulation Methods Ontology | <https://purls.helmholtz-metadaten.de/cmso/> |
| EMMO | European Materials Modelling Ontology | <https://emmo-repo.github.io/> |
| PMDco | Platform Material Digital ontology | <https://w3id.org/pmd/co/> |
| Croissant | MLCommons Croissant (dataset metadata, v1.0) | <http://mlcommons.org/croissant/> |

## Per-CQ analysis

### CQ1: Algorithm hyperparameters (name, datatype, range, default)

Required terms: a class for *Algorithm* (or *Method*); a class
for *Hyperparameter*; a property linking algorithm to
hyperparameter; data properties for the hyperparameter's name,
datatype, and (optionally) default and range.

| Comparator | Has Alg.? | Has Hp? | hasHp link? | Hp metadata? | Verdict |
|---|---|---|---|---|---|
| ML-Schema   | `mls:Algorithm` ✓ | `mls:HyperParameter` ✓ | `mls:hasHyperParameter` ✓ | `rdfs:label` only; no datatype, no default | ○ |
| MDO         | — | — | — | — | — |
| CMSO/ASMO   | — | — | — | — | — |
| EMMO        | — (model concept differs) | — | — | — | — |
| PMDco       | — | — | — | — | — |
| Croissant   | — | — | — | — | — |

### CQ2: Implementations and library versions

Required: *Implementation* class linked to *Library* / software,
with a version literal.

| Comparator | Verdict | Note |
|---|---|---|
| ML-Schema | ○ | `mls:Implementation` exists but no native version property |
| MDO       | — | no Implementation concept |
| CMSO/ASMO | — | similar |
| EMMO      | — | software not modelled at this granularity |
| PMDco     | — | similar |
| Croissant | — | versions the dataset (schema:version), not software libraries implementing a method |

### CQ3: Training data + DFT settings

Required: *TrainingDataset*, link to *MaterialSystem*,
*DFTCalculation*, and DFT-specific settings (XC functional,
energy cutoff, pseudopotential type).

| Comparator | Verdict | Note |
|---|---|---|
| ML-Schema | — | no DFT/calculation concepts |
| MDO       | ○ | has Calculation + Structure; no DFT-specific setting properties |
| CMSO/ASMO | ○ | similar; ASMO has the calculation graph but not the DFT-setting fields |
| EMMO      | ○ | has top-level Calculation concept |
| PMDco     | ○ | aligns with EMMO; same level |
| Croissant | ○ | schema.org Dataset + cr:RecordSet describe the dataset/distribution; no DFT code or settings terms |

### CQ4: Dataset provenance (published / in-house / augmented)

Required: a `datasetProvenance` enumeration (Published,
InHouse, AugmentedFrom).

| Comparator | Verdict | Note |
|---|---|---|
| ML-Schema, MDO, CMSO/ASMO, EMMO, PMDco | — | none of these model this enumeration |
| Croissant | ○ | schema.org creator / publisher / citeAs / isBasedOn approximate provenance, but not the Published / InHouse / Augmented categories |

### CQ5: Dataset size + property coverage + sampling strategy

Required: count of configurations, set of covered physical
properties (energies/forces/stresses), sampling-strategy
enumeration.

| Comparator | Verdict | Note |
|---|---|---|
| ML-Schema, MDO, CMSO/ASMO, EMMO, PMDco | — | none model property-coverage at this granularity |
| Croissant | ○ | cr:RecordSet / cr:Field / dataType give generic field coverage; no configuration-count property and no sampling-strategy enumeration |

### CQ6: Published benchmarks

Required: *BenchmarkStudy* + *BenchmarkResult* + link to
*TrainedModel* + *AccuracyMetric*.

| Comparator | Verdict | Note |
|---|---|---|
| All (incl. Croissant) | — | the benchmark--method--metric triangle is unique to ours |

### CQ7: Accuracy ranking across method/hyperparameter combinations

Required: comparable benchmark results across methods, ordered
by an accuracy metric.

| Comparator | Verdict | Note |
|---|---|---|
| All (incl. Croissant) | — | no comparator declares comparable cross-method benchmark structure |

### CQ8: Simulation types supported by a method

Required: enumeration of simulation types (MD, MC, geometry
opt, phonon, thermo. integration); link from *Algorithm* to
*SimulationType*.

| Comparator | Verdict | Note |
|---|---|---|
| ML-Schema | — | not modelled |
| MDO       | — | not modelled |
| CMSO/ASMO | ○ | ASMO declares simulation-method classes that approximate this |
| EMMO      | ○ | similar approximation |
| PMDco     | — | not modelled |
| Croissant | — | simulation types not modelled |

### CQ9: Method efficiency (asymptotic complexity + compute cost)

Required: an asymptotic *inferenceComplexity* on the method, plus
measured *gpuHours* (on the run) and *inferenceTimePerAtom* (on the
trained model).

| Comparator | Verdict | Note |
|---|---|---|
| All (incl. Croissant) | — | no comparator declares compute-cost or asymptotic-complexity vocabulary (cf. the MLIPRun compute-cost note below); Croissant models dataset metadata, not method efficiency |

### Auxiliary axes (rows below the line in Table 4)

**Training-run provenance.** ML-Schema's `mls:Run` provides
training-run context (executes, hasInput, hasOutput) that
predates and complements our `MLIPRun`; we link the two via
`rdfs:subClassOf`-style alignment. Our schema gains compute-cost
data properties on `MLIPRun` that `mls:Run` does not have.

**Crystal structure.** MDO/CMSO/EMMO/PMDco each carry
detailed crystal-structure modelling (lattice parameters,
Wyckoff positions, space groups) that our `MaterialSystem`
deliberately does not duplicate. The `CrystalMaterial` IRI
scheme designed in
`appendix-internal-crystal-materials.tex` will use these
ontologies as the targets of `rdfs:subClassOf` alignment.
