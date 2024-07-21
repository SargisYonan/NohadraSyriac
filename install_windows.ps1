# Author: Sargis Yonan (sargis@yonan.org)
# Date: 19 July 2024

# Get the directory in which the installation script lives.
$INSTALL_DIR = Split-Path -Parent $MyInvocation.MyCommand.Definition
# Push into the script directory to get relative paths to work.
Push-Location $INSTALL_DIR

## Install Fonts ##

# The list of all fonts to install
$FONT_FILES = Get-ChildItem -Path ".\fonts\" -Filter "*.otf"

# The location to install the fonts on the system
$FONT_INSTALL_DIR = "$env:USERPROFILE\AppData\Local\Microsoft\Windows\Fonts"

# Make the fonts directory if it does not exist.
if (-Not (Test-Path -Path $FONT_INSTALL_DIR)) {
    New-Item -ItemType Directory -Path $FONT_INSTALL_DIR
}

# Loop through all of the fonts to install, and copy them one-by-one.
foreach ($font in $FONT_FILES) {
    $fontname = $font.Name

    Write-Output "Installing font: $fontname"
    $destination = Join-Path $FONT_INSTALL_DIR $fontname
    if (Test-Path -Path $destination) {
        Remove-Item -Path $destination -Force
    }

    Copy-Item -Path $font.FullName -Destination $destination
}

# Pop back into the original directory.
Pop-Location

Write-Output ""
Write-Output "Installation complete."
Write-Output ""
