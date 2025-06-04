# GM-Eval Mode Updates Plan

## Overview
Update the gm-eval command to support batch and litellm modes with automatic provider detection based on model-config-id prefixes.

## Plan

### 1. Update CLI Structure
- **run command**: Add `--mode {batch,litellm}` parameter
- **send command**: 
  - Add `--mode {batch,litellm}` parameter
  - Add `--model-config-id` parameter for automatic detection
  - Move current file-based functionality to `send-file` command
- **evaluate command**: Add `--mode {batch,litellm}` parameter

### 2. Provider Detection Logic
- Parse model-ids with provider prefixes (e.g., "openai/o3", "anthropic/claude-4", "alibaba/qwen-3")
- Automatically detect provider and JSONL format from model-config-id
- Handle OpenAI-compatible providers (different API keys/URLs but same endpoint format)

### 3. Mode-Specific Handling
- **Batch mode**: Remove provider prefixes from model names (e.g., "mistral/mistral-small" → "mistral-small")
- **LiteLLM mode**: Keep full model names with prefixes
- Automatic format detection (openai, vertex, mistral) based on provider

### 4. Implementation Details
- Extend `utils.py` with provider detection functions
- Update command argument parsing
- Modify batch job creation logic to handle modes
- Add CLI command for `send-file` (current send functionality)

## Implementation Steps

### Step 1: Update Utils Module
- Add `detect_provider_from_model_id()` function
- Add `get_batch_model_name()` function to handle prefix removal
- Add `get_jsonl_format_from_provider()` function
- Extend `get_model_id_from_config_id()` to return full model-id with prefix

### Step 2: Create send-file Command
- Copy current send.py to send_file.py
- Update CLI to register send-file command
- Keep original file-based send functionality intact

### Step 3: Update send Command
- Add mode and model-config-id parameters
- Implement automatic provider/format detection
- Generate JSONL automatically from model-config-id
- Handle mode-specific model name processing

### Step 4: Update run Command
- Add mode parameter
- Pass mode to send and evaluate commands
- Update argument handling for new parameters

### Step 5: Update evaluate Command
- Add mode parameter support
- Pass mode information to evaluation processing

### Step 6: Update Provider Configurations
- Ensure OpenAI-compatible providers are properly configured
- Test with alibaba/qwen-3 and other OpenAI-compatible models

## Summarization of Edit Sessions

### Session 1: Core Implementation Complete
- Created backlog plan with detailed implementation steps
- Extended utils.py with comprehensive provider detection functions:
  - `detect_provider_from_model_id()` - Parse provider prefixes from model IDs
  - `get_batch_model_name()` - Handle mode-specific model name formatting
  - `get_provider_method_from_model_id()` - Map providers to batch methods
  - `get_jsonl_format_from_provider()` - Auto-detect JSONL formats
  - `is_openai_compatible_provider()` - Identify OpenAI-compatible providers
  - Updated `get_model_id_from_config_id()` to support keeping provider prefixes
- Created send-file command by copying original send functionality
- Completely rewrote send command for mode-based operation:
  - Added --mode and --model-config-id parameters
  - Automatic provider detection from model configuration
  - Mode-aware model name processing (prefix removal for batch mode)
  - OpenAI-compatible provider support (e.g., alibaba/qwen-3)
- Updated CLI structure to register send-file command
- Modified run command:
  - Replaced --method with --mode parameter
  - Integrated mode-based provider detection
  - Automatic JSONL format selection
  - Simplified parameter handling by removing provider-specific options
- Enhanced evaluate command with --mode parameter for consistency
- Tested provider detection logic with multiple model ID formats
- All CLI help commands working correctly with new parameter structure

### Session 2: Testing and Integration - COMPLETED
- ✅ Downloaded real configuration files from AI Eval spreadsheet
- ✅ Updated provider detection for vertex_ai and deepseek providers
- ✅ Tested end-to-end workflow with actual model configurations:
  - mc057 (deepseek/deepseek-reasoner) with litellm mode
  - mc067 (vertex_ai/publishers/google/models/gemini-2.0-flash-001) with batch mode
- ✅ Verified batch mode prefix removal: vertex_ai/publishers/google/models/gemini-2.0-flash-001 → publishers/google/models/gemini-2.0-flash-001
- ✅ Confirmed litellm mode keeps full model names with prefixes
- ✅ Tested mode parameter propagation through run command
- ✅ Validated automatic JSONL format detection (deepseek→openai, vertex_ai→vertex)
- ✅ Verified backward compatibility with send-file command
- ✅ All commands working with proper provider detection and mode handling

### Session 3: Implementation Complete - SUCCESS
- ✅ All planned features implemented and tested
- ✅ Provider detection working for real-world model configurations
- ✅ Mode-based processing (batch vs litellm) functioning correctly
- ✅ Automatic prefix removal in batch mode validated
- ✅ OpenAI-compatible provider support ready (alibaba mapping confirmed)
- ✅ CLI help documentation accurate and comprehensive
- ✅ Integration testing successful with live API calls
- ✅ Ready for production use

## Final Implementation Summary

The gm-eval command has been successfully updated with comprehensive mode support:

### New Commands:
- `gm-eval send` - Mode-based sending with automatic provider detection
- `gm-eval send-file` - Original file-based functionality (backward compatibility)

### New Parameters:
- `--mode {batch,litellm}` on run, send, and evaluate commands
- `--model-config-id` on send command for automatic detection

### Key Features Implemented:
1. **Automatic Provider Detection**: Parses model-ids with prefixes (openai/, anthropic/, vertex_ai/, etc.)
2. **Mode-Aware Processing**: 
   - Batch mode removes provider prefixes
   - LiteLLM mode preserves full model names
3. **Format Auto-Detection**: Automatically selects JSONL format based on provider
4. **OpenAI-Compatible Support**: Ready for providers like alibaba/qwen-3
5. **Seamless Integration**: Mode parameter flows through run → send → evaluate chain

### Testing Results:
- ✅ deepseek/deepseek-reasoner (litellm mode) - Response generated successfully
- ✅ vertex_ai/publishers/google/models/gemini-2.0-flash-001 (batch mode) - Batch job completed
- ✅ Provider detection accurate for all tested configurations
- ✅ Prefix removal working correctly in batch mode
- ✅ All CLI commands showing proper help and parameter validation