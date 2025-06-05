# Folder Naming Standardization for GM-Eval Commands

## Overview
Standardize folder naming and location between `gm-eval download` and `gm-eval run` commands to use consistent datetime format and location.

## Current Issue
- `gm-eval download` creates folders like `20250604_121721` (date + time) in project root
- `gm-eval run` creates folders like `experiments/20250604` (date only) in experiments subfolder
- User wants both to follow the `gm-eval download` pattern

## Plan

### 1. Analyze Current Implementation
- ✅ `download.py` line 52-56: Uses `datetime.utcnow().strftime("%Y%m%d_%H%M%S")` in project root (`./`)
- ✅ `run.py` line 96-98: Uses `datetime.now().strftime("%Y%m%d")` in `experiments/` subfolder

### 2. Standardization Target
- **Format**: `YYYYMMDD_HHMMSS` (date + time)
- **Location**: Project root (current directory)
- **Example**: `20250604_121721`

### 3. Required Changes
- Update `run.py` to use the same datetime format and location as `download.py`
- Ensure both commands use `datetime.utcnow()` for consistency
- Remove the `experiments/` subdirectory prefix

### 4. Implementation Steps
1. Modify `run.py` line 97 to use `datetime.utcnow().strftime("%Y%m%d_%H%M%S")`
2. Modify `run.py` line 98 to use `os.path.join("./", date_str)` instead of `os.path.join("experiments", date_str)`
3. Test both commands to ensure they create folders with identical naming pattern
4. Update any documentation that references the old folder structure

## Testing Plan
1. Create temp folder in project root
2. Run `gm-eval download` and verify folder name format
3. Run `gm-eval run --model-config-id <test-id> --mode litellm` and verify folder name format
4. Confirm both create folders in same location with same datetime format

## Summarization of Edit Sessions

### Session 1: Analysis Complete
- ✅ Identified the root cause of folder naming inconsistency
- ✅ Found exact code locations in both commands
- ✅ Determined standardization target (download.py pattern)
- ✅ Created implementation plan with specific line changes needed
- ✅ Ready to implement the fix

### Session 2: Implementation and Testing - COMPLETED
- ✅ Successfully modified `run.py` line 111-112 to match `download.py` pattern:
  - Changed `datetime.now().strftime("%Y%m%d")` to `datetime.utcnow().strftime("%Y%m%d_%H%M%S")`
  - Changed `os.path.join("experiments", date_str)` to `os.path.join("./", date_str)`
- ✅ Tested both commands in temp folder:
  - `gm-eval download` created: `20250604_130353` (date+time format)
  - `gm-eval run --model-config-id mc067 --mode litellm` created: `20250604_130537` (date+time format)
- ✅ Verified both folders created in project root (not experiments subfolder)
- ✅ Confirmed identical folder structure and content organization
- ✅ Updated README.md documentation to reflect new standardized folder naming:
  - Changed examples from `experiments/YYYYMMDD/` to `YYYYMMDD_HHMMSS/`
  - Updated all CLI command examples with correct folder references
  - Added clarification about automatic timestamped folder creation
- ✅ Standardization complete - both commands now use consistent naming pattern
- ✅ Issue resolved successfully

## Final Summary

**Problem Solved**: Inconsistent folder naming between `gm-eval download` and `gm-eval run` commands

**Root Cause**: 
- `download.py` used `datetime.utcnow().strftime("%Y%m%d_%H%M%S")` in project root
- `run.py` used `datetime.now().strftime("%Y%m%d")` in `experiments/` subfolder

**Solution Applied**:
- Modified `run.py` to use identical pattern as `download.py`
- Both commands now create folders with format `YYYYMMDD_HHMMSS` in project root
- Updated all documentation to reflect the standardized naming convention

**Testing Results**:
- ✅ Both commands create identical timestamp format folders
- ✅ Both commands create folders in same location (project root)
- ✅ Folder contents and structure remain unchanged
- ✅ All existing functionality preserved

**Status**: ✅ RESOLVED - Implementation complete and tested successfully