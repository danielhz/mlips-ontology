SAXON = java -jar $(HOME)/bin/saxon-he.jar
RAPPER = rapper
CONCON_ONTO = $(HOME)/code/software/concon-onto/target/debug/concon-onto
EXTRACT_XSL = $(HOME)/code/software/concon-onto/xslt/extract-owl.xsl

# Source of truth
XHTML_SOURCE = artifacts/ontology/mlips.xhtml

# Generated from XHTML
OWL_FILE = artifacts/ontology/mlips.owl
TTL_FILE = artifacts/ontology/mlips.ttl
LATEX_SECTIONS = sections/appendix-classes.tex \
                 sections/appendix-object-properties.tex \
                 sections/appendix-data-properties.tex

# LaTeX sources
TEX_SECTIONS = $(wildcard sections/*.tex)
TEX_FIGURES = $(wildcard artifacts/figures/*.tex)
COMMON_DEPS = main.tex references.bib $(TEX_SECTIONS) $(TEX_FIGURES) $(LATEX_SECTIONS) $(TTL_FILE)

.PHONY: all clean ontology latex paper draft

all: paper draft

# === Ontology pipeline ===

ontology: $(TTL_FILE)

$(OWL_FILE): $(XHTML_SOURCE) $(EXTRACT_XSL)
	$(SAXON) -s:$(XHTML_SOURCE) -xsl:$(EXTRACT_XSL) -o:$(OWL_FILE)
	@echo "Generated $(OWL_FILE)"

$(TTL_FILE): $(OWL_FILE)
	$(RAPPER) -i rdfxml -o turtle $(OWL_FILE) > $(TTL_FILE) 2>/dev/null
	@echo "Generated $(TTL_FILE)"

# === LaTeX appendices from XHTML ===

latex: $(LATEX_SECTIONS)

$(LATEX_SECTIONS) &: $(XHTML_SOURCE) $(CONCON_ONTO)
	$(CONCON_ONTO) latex --input $(XHTML_SOURCE) --output-dir sections/ --examples-dir artifacts/examples

# === Paper PDF (submission — no todo notes) ===

paper: paper.pdf

paper.pdf: paper.tex $(COMMON_DEPS)
	pdflatex paper
	bibtex paper
	pdflatex paper
	pdflatex paper

# === Draft PDF (editing — with todo notes and wide margin) ===

draft: draft.pdf

draft.pdf: draft.tex $(COMMON_DEPS)
	pdflatex draft
	bibtex draft
	pdflatex draft
	pdflatex draft

clean:
	rm -f paper.aux paper.bbl paper.blg paper.log paper.out paper.pdf
	rm -f draft.aux draft.bbl draft.blg draft.log draft.out draft.pdf
	rm -f main.aux main.bbl main.blg main.log main.out main.pdf
	rm -f $(OWL_FILE)
