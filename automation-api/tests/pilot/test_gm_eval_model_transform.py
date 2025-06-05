"""
Tests for centralized model ID transformation in gm_eval.
"""

from lib.pilot.gm_eval.utils import get_batch_model_name, transform_model_id


class TestCentralizedModelTransformation:
    """Test the centralized transform_model_id function."""

    def test_vertex_ai_litellm_mode(self):
        """Test vertex_ai model in LiteLLM mode uses vertex_ai/model_name format."""
        model_id = "vertex_ai/publishers/google/models/gemini-2.0-flash-001"
        result = transform_model_id(model_id, mode="litellm")
        expected = "vertex_ai/gemini-2.0-flash-001"
        assert result == expected, f"Expected {expected}, got {result}"

    def test_vertex_ai_batch_mode(self):
        """Test vertex_ai model in batch mode removes only vertex_ai prefix."""
        model_id = "vertex_ai/publishers/google/models/gemini-2.0-flash-001"
        result = transform_model_id(model_id, mode="batch")
        expected = "publishers/google/models/gemini-2.0-flash-001"
        assert result == expected, f"Expected {expected}, got {result}"

    def test_vertex_ai_openai_format(self):
        """Test vertex_ai model with OpenAI JSONL format extracts model name."""
        model_id = "vertex_ai/publishers/google/models/gemini-2.0-flash-001"
        result = transform_model_id(model_id, jsonl_format="openai")
        expected = "gemini-2.0-flash-001"
        assert result == expected, f"Expected {expected}, got {result}"

    def test_vertex_ai_vertex_format(self):
        """Test vertex_ai model with Vertex JSONL format removes vertex_ai prefix."""
        model_id = "vertex_ai/publishers/google/models/gemini-2.0-flash-001"
        result = transform_model_id(model_id, jsonl_format="vertex")
        expected = "publishers/google/models/gemini-2.0-flash-001"
        assert result == expected, f"Expected {expected}, got {result}"

    def test_openai_litellm_mode(self):
        """Test OpenAI model in LiteLLM mode keeps provider prefix."""
        model_id = "openai/gpt-4"
        result = transform_model_id(model_id, mode="litellm")
        expected = "openai/gpt-4"
        assert result == expected, f"Expected {expected}, got {result}"

    def test_openai_batch_mode(self):
        """Test OpenAI model in batch mode removes provider prefix."""
        model_id = "openai/gpt-4"
        result = transform_model_id(model_id, mode="batch")
        expected = "gpt-4"
        assert result == expected, f"Expected {expected}, got {result}"

    def test_anthropic_all_modes(self):
        """Test Anthropic model handling in all modes."""
        model_id = "anthropic/claude-3-sonnet"

        litellm_result = transform_model_id(model_id, mode="litellm")
        batch_result = transform_model_id(model_id, mode="batch")
        openai_format = transform_model_id(model_id, jsonl_format="openai")
        vertex_format = transform_model_id(model_id, jsonl_format="vertex")
        mistral_format = transform_model_id(model_id, jsonl_format="mistral")

        # LiteLLM keeps prefix, batch removes prefix
        assert litellm_result == "anthropic/claude-3-sonnet"
        assert batch_result == "claude-3-sonnet"
        assert openai_format == "claude-3-sonnet"
        assert vertex_format == "claude-3-sonnet"
        assert mistral_format == "claude-3-sonnet"

    def test_deepseek_litellm_mode(self):
        """Test DeepSeek model in LiteLLM mode keeps provider prefix."""
        model_id = "deepseek/deepseek-reasoner"
        result = transform_model_id(model_id, mode="litellm")
        expected = "deepseek/deepseek-reasoner"
        assert result == expected, f"Expected {expected}, got {result}"

    def test_deepseek_batch_mode(self):
        """Test DeepSeek model in batch mode removes provider prefix."""
        model_id = "deepseek/deepseek-reasoner"
        result = transform_model_id(model_id, mode="batch")
        expected = "deepseek-reasoner"
        assert result == expected, f"Expected {expected}, got {result}"

    def test_model_without_prefix(self):
        """Test model without prefix works in all modes."""
        model_id = "gpt-4"

        litellm_result = transform_model_id(model_id, mode="litellm")
        batch_result = transform_model_id(model_id, mode="batch")
        openai_format = transform_model_id(model_id, jsonl_format="openai")
        vertex_format = transform_model_id(model_id, jsonl_format="vertex")

        assert litellm_result == "gpt-4"
        assert batch_result == "gpt-4"
        assert openai_format == "gpt-4"
        assert vertex_format == "gpt-4"

    def test_mode_takes_precedence_over_format(self):
        """Test that mode parameter takes precedence over jsonl_format."""
        model_id = "vertex_ai/publishers/google/models/gemini-2.0-flash-001"

        # Mode should override format
        result = transform_model_id(model_id, mode="litellm", jsonl_format="vertex")
        expected = "vertex_ai/gemini-2.0-flash-001"  # Should use litellm logic, not vertex
        assert result == expected, f"Expected {expected}, got {result}"

        result = transform_model_id(model_id, mode="batch", jsonl_format="openai")
        expected = "publishers/google/models/gemini-2.0-flash-001"  # Should use batch logic
        assert result == expected, f"Expected {expected}, got {result}"


class TestComplexVertexAIPaths:
    """Test vertex_ai with various complex model paths."""

    def test_project_specific_paths(self):
        """Test vertex_ai with project-specific model paths."""
        test_cases = [
            {
                "model_id": "vertex_ai/projects/my-project/locations/us-central1/publishers/google/models/gemini-1.5-pro",
                "litellm_expected": "vertex_ai/gemini-1.5-pro",
                "batch_expected": "projects/my-project/locations/us-central1/publishers/google/models/gemini-1.5-pro",
            },
            {
                "model_id": "vertex_ai/publishers/google/models/text-bison-001",
                "litellm_expected": "vertex_ai/text-bison-001",
                "batch_expected": "publishers/google/models/text-bison-001",
            },
            {
                "model_id": "vertex_ai/publishers/anthropic/models/claude-3-sonnet",
                "litellm_expected": "vertex_ai/claude-3-sonnet",
                "batch_expected": "publishers/anthropic/models/claude-3-sonnet",
            },
        ]

        for case in test_cases:
            litellm_result = transform_model_id(case["model_id"], mode="litellm")
            batch_result = transform_model_id(case["model_id"], mode="batch")

            assert (
                litellm_result == case["litellm_expected"]
            ), f"LiteLLM: Expected {case['litellm_expected']}, got {litellm_result} for {case['model_id']}"
            assert (
                batch_result == case["batch_expected"]
            ), f"Batch: Expected {case['batch_expected']}, got {batch_result} for {case['model_id']}"


class TestBackwardCompatibility:
    """Test backward compatibility with existing get_batch_model_name function."""

    def test_get_batch_model_name_delegation(self):
        """Test that get_batch_model_name delegates to transform_model_id correctly."""
        test_cases = [
            (
                "vertex_ai/publishers/google/models/gemini-2.0-flash-001",
                "batch",
                "publishers/google/models/gemini-2.0-flash-001",
            ),
            ("vertex_ai/publishers/google/models/gemini-2.0-flash-001", "litellm", "vertex_ai/gemini-2.0-flash-001"),
            ("openai/gpt-4", "batch", "gpt-4"),
            ("openai/gpt-4", "litellm", "openai/gpt-4"),
            ("anthropic/claude-3-sonnet", "batch", "claude-3-sonnet"),
            ("anthropic/claude-3-sonnet", "litellm", "anthropic/claude-3-sonnet"),
        ]

        for model_id, mode, expected in test_cases:
            # Test both functions return the same result
            old_result = get_batch_model_name(model_id, mode)
            new_result = transform_model_id(model_id, mode=mode)

            assert (
                old_result == new_result == expected
            ), f"Mismatch for {model_id} in {mode} mode: old={old_result}, new={new_result}, expected={expected}"


class TestErrorCases:
    """Test edge cases and error conditions."""

    def test_empty_model_id(self):
        """Test empty model ID handling."""
        result_litellm = transform_model_id("", mode="litellm")
        result_batch = transform_model_id("", mode="batch")
        result_openai = transform_model_id("", jsonl_format="openai")

        assert result_litellm == ""
        assert result_batch == ""
        assert result_openai == ""

    def test_invalid_format(self):
        """Test behavior with unknown format."""
        model_id = "vertex_ai/publishers/google/models/gemini-2.0-flash-001"

        # Should use default behavior (not transform vertex_ai)
        result = transform_model_id(model_id, jsonl_format="unknown")
        assert result == model_id  # Should remain unchanged

        # Test with anthropic - should also remain unchanged with unknown format
        anthropic_id = "anthropic/claude-3-sonnet"
        result = transform_model_id(anthropic_id, jsonl_format="unknown")
        assert result == anthropic_id  # Should remain unchanged

    def test_no_mode_or_format(self):
        """Test behavior when neither mode nor format is specified."""
        # Should use default behavior (return unchanged)
        result = transform_model_id("anthropic/claude-3-sonnet")
        assert result == "anthropic/claude-3-sonnet"

        result = transform_model_id("openai/gpt-4")
        assert result == "openai/gpt-4"

        # vertex_ai should remain unchanged in default mode
        result = transform_model_id("vertex_ai/publishers/google/models/gemini-2.0-flash-001")
        assert result == "vertex_ai/publishers/google/models/gemini-2.0-flash-001"


class TestRealWorldScenarios:
    """Test scenarios that match real-world usage patterns."""

    def test_generate_prompts_scenario(self):
        """Test the scenario used in generate_prompts.py."""
        model_id = "vertex_ai/publishers/google/models/gemini-2.0-flash-001"

        # OpenAI format for LiteLLM
        openai_result = transform_model_id(model_id, jsonl_format="openai")
        assert openai_result == "gemini-2.0-flash-001"

        # Vertex format for batch
        vertex_result = transform_model_id(model_id, jsonl_format="vertex")
        assert vertex_result == "publishers/google/models/gemini-2.0-flash-001"

    def test_send_command_scenario(self):
        """Test the scenario used in send command."""
        model_id = "vertex_ai/publishers/google/models/gemini-2.0-flash-001"

        # LiteLLM mode - uses vertex_ai/model_name format
        litellm_result = transform_model_id(model_id, mode="litellm")
        assert litellm_result == "vertex_ai/gemini-2.0-flash-001"

        # Batch mode
        batch_result = transform_model_id(model_id, mode="batch")
        assert batch_result == "publishers/google/models/gemini-2.0-flash-001"

    def test_mixed_provider_workflow(self):
        """Test a complete workflow with different providers."""
        test_configs = [
            {
                "config_model_id": "vertex_ai/publishers/google/models/gemini-2.0-flash-001",
                "litellm_expected": "vertex_ai/gemini-2.0-flash-001",
                "batch_expected": "publishers/google/models/gemini-2.0-flash-001",
                "openai_format_expected": "gemini-2.0-flash-001",
                "vertex_format_expected": "publishers/google/models/gemini-2.0-flash-001",
            },
            {
                "config_model_id": "deepseek/deepseek-reasoner",
                "litellm_expected": "deepseek/deepseek-reasoner",
                "batch_expected": "deepseek-reasoner",
                "openai_format_expected": "deepseek-reasoner",
                "vertex_format_expected": "deepseek-reasoner",
            },
            {
                "config_model_id": "anthropic/claude-3-sonnet",
                "litellm_expected": "anthropic/claude-3-sonnet",
                "batch_expected": "claude-3-sonnet",
                "openai_format_expected": "claude-3-sonnet",
                "vertex_format_expected": "claude-3-sonnet",
            },
        ]

        for config in test_configs:
            model_id = config["config_model_id"]

            # Test mode-based transformations
            assert transform_model_id(model_id, mode="litellm") == config["litellm_expected"]
            assert transform_model_id(model_id, mode="batch") == config["batch_expected"]

            # Test format-based transformations
            assert transform_model_id(model_id, jsonl_format="openai") == config["openai_format_expected"]
            assert transform_model_id(model_id, jsonl_format="vertex") == config["vertex_format_expected"]
