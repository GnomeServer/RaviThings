# Design: Visual Progress Reports for getData.sh

## Overview
Improve the `getData.sh` script to provide a graphical progress bar on the CLI during the download of fiscal year (FY) contract data.

## Goal
- Replace the silent, repetitive `curl` loop with a visual indicator of overall progress.
- Maintain a clean terminal output by suppressing `curl`'s internal progress metrics.

## Approach: Custom Bash Function
We will implement a self-contained Bash function to draw a progress bar using `printf` and `\r` (carriage return).

### Components
1. **Loop Variables**: 
    - `START_FY=2007`
    - `END_FY=2026`
    - `TOTAL=$((END_FY - START_FY + 1))`
2. **Progress Bar Function**:
    - Calculates percentage based on `CURRENT / TOTAL`.
    - Draws a 20-character wide bar (using `#` for completed and `-` for remaining).
    - Overwrites the current line.
3. **Loop Integration**:
    - Silences `curl` using `-s`.
    - Updates the bar at each step.

## Visual Mockup
During execution:
`Progress: [##########----------] 50% (10/20) - Downloading FY2017...`

## Error Handling
- Use `curl -f` to ensure the script doesn't hang or report success on a failed download.
- Ensure the progress bar updates correctly even if an individual year fails.

## Success Criteria
- The script successfully downloads all files from 2007 to 2026.
- A single-line progress bar remains visible and updates until completion.
- No cluttered output from `curl`.
