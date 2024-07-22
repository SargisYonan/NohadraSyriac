#!/bin/bash

# Author: Sargis Yonan (sargis@yonan.org)
# Date: 19 July 2024

# Get the directory in which the installation script lives.
INSTALL_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
pushd "$INSTALL_DIR" > /dev/null

# Function to install fonts on macOS
install_fonts_macos() {
    FONT_FILES=$(ls fonts/*.otf)
    FONT_INSTALL_DIR="/Users/$USER/Library/Fonts"

    mkdir -p "$FONT_INSTALL_DIR"

    for font in $FONT_FILES
    do
        fontname=$(basename "$font")
        echo "Installing font: $fontname"
        if [ -f "$HOME/Library/Fonts/$fontname" ]; then 
            rm "$HOME/Library/Fonts/$fontname"
        fi
        cp "$font" "$HOME/Library/Fonts/"
    done
}

# Function to install fonts on Linux
install_fonts_linux() {
    FONT_FILES=$(ls fonts/*.otf)
    FONT_INSTALL_DIR="$HOME/.local/share/fonts"

    mkdir -p "$FONT_INSTALL_DIR"

    for font in $FONT_FILES
    do
        fontname=$(basename "$font")
        echo "Installing font: $fontname"
        if [ -f "$FONT_INSTALL_DIR/$fontname" ]; then 
            rm "$FONT_INSTALL_DIR/$fontname"
        fi
        cp "$font" "$FONT_INSTALL_DIR/"
    done

    fc-cache -f -v
}

# Function to install fonts on Windows
install_fonts_windows() {
    FONT_FILES=$(ls fonts/*.otf)
    FONT_INSTALL_DIR="$USERPROFILE\\AppData\\Local\\Microsoft\\Windows\\Fonts"

    if [ ! -d "$FONT_INSTALL_DIR" ]; then
        mkdir "$FONT_INSTALL_DIR"
    fi

    for font in $FONT_FILES
    do
        fontname=$(basename "$font")
        echo "Installing font: $fontname"
        if [ -f "$FONT_INSTALL_DIR\\$fontname" ]; then
            rm "$FONT_INSTALL_DIR\\$fontname"
        fi
        cp "$font" "$FONT_INSTALL_DIR\\"
    done
}

# Detect the operating system and call the appropriate function
case "$OSTYPE" in
    darwin*)  install_fonts_macos ;; 
    linux*)   install_fonts_linux ;;
    msys*)    install_fonts_windows ;;
    cygwin*)  install_fonts_windows ;;
    *)        echo "Unsupported OS: $OSTYPE" ;;
esac

popd > /dev/null

echo ""
echo "Installation complete."
echo ""
