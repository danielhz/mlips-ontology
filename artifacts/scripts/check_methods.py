#!/usr/bin/env python3
"""Method-identity gate for the per-paper KG (see artifacts/kg/METHODS.md).

Checks every artifacts/kg/papers/<id>.ttl that is not one of the 20
legacy files against artifacts/kg/methods-registry.csv:

  1. every mlips:MLIPMethod subject, and every mlips:appliesMethod
     target, is a registry method;
  2. a registry method carries exactly the registry label, and only the
     registry descriptor / functional form (identity triples are
     registry-fixed and repeated verbatim, never paper-specific);
  3. every mlips:evaluatesModel target is a TrainedModel declared in the
     same file or a registry model;
  4. a registry model whose run is re-declared in the file (a "stub")
     uses the registry run IRI, label and method;
  5. every other subject in the entity: namespace ends in -<paper-id>,
     so paper-local nodes of different files can never merge;
  6. no paper file asserts mlips:derivedFromMethod (method derivation is
     registry-fixed and generated into shared/methods.ttl).

In shared/methods.ttl, every method at either end of a derivation edge
must be declared a mlips:MLIPMethod with exactly its registry label, so
that no endpoint reaches the published graph untyped or unlabelled.

It also checks the registry itself: every key in the derived_from column
is a registry method, each such row names its derived_from_source, and
no method derives from itself, directly or not. Checked for all files,
legacy ones included: rule 6.

Exit status 1 on any violation.
"""
import csv
import glob
import os
import sys

import rdflib
from rdflib.namespace import RDF, RDFS

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
KG = os.path.join(ROOT, "artifacts", "kg")
MLIPS = rdflib.Namespace("https://w3id.org/mlips#")
ENTITY = "https://w3id.org/mlips/entity/"

# Files encoded before the convention existed; listed in METHODS.md with
# what aligning each would take. They are not checked here.
LEGACY = {
    "bartok2010", "bartok2018si", "batatia2022", "batatia2024mp0",
    "batzner2022", "behler2007", "chen2022", "deng2023", "eckhoff2021spin",
    "gubaev2023", "kumar2025", "lysogorskiy2021ace", "musaelian2023allegro",
    "nitol2024nial", "qi2023", "schutt2018", "shapeev2016", "smith2017",
    "smith2019ccx", "wang2018dpkit",
}


def load_registry():
    methods, models = {}, {}
    with open(os.path.join(KG, "methods-registry.csv"), newline="") as fh:
        for row in csv.DictReader(fh):
            (methods if row["kind"] == "method" else models)[row["iri"]] = row
    return methods, models


def local(iri):
    return str(iri)[len(ENTITY):]


def parents(row):
    return [k for k in row["derived_from"].split("|") if k]


def derivation_errors(methods):
    """Registry-level checks of the derived_from / derived_from_source columns."""
    errs = []
    by_key = {m["key"]: m for m in methods.values()}
    for key, m in sorted(by_key.items()):
        for p in parents(m):
            if p not in by_key:
                errs.append(f"registry: {key} derived_from {p} is not a registry method key")
            elif p == key:
                errs.append(f"registry: {key} is derived from itself")
        if parents(m) and not m["derived_from_source"].strip():
            errs.append(f"registry: {key} has derived_from but no derived_from_source")
        if m["derived_from_source"].strip() and not parents(m):
            errs.append(f"registry: {key} has derived_from_source but no derived_from")

    def reaches(start, goal, seen):
        for p in parents(by_key[start]):
            if p == goal:
                return True
            if p in by_key and p not in seen:
                seen.add(p)
                if reaches(p, goal, seen):
                    return True
        return False
    for key in sorted(by_key):
        if any(p != key for p in parents(by_key[key])) and reaches(key, key, set()):
            errs.append(f"registry: {key} is in a derivation cycle")
    return errs


def check(path, methods, models):
    pid = os.path.basename(path)[:-4]
    g = rdflib.Graph().parse(path)
    errs = []
    shared = set(methods) | set(models)
    shared |= {m["form_iri"] for m in methods.values() if m["form_iri"]}
    shared |= {m["run_iri"] for m in models.values() if m["run_iri"]}

    for s in set(g.subjects(RDF.type, MLIPS.MLIPMethod)):
        name = local(s)
        if name not in methods:
            errs.append(f"method entity:{name} is not in the registry")
            continue
        reg = methods[name]
        labels = {str(o) for o in g.objects(s, RDFS.label)}
        if labels != {reg["label"]}:
            errs.append(f"entity:{name} label {sorted(labels)} != registry label")
        for o in g.objects(s, MLIPS.hasDescriptor):
            if str(o) != str(MLIPS[reg["descriptor"]]) or not reg["descriptor"]:
                errs.append(f"entity:{name} hasDescriptor {o} is not the registry descriptor")
        for o in g.objects(s, MLIPS.hasFunctionalForm):
            if not reg["form_iri"] or local(o) != reg["form_iri"]:
                errs.append(f"entity:{name} hasFunctionalForm {o} is not the registry form")
            elif {str(x) for x in g.objects(o, RDFS.label)} != {reg["form_label"]}:
                errs.append(f"entity:{reg['form_iri']} label differs from the registry")

    for run, m in g.subject_objects(MLIPS.appliesMethod):
        if local(m) not in methods and local(run).endswith("-" + pid):
            errs.append(f"appliesMethod target entity:{local(m)} is not a registry method")

    local_models = set(g.subjects(RDF.type, MLIPS.TrainedModel))
    for _, m in g.subject_objects(MLIPS.evaluatesModel):
        if m not in local_models and local(m) not in models:
            errs.append(f"evaluatesModel target entity:{local(m)} is neither local nor a registry model")

    for m in local_models:
        name = local(m)
        if name in models:
            reg = models[name]
            if {str(o) for o in g.objects(m, RDFS.label)} != {reg["label"]}:
                errs.append(f"registry model entity:{name} label differs from the registry")
            for run in g.subjects(MLIPS.produces, m):
                if local(run) != reg["run_iri"]:
                    errs.append(f"registry model entity:{name} produced by {local(run)}, registry says {reg['run_iri']}")
                if {local(o) for o in g.objects(run, MLIPS.appliesMethod)} != {reg["method"]}:
                    errs.append(f"registry run entity:{local(run)} does not apply entity:{reg['method']}")

    for s in set(g.subjects()):
        if isinstance(s, rdflib.URIRef) and str(s).startswith(ENTITY):
            name = local(s)
            if name not in shared and not name.endswith("-" + pid):
                errs.append(f"paper-local subject entity:{name} lacks the -{pid} suffix")
    return errs


def main():
    methods, models = load_registry()
    paths = sorted(glob.glob(os.path.join(KG, "papers", "*.ttl")))
    only = set(sys.argv[1:])
    bad = checked = 0
    for e in derivation_errors(methods):
        bad += 1
        print(e)
    for path in paths:
        pid = os.path.basename(path)[:-4]
        if only and pid not in only:
            continue
        if (None, MLIPS.derivedFromMethod, None) in rdflib.Graph().parse(path):
            bad += 1
            print(f"{pid}: asserts mlips:derivedFromMethod (registry-fixed; set derived_from in the registry)")
        if pid in LEGACY:
            continue
        checked += 1
        for e in check(path, methods, models):
            bad += 1
            print(f"{pid}: {e}")
    shared = os.path.join(KG, "shared", "methods.ttl")
    if os.path.exists(shared):
        g = rdflib.Graph().parse(shared)
        ends = {o for t in g.triples((None, MLIPS.derivedFromMethod, None)) for o in (t[0], t[2])}
        for e in sorted(ends):
            name = local(e)
            if (e, RDF.type, MLIPS.MLIPMethod) not in g:
                bad += 1
                print(f"shared/methods.ttl: derivation endpoint entity:{name} is not declared a mlips:MLIPMethod")
            labels = {str(o) for o in g.objects(e, RDFS.label)}
            if name not in methods or labels != {methods[name]["label"]}:
                bad += 1
                print(f"shared/methods.ttl: derivation endpoint entity:{name} lacks its registry label")
    print(f"checked {checked} files against {len(methods)} registry methods "
          f"and {len(models)} registry models: {bad} violations")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
