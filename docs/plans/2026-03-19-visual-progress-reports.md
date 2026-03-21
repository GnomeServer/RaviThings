# Visual Progress Reports Implementation Plan

> **For Gemini CLI:** REQUIRED SUB-SKILL: Use /executing-plans to implement this plan task-by-task.

**Goal:** Improve `getData.sh` to provide a graphical progress bar on the CLI during the download of fiscal year (FY) contract data.

**Architecture:** Use a custom Bash function to calculate and draw a 20-character wide progress bar using `printf` and `\r`. Silence `curl` output with `-s`.

**Tech Stack:** Bash, curl

---

### Task 1: Scaffolding and Setup

**Files:**
- Modify: `getData.sh:1-3`

**Step 1: Define loop constants and total count**

```bash
START_FY=2007
END_FY=2026
TOTAL=$((END_FY - START_FY + 1))
CURRENT=0
```

**Step 2: Add the progress bar function**

```bash
draw_progress_bar() {
    local percentage=$(( ($1 * 100) / $2 ))
    local filled=$(( ($1 * 20) / $2 ))
    local empty=$(( 20 - filled ))
    local bar=$(printf "%${filled}s" | tr ' ' '#')
    local spaces=$(printf "%${empty}s" | tr ' ' '-')
    printf "\rProgress: [%s%s] %d%% (%d/%d) - Downloading %s... " "$bar" "$spaces" "$percentage" "$1" "$2" "$3"
}
```

**Step 3: Update the loop to use the function and silence curl**

```bash
for fy in $(seq $START_FY $END_FY); do
    CURRENT=$((CURRENT + 1))
    draw_progress_bar $CURRENT $TOTAL "FY$fy"
    curl -sLOf "https://files.usaspending.gov/award_data_archive/FY${fy}_089_Contracts_Full_20260306.zip"
done
echo -e "\nDone!"
```

**Step 4: Commit**

```bash
git add getData.sh
git commit -m "feat: add visual progress bar to getData.sh"
```

### Task 2: Verification

**Step 1: Run the script to verify the progress bar appearance**

Run: `./getData.sh`
Expected: A progress bar that updates in place on a single line.

**Step 2: Verify files are being downloaded**

Run: `ls -lh FY*.zip`
Expected: ZIP files for the years processed.
