OUTPUT_DIRS:=nohadra
FONT_EXTENSIONS:=otf ttf woff woff2
FONTS_DIR:=fonts

GLYPH_FILES := $(foreach dir, $(OUTPUT_DIRS), $(shell find $(dir) -name '*.glyphs' | grep -v ' (Autosaved).glyphs'))

all: build move install test

venv/created: requirements.txt
	python3 -m venv venv
	. venv/bin/activate; pip3 install -Ur requirements.txt
	touch venv/created

venv: venv/created

open:
	for file in $(GLYPH_FILES); do \
		if [ -f "$$file" ]; then \
			open -a /Applications/Glyphs\ 3.app $$file; \
		fi \
	done

move: 
	for ext in $(FONT_EXTENSIONS); do \
		for file in $(OUTPUT_DIRS)/*.$$ext; do \
			if [ -f "$$file" ]; then \
				mv $$file fonts/; \
			fi; \
		done; \
	done

build:
	for file in $(GLYPH_FILES); do \
		if [ -f "$$file" ]; then \
			osascript scripts/exportfont.scpt "$$file"; \
		fi \
	done

install: move
	for file in $(FONTS_DIR)/*.otf; do \
		filename=$$(basename "$$file"); \
		if [ -f "~/Library/Fonts/$$filename" ]; then \
			rm -f "~/Library/Fonts/$$filename"; \
		fi; \
		cp "$$file" ~/Library/Fonts/; \
	done


test: venv move
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
	rm fonts/*
