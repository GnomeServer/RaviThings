#!/bin/bash

START_FY=2007
END_FY=2026
TOTAL=$((END_FY - START_FY + 1))
CURRENT=0

draw_progress_bar() {
    local percentage=$(( ($1 * 100) / $2 ))
    local filled=$(( ($1 * 20) / $2 ))
    local empty=$(( 20 - filled ))
    local bar=$(printf "%${filled}s" | tr ' ' '#')
    local spaces=$(printf "%${empty}s" | tr ' ' '-')
    printf "\rProgress: [%s%s] %d%% (%d/%d) - Downloading %s... " "$bar" "$spaces" "$percentage" "$1" "$2" "$3"
}

for fy in $(seq $START_FY $END_FY); do
    CURRENT=$((CURRENT + 1))
    draw_progress_bar $CURRENT $TOTAL "FY$fy"
    curl -sLOf "https://files.usaspending.gov/award_data_archive/FY${fy}_089_Contracts_Full_20260306.zip"
done

echo -e "\nDone!"
