# Vendored imports

Local copies of the two ontologies that `mlips.ttl` imports (`owl:imports`), so that the consistency checks run offline and reproducibly (`make consistency-check`, `make reason-kg`; see issue #1). They are not edited here.

| File | Ontology IRI | Source | Retrieved |
|---|---|---|---|
| `prov-o.ttl` | `http://www.w3.org/ns/prov-o` | https://www.w3.org/ns/prov-o.ttl (PROV-O, W3C Recommendation 2013-04-30) | 2026-10-14 |
| `mls.ttl` | `http://www.w3.org/ns/mls` | https://www.w3.org/ns/mls.ttl (W3C ML-Schema) | 2026-10-14 |

Both are W3C documents, redistributed under the W3C Software and Document License. `catalog-v001.xml` maps the ontology IRIs to these files for ROBOT/OWL API (`robot --catalog artifacts/ontology/imports/catalog-v001.xml ...`).
