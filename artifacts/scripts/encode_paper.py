#!/usr/bin/env python3
"""Generate a per-paper KG file from its encoding input (artifacts/kg/encoding/).

Input (committed, hand-written by the encoder):
  artifacts/kg/encoding/specs/<id>.yaml  the facts extracted from the paper,
                                         organised by the 12 questions
  artifacts/kg/encoding/bib/<id>.json    author metadata deposited with the
                                         DOI (Crossref or DataCite), cached
Output (generated; the canonical artefact):
  artifacts/kg/papers/<id>.ttl           Turtle, ending with the result-label
                                         block of add_result_labels.py

The spec format, including the fields that are kept in the input only
until the schema has terms for them (evaluation role and data, base
model, timings, source locations), is described in
artifacts/kg/encoding/README.md. Method and model names come from
artifacts/kg/methods-registry.csv (artifacts/kg/METHODS.md).

Usage:
  encode_paper.py <id> ...       regenerate these papers
  encode_paper.py --check [id]   write nothing; exit 1 if a generated file
                                 differs from the committed one (all specs
                                 when no id is given)
  encode_paper.py --new <id>     start a spec from the corpus manifest row
                                 (../corpus/manifest.csv) and fetch the
                                 author metadata into bib/<id>.json
Generation reads only committed files: no network, no corpus.
"""
import csv
import json
import os
import re
import sys
import unicodedata
import urllib.request
from decimal import Decimal

from ruamel.yaml import YAML

from add_result_labels import block_for

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
KG = os.path.join(ROOT, "artifacts", "kg")
ENC = os.path.join(KG, "encoding")
MANIFEST = os.path.join(ROOT, "..", "corpus", "manifest.csv")

VOCAB_LIBS = "VASP CASTEP QuantumESPRESSO FHIaims Gaussian ORCA MLIP QUIP MACE NequIP Allegro TorchANI NeuroChem M3GNet CHGNet DeePMDkit SchNet RuNNer PACE".split()
VOCAB_XC = "LDA PW91 PBE PBE0 HSE06 SCAN omegaB97X wB97X".split()
VOCAB_PP = "PAW Ultrasoft NormConserving".split()
VOCAB_WF = "HF MP2 CCSD CCSDT DLPNO_CCSDT CASPT2 NEVPT2".split()
VOCAB_BASIS = "NAOIntermediate NAOTier1 NAOTier2 LAPW".split()
VOCAB_HP = "cutoffRadius angularCutoff minInteratomicDistance momentLevel bodyOrder numLayers numFeatures numRadialBasis numAngularBasis learningRate batchSize numEpochs numSparseConfigs".split()
VOCAB_SIM = "MolecularDynamics MonteCarlo GeometryOptimization PhononCalculation ThermodynamicIntegration NudgedElasticBand".split()
PROPS = {"Energy", "Forces", "Stresses", "Virials"}
PROV = {"Published", "InHouse", "Augmented"}
MTYPE = {"MAE", "RMSE", "R2"}
MPROP = {"Energy": "EnergyProperty", "Force": "ForceProperty", "Stress": "StressProperty"}
UNITS = {
    "meV/atom": "mlips:MilliEV-PER-ATOM", "meV/A": "mlips:MilliEV-PER-ANGSTROM",
    "meV": "mlips:MilliEV", "kcal/mol/A": "mlips:KiloCAL-PER-MOL-ANGSTROM",
    "eV/A": "unit:EV-PER-ANGSTROM", "eV": "unit:EV", "GPa": "unit:GigaPA",
    "kcal/mol": "unit:KiloCAL-PER-MOL", None: None,
}
# input-only fields (README): allowed values
ROLES = {"training", "validation", "test", "external", None}
SOURCE_FIELDS = ["rank", "year", "first_author", "title", "venue", "doi", "kg_relevance",
                 "arxiv_id", "pdf_version", "pdf_sha256"]


def load_yaml(path):
    with open(path, encoding="utf-8") as fh:
        return YAML(typ="safe", pure=True).load(fh)


def lit(s):
    s = re.sub(r"\s+", " ", str(s).strip())
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'


def val(v):
    """A value may be written as {v: <value>, loc: <source location>}."""
    return v["v"] if isinstance(v, dict) and "v" in v else v


def num(v, force=None):
    v = val(v)
    if isinstance(v, bool):
        return f'"{str(v).lower()}"^^xsd:boolean'
    if force == "double" or isinstance(v, float):
        t = format(Decimal(repr(v)), "f")
        if "." in t:
            t = t.rstrip("0").rstrip(".")
        return f'"{t}"^^xsd:double'
    if isinstance(v, int):
        return f'"{v}"^^xsd:integer'
    return lit(v)


def slug(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9]+", "", s)


def key(s):
    s = unicodedata.normalize("NFKD", str(s)).encode("ascii", "ignore").decode()
    return re.sub(r"[^A-Za-z0-9_.]+", "-", s).strip("-").replace(".", "_")


def registry():
    methods, models = {}, {}
    with open(os.path.join(KG, "methods-registry.csv"), newline="", encoding="utf-8") as fh:
        rows = list(csv.reader(fh))
    for raw in rows[1:]:
        assert len(raw) == len(rows[0]), f"registry row has {len(raw)} columns: {raw[:3]}"
    for row in (dict(zip(rows[0], r)) for r in rows[1:]):
        (methods if row["kind"] == "method" else models)[row["key"]] = row
    return methods, models


def dataset_keys():
    with open(os.path.join(KG, "datasets-registry.csv"), newline="", encoding="utf-8") as fh:
        return {r["key"] for r in csv.DictReader(fh)}


def generate(pid):
    spec = load_yaml(os.path.join(ENC, "specs", f"{pid}.yaml"))
    assert spec["id"] == pid, "spec id mismatch"
    row = spec["source"]
    bib_path = os.path.join(ENC, "bib", f"{pid}.json")
    bib = json.load(open(bib_path, encoding="utf-8")) if os.path.exists(bib_path) else {"source": None, "authors": []}
    methods_reg, models_reg = registry()
    E = lambda name: f"entity:{name}"
    L = lambda kind, k: f"entity:{kind}-{key(k)}-{pid}"
    o = []
    w = o.append

    def section(title):
        w("#" * 79)
        w(f"# {title}")
        w("#" * 79)
        w("")

    def node(subj, pairs):
        pairs = [(p, v) for p, v in pairs if v is not None and v != []]
        w(f"{subj}")
        for i, (p, v) in enumerate(pairs):
            if isinstance(v, list):
                v = " ,\n        ".join(v)
            w(f"    {p} {v} {';' if i < len(pairs) - 1 else '.'}")
        w("")

    # ---- header -----------------------------------------------------------
    authors = spec.get("authors") or bib["authors"]
    if not authors:
        sys.exit(f"{pid}: no authors: give `authors:` in the spec")
    for a in authors:
        fam = (a.get("family") or "").strip()
        letters = len(re.sub(r"[^A-Za-zÀ-ɏ]", "", fam))
        ok_single = letters == 1 and not fam.endswith(".") and len(a.get("given") or "") >= 3 and "." not in (a.get("given") or "")
        if (letters < 2 and not ok_single) or fam.endswith("."):
            sys.exit(f"{pid}: suspicious author family name {fam!r} (given {a.get('given')!r}): give `authors:` in the spec")
    title = spec.get("title") or bib.get("title") or row["title"]
    title = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", title)).strip()
    arx = str(row.get("arxiv_id") or "")
    ver = row["pdf_version"] + (f" arXiv:{arx}" if arx and row["pdf_version"] == "arxiv-preprint" else "")
    w("# Canonical Turtle for the protocol-derived encoding of:")
    w(f"#   {row['first_author']} et al. ({row['year']}). {title}.")
    w(f"#   {row['venue']}. doi:{row['doi']}" + (f"  arXiv:{arx}" if arx else ""))
    w("#")
    w(f"# Version read: {ver} (sha256 {str(row['pdf_sha256'])[:16]}...);")
    w("#   the DOI above is cited, numbers are those of the version read.")
    w(f"# Corpus rank {row['rank']} ({row['kg_relevance']}). Method identity follows")
    w("#   artifacts/kg/METHODS.md (registry: artifacts/kg/methods-registry.csv).")
    w(f"# Generated by artifacts/scripts/encode_paper.py from artifacts/kg/encoding/specs/{pid}.yaml.")
    w("#")
    for ln in str(spec["scope"]).strip().splitlines():
        w(f"# {ln}".rstrip())
    w("")
    for p, u in [("rdf", "http://www.w3.org/1999/02/22-rdf-syntax-ns#"), ("rdfs", "http://www.w3.org/2000/01/rdf-schema#"),
                 ("xsd", "http://www.w3.org/2001/XMLSchema#"), ("schema", "https://schema.org/"), ("mls", "http://www.w3.org/ns/mls#"),
                 ("unit", "http://qudt.org/vocab/unit/"), ("mlips", "https://w3id.org/mlips#"), ("entity", "https://w3id.org/mlips/entity/")]:
        w(f"@prefix {p}: <{u}> .")
    w("")

    # ---- Q1 ---------------------------------------------------------------
    section("Q1 -- Bibliographic identification")
    study, article = E(f"study-{pid}"), E(f"article-{pid}")
    node(study + " a mlips:BenchmarkStudy ;", [("rdfs:label", lit(spec["study_label"])), ("mlips:reportedIn", article)])
    persons, seen = [], set()
    for a in authors:
        fam, giv = a.get("family"), a.get("given")
        if a.get("orcid"):
            iri = f"<{a['orcid']}>"
        else:
            base = f"person-{slug(fam)}-{pid}"
            if base in seen:
                base = f"person-{slug(fam)}{slug(giv or '')}-{pid}"
            seen.add(base)
            iri = E(base)
        persons.append((iri, a))
    node(article + " a schema:ScholarlyArticle ;", [
        ("schema:sameAs", f"<https://doi.org/{row['doi']}>"),
        ("schema:datePublished", f'"{row["year"]}"^^xsd:gYear'),
        ("schema:name", lit(title)),
        ("schema:author", [p for p, _ in persons])])
    done = set()
    for iri, a in persons:
        if iri in done:
            continue
        done.add(iri)
        fam, giv = a.get("family"), a.get("given")
        node(iri + " a schema:Person ;", [
            ("schema:name", lit(f"{giv} {fam}" if giv else fam)),
            ("schema:givenName", lit(giv) if giv else None),
            ("schema:familyName", lit(fam)),
            ("schema:identifier", iri if a.get("orcid") else None)])

    # ---- Q2 ---------------------------------------------------------------
    section("Q2 -- Material system")
    mats = spec.get("materials") or {}
    for k, m in mats.items():
        node(L("mat", k) + " a mlips:MaterialSystem ;", [
            ("rdfs:label", lit(m["label"])),
            ("mlips:chemicalFormula", lit(m["formula"]) if m.get("formula") else None),
            ("mlips:materialClass", lit(m["class"]) if m.get("class") else None),
            ("mlips:microstructuralFeature", lit(m["feature"]) if m.get("feature") else None),
            ("rdfs:comment", lit(m["comment"]) if m.get("comment") else None),
            ("mlips:sameAsWikidata", f"<http://www.wikidata.org/entity/{m['wikidata']}>" if m.get("wikidata") else None)])
    if not mats:
        w("# No material system is characterised by the paper (see Q12).\n")

    # ---- Q3 / Q4 ----------------------------------------------------------
    refs = spec.get("reference") or {}
    section("Q3 -- Reference calculation method (type only; settings live in Q4)")
    CT = {"DFT": ("DFTCalculation", "DFTSettings", "hasDFTSettings", "usedDFTCode"),
          "WF": ("WaveFunctionCalculation", "WaveFunctionSettings", "hasWaveFunctionSettings", "usedReferenceCode"),
          "REF": ("ReferenceCalculation", "ReferenceSettings", "hasReferenceSettings", "usedReferenceCode")}
    for k, r in refs.items():
        w(f"{L('calc', k)} a mlips:{CT[r['type']][0]} .\n")
    if not refs:
        w("# No reference calculation is described by the paper (see Q12).\n")
    section("Q4 -- Reference settings + software code")
    extra = []

    def vocab(v, allowed, cls, kind):
        """vocabulary individual, or a paper-local candidate {local: label, comment:}"""
        if v is None:
            return None
        if isinstance(v, dict):
            iri = L(kind, v["local"])
            extra.append((iri + f" a mlips:{cls} ;", [("rdfs:label", lit(v["local"])),
                          ("rdfs:comment", lit(v["comment"]) if v.get("comment") else None),
                          ("mlips:candidateForVocabulary", f"mlips:{cls}")]))
            return iri
        assert v in allowed, f"{v} is not a vocabulary {cls}"
        return f"mlips:{v}"

    for k, r in refs.items():
        ct = CT[r["type"]]
        calc, st = L("calc", k), L("calc-settings", k)
        w(f"{calc} mlips:{ct[2]} {st} .\n")
        node(st + f" a mlips:{ct[1]} ;", [
            (f"mlips:{ct[3]}", vocab(r.get("code"), VOCAB_LIBS, "Library", "lib")),
            ("mlips:xcFunctional", vocab(r.get("xc"), VOCAB_XC, "XCFunctional", "xc")),
            ("mlips:pseudopotentialType", vocab(r.get("pp"), VOCAB_PP, "PseudopotentialType", "pp")),
            ("mlips:dftBasisSet", vocab(r.get("dft_basis"), VOCAB_BASIS, "DftBasisSet", "basis")),
            ("mlips:wfMethod", vocab(r.get("wf"), VOCAB_WF, "WfMethod", "wf")),
            ("mlips:basisSet", lit(r["basis"]) if r.get("basis") else None),
            ("mlips:energyCutoff", num(r["cutoff"], "double") if r.get("cutoff") is not None else None),
            ("mlips:kPointMesh", lit(r["kpoints"]) if r.get("kpoints") else None),
            ("rdfs:comment", lit(r["comment"]) if r.get("comment") else None)])
    for e in extra:
        node(*e)
    extra.clear()

    # ---- Q5 / Q6 ----------------------------------------------------------
    section("Q5 -- Training dataset characterisation")
    dss = spec.get("datasets") or {}
    samp = spec.get("sampling") or {}
    for k, d in dss.items():
        for pr in d.get("properties", []):
            assert pr in PROPS, pr
        if d.get("provenance"):
            assert d["provenance"] in PROV
        calcs = d.get("calc")
        calcs = [calcs] if isinstance(calcs, str) else (calcs or [])
        dftc = [L("calc", c) for c in calcs if refs[c]["type"] == "DFT"]
        refc = [L("calc", c) for c in calcs if refs[c]["type"] != "DFT"]
        node(L("ds", k) + " a mlips:TrainingDataset ;", [
            ("rdfs:label", lit(d["label"])),
            ("mlips:coversMaterial", [L("mat", m) for m in d.get("materials", [])]),
            ("mlips:coversProperty", [f"mlips:{p}" for p in d.get("properties", [])]),
            ("mlips:datasetProvenance", f"mlips:{d['provenance']}" if d.get("provenance") else None),
            ("mlips:numConfigurations", str(int(val(d["n"]))) if d.get("n") is not None else None),
            ("mlips:hasDFTCalculation", dftc), ("mlips:hasReferenceCalculation", refc),
            ("rdfs:comment", lit(d["comment"]) if d.get("comment") else None)])
        for m in d.get("materials", []):
            assert m in mats, f"dataset {k}: unknown material {m}"
    if not dss:
        w("# No training dataset is characterised by the paper (see Q12).\n")
    section("Q6 -- Sampling strategies")
    used = set()
    for k, d in dss.items():
        if d.get("sampling"):
            used |= set(d["sampling"])
            w(f"{L('ds', k)} mlips:samplingStrategy\n    " + " ,\n    ".join(L("sampling", s) for s in d["sampling"]) + " .\n")
    assert used == set(samp), f"sampling keys unused/undefined: {used ^ set(samp)}"
    for k, s in samp.items():
        node(L("sampling", k) + " a mlips:SamplingStrategy ;", [("rdfs:label", lit(s["label"])),
             ("rdfs:comment", lit(s["comment"]) if s.get("comment") else None)])
    if not samp:
        w("# No sampling strategy is described by the paper (see Q12).\n")

    # ---- Q7 ---------------------------------------------------------------
    section("Q7 -- MLIP method, components, implementation")
    hps = spec.get("hyperparameters") or {}

    def hp(k):
        if k in VOCAB_HP:
            return f"mlips:{k}"
        assert k in hps, f"unknown hyperparameter {k}"
        return L("hp", k)

    meths = spec.get("methods") or {}
    ext = spec.get("external_models") or []
    stub_methods = set()
    for x in ext:
        assert x in models_reg, f"external model {x} is not a registry model"
        if not models_reg[x]["origin"]:
            stub_methods.add(models_reg[x]["method"])
    for mk in list(meths) + [m for m in sorted(stub_methods) if m not in meths]:
        m = meths.get(mk) or {}
        assert mk in methods_reg, f"method {mk} is not a registry method"
        reg = methods_reg[mk]
        for s in m.get("sims", []):
            assert s in VOCAB_SIM, s
        node(E(reg["iri"]) + " a mlips:MLIPMethod ;", [
            ("rdfs:label", lit(reg["label"])),
            ("mlips:hasDescriptor", f"mlips:{reg['descriptor']}" if reg["descriptor"] else None),
            ("mlips:hasFunctionalForm", E(reg["form_iri"]) if reg["form_iri"] else None),
            ("mlips:hasLossFunction", L("loss", mk) if m.get("loss") else None),
            ("mlips:hasTrainingAlgorithm", L("alg", mk) if m.get("algorithm") else None),
            ("mlips:hasHyperparameter", [hp(h) for h in m.get("hp", [])]),
            ("mlips:hasImplementation", L("impl", mk) if m.get("impl") else None),
            ("mlips:supportsSimulation", [f"mlips:{s}" for s in m.get("sims", [])]),
            ("mlips:inferenceComplexity", lit(m["inferenceComplexity"]) if m.get("inferenceComplexity") else None),
            ("mlips:trainingComplexity", lit(m["trainingComplexity"]) if m.get("trainingComplexity") else None)])
        if reg["form_iri"]:
            node(E(reg["form_iri"]) + " a mlips:FunctionalForm ;", [("rdfs:label", lit(reg["form_label"]))])
        if m.get("loss"):
            node(L("loss", mk) + " a mlips:LossFunction ;", [("rdfs:label", lit(m["loss"]))])
        if m.get("algorithm"):
            node(L("alg", mk) + " a mls:Algorithm ;", [("rdfs:label", lit(m["algorithm"]))])
        if m.get("impl"):
            im = m["impl"]
            node(L("impl", mk) + " a mlips:Implementation ;", [
                ("mlips:implementedIn", vocab(im.get("lib"), VOCAB_LIBS, "Library", "lib")),
                ("mlips:version", lit(im["version"]) if im.get("version") else None)])
    seen_extra = set()
    for e in extra:
        if e[0] not in seen_extra:
            seen_extra.add(e[0])
            node(*e)
    for k, h in hps.items():
        node(L("hp", k) + " a mlips:Hyperparameter ;", [
            ("rdfs:label", lit(h["label"])),
            ("mlips:hyperparameterName", lit(h.get("name", k))),
            ("mlips:hyperparameterDatatype", f"xsd:{h.get('datatype', 'string')}"),
            ("mlips:candidateForVocabulary", "mlips:Hyperparameter")])
    if not meths and not stub_methods:
        w("# No MLIP method is trained or evaluated by the paper (see Q12).\n")

    # ---- Q8 / Q9 / Q11 ----------------------------------------------------
    runs = spec.get("runs") or {}
    section("Q8 -- Hyperparameter settings")
    declared_hp = {mk: set(m.get("hp", [])) for mk, m in meths.items()}
    for rk, r in runs.items():
        for h, v in (r.get("settings") or {}).items():
            assert h in declared_hp[r["method"]], f"run {rk}: {h} not in hp list of method {r['method']}"
            node(L("setting", f"{rk}-{h}") + " a mlips:HyperparameterSetting ;", [
                ("mlips:forHyperparameter", hp(h)), ("mlips:settingValue", num(v))])
    if not any(r.get("settings") for r in runs.values()):
        w("# No hyperparameter value is stated by the paper (see Q12).\n")
    section("Q9 -- MLIP run + trained model (Q11 training-cost properties inline)")
    model_iri = {}
    for rk, r in runs.items():
        assert r["method"] in meths, f"run {rk}: method {r['method']} not declared"
        assert "inferenceTimePerAtom" not in r and "inferenceHardware" not in r, \
            f"run {rk}: inference timings go in `timings:` (they sit on a BenchmarkResult)"
        if r.get("dataset"):
            assert r["dataset"] in dss, f"run {rk}: unknown dataset"
        bm = r.get("base_model")
        if bm is not None:
            assert isinstance(bm, dict) and (bm.get("registry") or bm.get("run") or bm.get("label")), f"run {rk}: base_model needs registry, run or label"
            assert not bm.get("registry") or bm["registry"] in models_reg, f"run {rk}: base_model registry key {bm.get('registry')} unknown"
            assert not bm.get("run") or bm["run"] in runs, f"run {rk}: base_model run {bm.get('run')} unknown"
        rg = models_reg[r["registry"]] if r.get("registry") else None
        if rg:
            assert rg["method"] == methods_reg[r["method"]]["iri"] and rg["origin"] == pid, f"run {rk}: registry row must have method {r['method']} and origin {pid}"
        run_iri = E(rg["run_iri"]) if rg else L("run", rk)
        model_iri[rk] = E(rg["iri"]) if rg else L("model", rk)
        node(run_iri + " a mlips:MLIPRun ;", [
            ("rdfs:label", lit(f"Training run of {rg['label']}") if rg else lit(r["label"])),
            ("mlips:appliesMethod", E(methods_reg[r["method"]]["iri"])),
            ("mlips:runsOn", L("ds", r["dataset"]) if r.get("dataset") else None),
            ("mlips:hasHyperparameterSetting", [L("setting", f"{rk}-{h}") for h in (r.get("settings") or {})]),
            ("mlips:gpuHours", num(r["gpuHours"], "double") if r.get("gpuHours") is not None else None),
            ("mlips:trainingDuration", num(r["trainingDuration"], "double") if r.get("trainingDuration") is not None else None),
            ("mlips:trainingHardware", lit(r["trainingHardware"]) if r.get("trainingHardware") else None),
            ("mlips:produces", model_iri[rk])])
        node(model_iri[rk] + " a mlips:TrainedModel ;", [
            ("rdfs:label", lit(rg["label"]) if rg else lit(r.get("model") or r["label"]))])
    for x in ext:
        reg = models_reg[x]
        if reg["origin"]:
            w(f"# {E(reg['iri'])} ({x}) is evaluated here; its run and model are declared in papers/{reg['origin']}.ttl.\n")
        else:
            w(f"# Registry stub for the externally trained model {x} (not trained in this paper).")
            node(E(reg["run_iri"]) + " a mlips:MLIPRun ;", [
                ("rdfs:label", lit(f"Training run of {reg['label']}")),
                ("mlips:appliesMethod", E(methods_reg[reg["method"]]["iri"])),
                ("mlips:produces", E(reg["iri"]))])
            node(E(reg["iri"]) + " a mlips:TrainedModel ;", [("rdfs:label", lit(reg["label"]))])
    if not runs and not ext:
        w("# No training run or trained model is reported by the paper (see Q12).\n")

    def model_ref(mk):
        if mk.startswith("ext:"):
            assert mk[4:] in ext, f"{mk} not listed in external_models"
            return E(models_reg[mk[4:]]["iri"])
        assert mk in runs, f"unknown run {mk}"
        return model_iri[mk]

    # ---- Q10 --------------------------------------------------------------
    section("Q10 -- Benchmark results (Q11 inference-cost properties inline)")
    results = spec.get("results") or []
    names = [L("result", r.get("key") or f"{i:02d}") for i, r in enumerate(results, 1)]
    assert len(set(names)) == len(names), "duplicate result keys"
    rkeys = {r.get("key") or f"{i:02d}": n for i, (r, n) in enumerate(zip(results, names), 1)}
    dkeys = dataset_keys()
    timed = {}
    for t in spec.get("timings") or []:
        model_ref(t["model"])
        if t.get("result") is None:
            continue
        assert t["result"] in rkeys, f"timing: unknown result {t['result']}"
        res = results[list(rkeys).index(t["result"])]
        rmodels = res["model"] if isinstance(res["model"], list) else [res["model"]]
        assert t["model"] in rmodels, f"timing on result {t['result']}: the result does not evaluate {t['model']}"
        assert t["result"] not in timed, f"two timings on result {t['result']}"
        timed[t["result"]] = t
    if results:
        w(f"{study} mlips:hasResult\n    " + " ,\n    ".join(names) + " .\n")
    for rk, name, r in zip(rkeys, names, results):
        assert r.get("role") in ROLES, f"result {rk}: role {r.get('role')!r} not in {sorted(x for x in ROLES if x)}"
        ed = r.get("eval_data")
        if isinstance(ed, dict) and ed.get("registry"):
            assert ed["registry"] in dkeys, f"result {rk}: eval_data registry key {ed['registry']} is not in datasets-registry.csv"
        model = [model_ref(mk) for mk in (r["model"] if isinstance(r["model"], list) else [r["model"]])]
        assert r["material"] in mats, f"result: unknown material {r['material']}"
        base = name[len("entity:result-"):]
        mnames = [f"entity:metric-{base[:-len(pid)-1]}-{j}-{pid}" for j in range(1, len(r["metrics"]) + 1)]
        t = timed.get(rk) or {}
        node(name + " a mlips:BenchmarkResult ;", [
            ("rdfs:comment", lit(r["comment"]) if r.get("comment") else None),
            ("mlips:evaluatesModel", model),
            ("mlips:targetMaterial", L("mat", r["material"])),
            ("mlips:hasAccuracyMetric", mnames),
            ("mlips:inferenceTimePerAtom", num(t["per_atom_us"], "double") if t.get("per_atom_us") is not None else None),
            ("mlips:inferenceHardware", lit(t["hardware"]) if t.get("hardware") else None)])
        for mn, met in zip(mnames, r["metrics"]):
            assert len(met) in (5, 6), f"metric needs [type, property, value, unit, label(, location)]: {met}"
            mtype, mprop, v, unit, label = met[:5]
            assert mtype in MTYPE and mprop in MPROP, met
            assert unit in UNITS, f"unit {unit}"
            node(mn + " a mlips:AccuracyMetric ;", [
                ("rdfs:label", lit(label)), ("mlips:metricType", f"mlips:{mtype}"),
                ("mlips:metricProperty", f"mlips:{MPROP[mprop]}"),
                ("mlips:metricValue", num(v, "double")),
                ("mlips:hasUnit", UNITS[unit])])
    if not results:
        w("# No energy/force/stress accuracy metric is reported in a form the schema captures (see Q12).\n")

    # ---- Q11 / Q12 --------------------------------------------------------
    section("Q11 -- Computational resources")
    w("# " + (str(spec.get("resources") or "The paper reports no training-cost or inference-cost figures.").strip().replace("\n", "\n# ")) + "\n")
    section("Q12 -- Gaps and ambiguities (prose; not triples)")
    for gp in spec.get("gaps") or ["None recorded."]:
        w("# - " + re.sub(r"\s+", " ", str(gp)).strip())
    w("# - Author affiliations are not encoded (ORCIDs are those deposited with the DOI metadata, source: %s)." % (bib.get("source") if not spec.get("authors") else "paper front matter"))
    w(f"# - Evaluation roles and data, base models, inference timings with their system sizes, and the source location of each value are recorded in the encoding input (artifacts/kg/encoding/specs/{pid}.yaml) until the schema has terms for them.")
    body = "\n".join(o).rstrip() + "\n"
    labels = block_for(body, pid)
    return body + ("\n" + labels + "\n" if labels else "")


def fetch_bib(doi):
    out = {"source": None, "title": None, "authors": []}
    hdr = {"User-Agent": "mlips-kg/0.2 (https://w3id.org/mlips)"}
    try:
        d = json.load(urllib.request.urlopen(urllib.request.Request("https://api.crossref.org/works/" + doi, headers=hdr), timeout=40))["message"]
        out["source"] = "crossref"
        out["title"] = (d.get("title") or [None])[0]
        for a in d.get("author", []):
            out["authors"].append({"given": a.get("given"), "family": a.get("family") or a.get("name"), "orcid": (a.get("ORCID") or "").replace("http://", "https://") or None})
    except Exception:
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request("https://api.datacite.org/dois/" + doi, headers=hdr), timeout=40))["data"]["attributes"]
            out["source"] = "datacite"
            out["title"] = d["titles"][0]["title"]
            for a in d.get("creators", []):
                orcid = None
                for ni in a.get("nameIdentifiers", []):
                    if "orcid" in (ni.get("nameIdentifierScheme") or "").lower():
                        v = ni["nameIdentifier"]
                        orcid = v if v.startswith("http") else "https://orcid.org/" + v
                out["authors"].append({"given": a.get("givenName"), "family": a.get("familyName") or a.get("name"), "orcid": orcid})
        except Exception as e:
            out["error"] = str(e)
    return out


def new_spec(pid):
    path = os.path.join(ENC, "specs", f"{pid}.yaml")
    if os.path.exists(path):
        sys.exit(f"{path} exists")
    with open(MANIFEST, newline="", encoding="utf-8") as fh:
        row = next((r for r in csv.DictReader(fh) if r["paper_id"] == pid), None)
    if row is None:
        sys.exit(f"{pid} not in {MANIFEST}")
    bib_path = os.path.join(ENC, "bib", f"{pid}.json")
    if not os.path.exists(bib_path):
        with open(bib_path, "w", encoding="utf-8") as fh:
            json.dump(fetch_bib(row["doi"]), fh, indent=1, ensure_ascii=False)
            fh.write("\n")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(f"id: {pid}\nsource:\n")
        for f in SOURCE_FIELDS:
            fh.write(f"  {f}: {json.dumps(int(row[f]) if f == 'rank' else row[f], ensure_ascii=False)}\n")
    print("started", path)


def main():
    args = sys.argv[1:]
    if args[:1] == ["--new"]:
        for pid in args[1:]:
            new_spec(pid)
        return 0
    check = args[:1] == ["--check"]
    ids = [a for a in args if a != "--check"]
    if check and not ids:
        ids = sorted(f[:-5] for f in os.listdir(os.path.join(ENC, "specs")) if f.endswith(".yaml"))
    bad = 0
    for pid in ids:
        out = os.path.join(KG, "papers", f"{pid}.ttl")
        text = generate(pid)
        if check:
            cur = open(out, encoding="utf-8").read() if os.path.exists(out) else None
            if cur != text:
                bad += 1
                print(f"{pid}: papers/{pid}.ttl differs from its generated version")
        else:
            with open(out, "w", encoding="utf-8") as fh:
                fh.write(text)
            print("wrote", os.path.relpath(out, ROOT), text.count("\n"), "lines")
    if check:
        print(f"checked {len(ids)} encoding inputs: {bad} generated file(s) differ")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
