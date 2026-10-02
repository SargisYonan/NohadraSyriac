SOURCE := glyphs/NohadraSyriac.glyphs
STYLES := Sapna Amedia
FONTS  := $(foreach s,$(STYLES),fonts/NohadraSyriac-$(s).otf)
VENV   := venv
PY     := $(VENV)/bin/python
# The release `make diff` compares against: a git tag or commit.
BEFORE ?= NohadraSyriac-v1.7

.DEFAULT_GOAL := help

help:
	@echo "Nohadra Syriac"
	@echo "  make build       compile fonts/*.otf from $(SOURCE)"
	@echo "  make qa          report problems with the letters, joins and marks"
	@echo "  make test        pass/fail tests for joins, marks and coverage"
	@echo "  make fontbakery  run fontbakery's universal checks (reports in out/)"
	@echo "  make proof       write out/<style>/proof.html and open it"
	@echo "  make images      render the README images into documentation/"
	@echo "  make diff        write out/diff.html: this build against BEFORE=$(BEFORE)"
	@echo "  make all         build, qa, proof, images, then test"
	@echo "  make ci          what GitHub runs on every push: fails on any QA error,"
	@echo "                   failing test or fontbakery failure"
	@echo "  make install     install the fonts for this user"
	@echo "  make open        open the source in Glyphs 3"
	@echo "  make clean       remove out/ and caches (the committed fonts are kept)"
	@echo ""
	@echo "Every check runs on both styles. To check fonts exported from Glyphs instead:"
	@echo "  make qa proof FONTS='path/to/NohadraSyriac-Sapna.otf path/to/NohadraSyriac-Amedia.otf'"

$(VENV)/.done: requirements.txt
	python3 -m venv $(VENV)
	$(VENV)/bin/pip install -q --upgrade pip
	$(VENV)/bin/pip install -q -r requirements.txt
	touch $@

venv: $(VENV)/.done

# Stamp the fonts with the source's last commit time rather than the build
# time, so rebuilding an unchanged source gives identical fonts.
SOURCE_DATE_EPOCH ?= $(shell git log -1 --format=%ct -- $(SOURCE) 2>/dev/null)
ifneq ($(SOURCE_DATE_EPOCH),)
export SOURCE_DATE_EPOCH
else
unexport SOURCE_DATE_EPOCH
endif

# One fontmake run writes both styles.
fonts/NohadraSyriac-Sapna.otf: $(SOURCE) $(VENV)/.done
	@mkdir -p fonts
	$(VENV)/bin/fontmake -g $(SOURCE) -i -o otf --overlaps-backend pathops \
		--output-dir fonts 2>&1 | grep -v "^INFO" || true
	@for f in $(FONTS); do test -f $$f || { echo "$$f was not built"; exit 1; }; done
	@touch $(FONTS)
fonts/NohadraSyriac-Amedia.otf: fonts/NohadraSyriac-Sapna.otf

build: $(FONTS)

# Use the fonts given on the command line as they are; otherwise build first.
FONT_DEP := $(if $(filter command line,$(origin FONTS)),,$(FONTS))

qa: $(FONT_DEP) $(VENV)/.done
	@for f in $(FONTS); do FONT=$$f $(PY) qa/check.py || exit 1; echo; done

test: $(FONT_DEP) $(VENV)/.done
	@for f in $(FONTS); do echo "== $$f"; FONT=$$f $(PY) -m pytest tests -q || exit 1; done

fontbakery: $(FONT_DEP) $(VENV)/.done
	@mkdir -p out
	$(VENV)/bin/fontbakery check-universal $(FONTS) --succinct -C \
		--html out/fontbakery.html --ghmarkdown out/fontbakery.md

proof: $(FONT_DEP) $(VENV)/.done
	@for f in $(FONTS); do \
		FONT=$$f $(PY) qa/check.py --quiet && FONT=$$f $(PY) qa/proof.py || exit 1; done
	@[ -n "$$CI" ] || open out/Sapna/proof.html 2>/dev/null || true

images: $(FONT_DEP) $(VENV)/.done
	@for f in $(FONTS); do FONT=$$f $(PY) qa/specimen.py || exit 1; done

# The fonts as they were at BEFORE, for `make diff`.
out/before/$(BEFORE)/.done:
	@mkdir -p $(@D)
	@for s in $(STYLES); do \
		git show $(BEFORE):fonts/NohadraSyriac-$$s.otf > $(@D)/NohadraSyriac-$$s.otf || exit 1; done
	@touch $@

diff: $(FONT_DEP) out/before/$(BEFORE)/.done $(VENV)/.done
	$(PY) qa/diff.py --before out/before/$(BEFORE) --label "$(BEFORE)" $(FONTS)
	@[ -n "$$CI" ] || open out/diff.html 2>/dev/null || true

all: build qa proof images test

# Always rebuild from the source, so CI tests the source rather than stale
# committed fonts.
ci: $(VENV)/.done
	rm -f $(FONTS)
	$(MAKE) build
	@for f in $(FONTS); do FONT=$$f $(PY) qa/check.py --strict || exit 1; done
	$(MAKE) test fontbakery proof images

install: $(FONTS)
	./install_fonts.sh

open:
	open -a "/Applications/Glyphs 3.app" $(SOURCE)

clean:
	rm -rf out master_ufo instance_ufo .pytest_cache qa/__pycache__ tests/__pycache__

.PHONY: help venv build qa test fontbakery proof images diff all ci install open clean
