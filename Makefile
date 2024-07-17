OUTPUT_DIRS:=nohadra
OUTPUT_NAMES:=EstrangelaNohadraSquare
FONT_EXTENSIONS:=otf ttf woff woff2
FONTS_DIR:=fonts
GLYPH_FILES := $(foreach dir, $(OUTPUT_DIRS), $(wildcard $(dir)/*.glyphs))

all: move install test

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
	@for ext in $(FONT_EXTENSIONS); do \
		for file in $(OUTPUT_DIRS)/*.$$ext; do \
			if [ -f "$$file" ]; then \
				mv $$file fonts/; \
			fi; \
		done; \
	done

build:
	for file in $(GLYPH_FILES); do \
		if [ -f "$$file" ]; then \
			osascript scripts/exportfont.scpt "../$$file"; \
		fi \
	done

install: move
	for file in $(FONTS_DIR)/*.otf; do \
		if [ -f "$$file" ]; then \
			cp $$file ~/Library/Fonts/; \
		fi; \
	done

test: venv move
	. venv/bin/activate; \
	for file in $(FONTS_DIR)/*.otf; do \
		if [ -f "$$file" ]; then \
			fontbakery check-notofonts file; \
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