# Dataset repo build pipeline.
#
# Targets:
#   make ontology         Regenerate mlips.{owl,ttl} from mlips.xhtml.
#   make roundtrip-check  Run check-roundtrip.sh on every paper in kg/papers/.
#   make listings         Run build-listings.sh on every paper.
#   make term-appendices  Generate the three term .tex files into dist/.
#   make figures          Render ontology figures into artifacts/figures/.
#   make release          ontology + roundtrip-check + listings + term-appendices + figures.
#   make clean            Remove generated outputs (keep canonical sources).

SAXON       ?= java -jar $(HOME)/bin/saxon-he.jar
RAPPER      ?= rapper
CONCON_ONTO ?= $(HOME)/code/software/concon-onto/code-repo/target/debug/concon-onto
EXTRACT_XSL ?= $(HOME)/code/software/concon-onto/code-repo/xslt/extract-owl.xsl

XHTML_SOURCE = artifacts/ontology/mlips.xhtml
OWL_FILE     = artifacts/ontology/mlips.owl
TTL_FILE     = artifacts/ontology/mlips.ttl

DIST_SECTIONS = dist/sections
LATEX_SECTIONS = $(DIST_SECTIONS)/appendix-classes.tex \
                 $(DIST_SECTIONS)/appendix-object-properties.tex \
                 $(DIST_SECTIONS)/appendix-data-properties.tex

PAPERS = $(notdir $(basename $(wildcard artifacts/kg/papers/*.ttl)))

.PHONY: all release ontology roundtrip-check listings term-appendices figures clean

all: release

# === Release: produce all vendor-able outputs ===

release: ontology roundtrip-check listings term-appendices figures
	@echo
	@echo "Release ready. From the paper repo, run:"
	@echo "  make sync-from-dataset DATASET_PATH=$$(pwd)"

# === Ontology pipeline (XHTML -> OWL -> TTL) ===
#
# Three-step build:
#   1. Saxon's extract-owl.xsl pulls term axioms out of the
#      <pre class="owl-xml"> CDATA blocks in the XHTML.
#   2. rapper converts the resulting RDF/XML to Turtle.
#   3. merge_rdfa_into_owl.py adds the ontology-header annotations
#      that live as RDFa in the XHTML body (dcterms:title,
#      dcterms:license, owl:versionIRI, vann:preferredNamespace*,
#      owl:imports, dcterms:creator/contributor, dcterms:publisher,
#      etc.) which the XSLT does not extract.
#
# Step 3 rewrites both .ttl and .owl from the merged graph, so the
# two serialisations stay in sync.

ontology: $(TTL_FILE)

$(OWL_FILE): $(XHTML_SOURCE)
	$(SAXON) -s:$(XHTML_SOURCE) -xsl:$(EXTRACT_XSL) -o:$(OWL_FILE)
	@echo "Generated $(OWL_FILE) (term axioms only)"

$(TTL_FILE): $(OWL_FILE) artifacts/scripts/merge_rdfa_into_owl.py
	$(RAPPER) -i rdfxml -o turtle $(OWL_FILE) > $(TTL_FILE) 2>/dev/null
	python3 artifacts/scripts/merge_rdfa_into_owl.py
	@echo "Merged RDFa header annotations into $(TTL_FILE) and $(OWL_FILE)"

# === Round-trip check on every paper ===

roundtrip-check:
	@for p in $(PAPERS); do \
	  echo "==> $$p" ; \
	  ./artifacts/kg/check-roundtrip.sh "$$p" || exit 1 ; \
	done
	@echo "All $(words $(PAPERS)) papers round-trip cleanly."

# === Per-paper Turtle-fragment listings ===

listings:
	@for p in $(PAPERS); do \
	  ./artifacts/kg/build-listings.sh "$$p" ; \
	done

# === LaTeX term appendices into dist/sections/ ===

term-appendices: $(LATEX_SECTIONS)

$(LATEX_SECTIONS) &: $(TTL_FILE)
	@mkdir -p $(DIST_SECTIONS)
	python3 artifacts/scripts/generate_term_appendix.py \
	  --output-dir $(DIST_SECTIONS) \
	  --ontology $(TTL_FILE) \
	  --skip-skeletons

# === Figures rendered from the ontology ===

figures: $(TTL_FILE)
	./artifacts/tools/render_figures.sh

# === Clean ===

clean:
	rm -f $(OWL_FILE) $(TTL_FILE)
	rm -rf dist/
	rm -rf artifacts/kg/listings/
	rm -rf artifacts/figures/
