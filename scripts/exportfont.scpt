on run argv
    set filePath to item 1 of argv
    
    tell application "Glyphs 3"
        activate
        open filePath
    end tell

	tell application "System Events"
        keystroke "s" using {command down}
    end tell

    tell application "System Events"
        keystroke "e" using {command down}
        -- delay 1 -- give Glyphs some time to open the file
        key code 36
    end tell
end run
