OUTPUT_DIRS := nohadra
FONT_EXTENSIONS := otf ttf woff woff2
FONTS_DIR := fonts

GLYPH_FILES := $(foreach dir, $(OUTPUT_DIRS), $(shell find $(dir) -name '*.glyphs' | grep -v ' (Autosaved).glyphs'))

SAMPLE_DIR := samples
SAMPLE_TEXT := "ܥܠ ܐܪܥܐ ܫܠܡܐ ܘܣܒܪܐ ܛܒܐ ܠܒܪܢܫ̈ܐ"

all: build generate-png install test

venv/created: requirements.txt
	python3 -m venv venv
	. venv/bin/activate; pip install -Ur requirements.txt
	touch venv/created

venv: venv/created

open:
	for file in $(GLYPH_FILES); do \
		if [ -f "$$file" ]; then \
			open -a /Applications/Glyphs\ 3.app "$$file"; \
		fi \
	done

build:
	for file in $(GLYPH_FILES); do \
		if [ -f "$$file" ]; then \
			osascript scripts/exportfont.scpt "$$file"; \
		fi \
	done

install: build
	./install.command

test: venv
	. venv/bin/activate; \
	for file in $(FONTS_DIR)/*.otf; do \
		if [ -f "$$file" ]; then \
			fontbakery check-opentype $$file; \
			fontbakery check-universal $$file; \
		fi; \
	done

clean:
	@for ext in $(FONT_EXTENSIONS); do \
		for file in $(OUTPUT_DIRS)/*.$$ext; do \
			if [ -f "$$file" ]; then \
				rm $$file; \
			fi; \
		done; \
	done; \
	rm -rf venv; \
	rm -rf $(FONTS_DIR)/*
	rm -rf samples/*

# Target to generate PNG with Syriac sample text using Python
generate-png: venv
	. venv/bin/activate && \
	for file in $(FONTS_DIR)/*.otf; do \
			font=$$(basename "$$file" .otf); \
			python3 scripts/render_text.py "$$file" $(SAMPLE_TEXT) "$(SAMPLE_DIR)/$$font.png"; \
	done

.PHONY: clean test install build open venv all generate-svg generate-png
