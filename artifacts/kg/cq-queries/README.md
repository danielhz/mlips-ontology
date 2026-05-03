# Competency Question SPARQL Queries

The nine SPARQL queries that realise the competency questions
(CQ1--CQ9) listed in §3 of the paper. Each file `cqNN.rq` is a
ready-to-run SELECT query. The companion script
`run-all.sh` executes each query against a merged corpus of the
ontology + vocabulary + 20 paper canonical .ttl files, reports the
row count and wall-clock time, and produces the table that lands in
§8.1 of the paper.

To regenerate the §8.1 numbers after a schema or KG change:

```sh
./artifacts/kg/cq-queries/run-all.sh
```

## Files

| File      | Question                                                                   |
|-----------|----------------------------------------------------------------------------|
| `cq01.rq` | Method hyperparameters (name, datatype, default).                          |
| `cq02.rq` | Implementations and their library + version per method.                    |
| `cq03.rq` | Training datasets with their DFT settings for a given material.            |
| `cq04.rq` | Provenance of each training dataset.                                       |
| `cq05.rq` | Dataset size (configurations) and covered properties.                      |
| `cq06.rq` | Published benchmarks of a method on a material, with accuracy metrics.    |
| `cq07.rq` | Ranking method/hyperparameter combinations by RMSE for a material.        |
| `cq08.rq` | Simulation types performed with each method.                               |
| `cq09.rq` | Method efficiency: inference complexity + GPU hours + inference time.     |

CQ3, CQ6, CQ7 are also reproduced inline in §8.1 of the paper as
examples of cross-module queries; CQ1, CQ2, CQ4, CQ5, CQ8, CQ9 are
in Appendix `appendix-sparql.tex`.
