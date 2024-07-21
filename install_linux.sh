#!/bin/sh

##
# Author: Sargis Yonan (sargis@yonan.org)
# Date: 19 July 2024
##

# Get the directory in which the installation script lives.
INSTALL_DIR=$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )
# Push into the script directory to get relative paths to work.
pushd "$INSTALL_DIR" > /dev/null

## Install Fonts ##

##
# @var FONT_FILES
# @brief The list of all of fonts to install
FONT_FILES=$(ls fonts/*.otf)

##
# @var FONT_INSTALL_DIR
# @brief The location to install the fonts on the system
FONT_INSTALL_DIR="$HOME/.local/share/fonts"

# Make the fonts directory if it does not exist.
mkdir -p "$FONT_INSTALL_DIR"

# Loop through all of the fonts to install, and copy them one-by-one.
for font in $FONT_FILES
do
    fontname=$(basename "$font")
    
    echo "Installing font: $fontname"
    if [ -f "$FONT_INSTALL_DIR/$fontname" ]; then 
        rm "$FONT_INSTALL_DIR/$fontname"
    fi
    
    cp "$font" "$FONT_INSTALL_DIR/"
done

# Refresh font cache
fc-cache -f -v

# Pop back into the original directory.
popd > /dev/null

echo ""
echo "Installation complete."
echo ""
