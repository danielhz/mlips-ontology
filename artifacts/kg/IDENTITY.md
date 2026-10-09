# Entity identity in the per-paper KG: where instances are duplicated and what could identify them

`METHODS.md` fixes the identity of methods and pretrained models through a registry. This file looks at every other class: how much the same real-world thing is represented by several nodes after the population run over the 200-paper corpus, and which identifier could disambiguate each class. It is an analysis and a set of options, not a convention; nothing here has been applied to the graph. Written 2026-10-09 on the 198-file corpus (schema 0.1.2).

## Why duplication exists

Rule 9 of `METHODS.md` makes every node other than a registry method or model paper-local, with a `-<paper-id>` suffix. That was deliberate: two files can never merge two different things by accident. The price is that two files can also never merge the same thing. A cross-paper question ("which models were trained on MD17 ethanol", "what did this author publish", "which papers use CP2K") is answered today only by string matching on labels.

## How it was measured

`make duplicates-report` (`artifacts/scripts/report_duplicates.py`) loads all per-paper files and, per class, counts the instances that share a normalised label (`rdfs:label` or `schema:name`) with another instance of the same class. This is a **lower bound**: the same data set or material under two different labels is not seen, and a shared label is not always the same thing (two metrics both called "Force RMSE, training set" are different measurements). The last column below is therefore a judgement, made with knowledge of how each class was encoded.

| Concept | Nodes | Nodes sharing a label with another | Is it real duplication? |
|---|---|---|---|
| Person | 1009 | 281 | Yes. An author without an ORCID in Crossref gets one node per paper (Gábor Csányi 11 times; Jörg Behler, Ralf Drautz, Christoph Ortner, Weinan E 6 each). Name variants (initials, diacritics) make the true figure higher. |
| Material system | 452 | 100 | Yes. Each paper declares its own materials, so ethanol (MD17) exists 6 times and 3BPA 5 times; water, silicon, MPtrj crystals and OC20 systems recur under different labels. |
| Hyperparameter (paper-local candidates) | 230 | 90 | Yes. "Deep Potential fitting network sizes" 11 times, "embedding network sizes" 9, "number of training steps" 8, "maximum rotation order l_max" 7. |
| Exchange-correlation functional (paper-local) | 50 | 33 | Yes. B3LYP 4 times; PBE-D3, RPBE-D3, r2SCAN, SRP48 3 each; also PBEsol, BLYP-D3, omegaB97M-D3. |
| Library / code (paper-local) | 55 | 28 | Yes. CP2K 8 times, Psi4 and SevenNet 4, LAMMPS 3; also GPAW, ABINIT, SIESTA. |
| DFT basis set (paper-local) | 33 | 19 | Yes. 6-31G(d) 7 times, def2-TZVPPD and 6-31G(2df,p) 3 each. |
| Training data set | 449 | 2 | Yes, but hidden. MD17, rMD17, MPtrj, OC20, SPICE, ANI-1x, 3BPA and QM9 each exist as many nodes with different labels (subset sizes and splits are part of the label), so label matching does not see it. |
| Sampling strategy | 333 | 18 | Partly. A few generic descriptions recur ("published data set used as provided"); most are genuinely paper-specific prose. |
| Loss function, training algorithm | 242 | 23 | Hardly. Free-text descriptions; the few repeats come from one paper describing several methods the same way. |
| Accuracy metric | 2051 | 857 | No. Labels repeat, but each node is a different measurement. |
| Trained model, run | 927 each | 4 | No (two legacy-era label collisions inside one file). Cross-paper models are handled by the registry. |

Ranking by how much it matters:

1. **Persons** are the largest case in absolute terms and the only one where two nodes certainly denote the same real-world thing.
2. **Material systems and training data sets** do the most damage to the competency questions, because results on the same benchmark cannot be joined across papers. Data sets are the worst hidden case.
3. **Paper-local vocabulary candidates** (hyperparameters, functionals, codes, basis sets) have the highest duplication rate, half to two thirds of their nodes, and are the cheapest to fix: promote the recurring ones into the controlled vocabulary.

Methods and pretrained models are absent from this list for the 178 files encoded under `METHODS.md`. The 20 legacy files still carry the duplicates listed there (four MTP method nodes, `entity:MACE-MP-0` beside `entity:MACE`).

## Which identifier could disambiguate each concept

| Concept | Natural identifier | Fallback and caveats |
|---|---|---|
| Person | ORCID | Where missing: Wikidata QID, or an OpenAlex or DBLP author identifier. Never the name alone. Many authors of older papers have no ORCID in Crossref metadata, so this needs a lookup step, not just a better parser. |
| Training data set | DOI of the deposit (Zenodo, figshare, Materials Cloud, ColabFit), with its version | Older sets (MD17, ANI-1x) have no deposit DOI: use the DOI of the introducing paper plus the set name. A subset ("1000 samples of MD17 ethanol") is not a new identity; it should point to the parent set and state the split. |
| Material system | Depends on what it is: InChIKey (or PubChem CID) for a molecule; a Materials Project, ICSD or COD entry for a specific crystal phase; a Wikidata QID for a substance in general | Many material systems in papers are composites or families ("H2 on Cu surfaces", "the Li-P-S system", "alloys of 53 elements") and have no external identifier. Those need a local registry entry whose components carry the external identifiers. |
| Exchange-correlation functional | Libxc identifier | Dispersion corrections (D2, D3, vdW-TS) should be a separate attribute, otherwise PBE and PBE-D3 stay distinct by accident. Reparametrised functionals such as SRP48 have no Libxc identifier and stay local. |
| Basis set | Basis Set Exchange name | Code-specific sets (FHI-aims "tight", CP2K MOLOPT) are identified by code plus name. |
| Library / code | Wikidata QID or the canonical repository URL; a Software Heritage identifier or release DOI for a version | The code and its version are two things; today both sit in one node with a free-text version string. |
| Hyperparameter | None external: the `mlips:` vocabulary IRI is the identifier | The parameter key in the implementing package (for example DeePMD-kit `rcut_smth`) works as an alias for matching, not as an identity, because the same concept has different keys in different codes. |
| Pretrained model | The checkpoint identifier as published (release tag, file name, repository URL), ideally with a file hash | This is what the registry already uses. A paper that does not state it cannot be linked; guo2026battery (SI Table S1) is the best single source of identifiers met so far. |
| Method | Registry IRI, anchored on the DOI of the introducing paper | In place (`methods-registry.csv`, column `origin`). |
| Sampling strategy | None; these are descriptions | Only the recurring generic ones merit vocabulary terms. |
| Accuracy metric | Not an entity to disambiguate | It is identified by its context: model, test set, property, metric type. |

Two of these are harder than the table suggests. For **materials**, no single identifier scheme covers molecules, crystals and composite systems, so a registry is unavoidable; the external identifiers attach to its entries and their components. For **data sets**, the identifier exists in principle, but most papers do not cite it, so the mapping from a paper's wording to a DOI has to be curated by hand once per data set.

## Options, in order of cost

- **Promote recurring candidates into the vocabulary.** Hyperparameters, functionals, codes and basis sets that several papers use are already marked `mlips:candidateForVocabulary`; the report above gives the frequency list. This is a schema (vocabulary) change, so it belongs to a 0.2.0 round, after which the affected files are regenerated.
- **A registry for data sets and one for materials**, built like `methods-registry.csv`: canonical IRI, label, external identifier, aliases to search, and a gate that rejects a paper-local node whose label matches an alias. The 449 data-set nodes would have to be mapped once; most belong to a few dozen published sets.
- **Persons**: resolve ORCIDs for the 800-odd distinct names (Crossref often lacks them; OpenAlex has more), then mint one node per ORCID. This needs network lookups and a review of ambiguous names; it does not need a schema change.
- **Leave it** and answer cross-paper questions by label matching. Acceptable for a demo, misleading for any count that is quoted.

None of this is started. Each option changes the convention of `METHODS.md` rule 9 and moves numbers that the papers may quote, so it waits for a decision.
