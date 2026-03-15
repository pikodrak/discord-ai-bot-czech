"""
Comprehensive tests for language utility functions.

Tests language instruction building and system prompt modification
for multiple language codes including English, Czech, Slovak, German, etc.
"""

import pytest
from src.llm.language_utils import (
    build_language_instruction,
    apply_language_to_system_prompt,
    LANGUAGE_NAMES,
)


class TestBuildLanguageInstruction:
    """Test suite for build_language_instruction function."""

    def test_english_returns_empty(self):
        """Test that English language returns empty instruction."""
        instruction = build_language_instruction("en")
        assert instruction == ""

    def test_czech_language(self):
        """Test Czech language instruction."""
        instruction = build_language_instruction("cs")
        assert "Czech (cs-CZ)" in instruction
        assert "IMPORTANT" in instruction
        assert "MUST respond ONLY" in instruction

    def test_slovak_language(self):
        """Test Slovak language instruction."""
        instruction = build_language_instruction("sk")
        assert "Slovak (sk-SK)" in instruction
        assert "IMPORTANT" in instruction

    def test_german_language(self):
        """Test German language instruction."""
        instruction = build_language_instruction("de")
        assert "German (de-DE)" in instruction
        assert "IMPORTANT" in instruction

    def test_spanish_language(self):
        """Test Spanish language instruction."""
        instruction = build_language_instruction("es")
        assert "Spanish (es-ES)" in instruction

    def test_french_language(self):
        """Test French language instruction."""
        instruction = build_language_instruction("fr")
        assert "French (fr-FR)" in instruction

    def test_unknown_language_fallback(self):
        """Test unknown language code falls back to uppercase code."""
        instruction = build_language_instruction("xx")
        assert "XX" in instruction
        assert "IMPORTANT" in instruction

    def test_case_insensitive(self):
        """Test that language codes are case insensitive."""
        lower = build_language_instruction("cs")
        upper = build_language_instruction("CS")
        mixed = build_language_instruction("Cs")
        assert lower == upper == mixed

    def test_whitespace_trimming(self):
        """Test that language codes are trimmed."""
        with_space = build_language_instruction(" cs ")
        without_space = build_language_instruction("cs")
        assert with_space == without_space

    def test_instruction_format(self):
        """Test that instruction has correct format for non-English."""
        instruction = build_language_instruction("cs")
        # Should contain all key parts
        assert "IMPORTANT:" in instruction
        assert "MUST" in instruction
        assert "ONLY" in instruction
        assert "Never respond in English" in instruction

    @pytest.mark.parametrize("lang_code", ["cs", "sk", "de", "es", "fr"])
    def test_all_supported_languages(self, lang_code):
        """Test all supported languages return non-empty instructions."""
        instruction = build_language_instruction(lang_code)
        assert len(instruction) > 0
        assert "IMPORTANT" in instruction


class TestApplyLanguageToSystemPrompt:
    """Test suite for apply_language_to_system_prompt function."""

    def test_english_no_modification(self):
        """Test that English language doesn't modify system prompt."""
        original = "You are a helpful assistant."
        result = apply_language_to_system_prompt(original, "en")
        assert result == original

    def test_czech_adds_instruction(self):
        """Test that Czech language adds instruction to prompt."""
        original = "You are a helpful assistant."
        result = apply_language_to_system_prompt(original, "cs")
        
        assert original in result
        assert "Czech" in result
        assert "IMPORTANT" in result
        assert result.startswith(original)

    def test_none_prompt_with_language(self):
        """Test handling None prompt with non-English language."""
        result = apply_language_to_system_prompt(None, "cs")
        assert "Czech" in result
        assert "IMPORTANT" in result

    def test_none_prompt_english(self):
        """Test handling None prompt with English."""
        result = apply_language_to_system_prompt(None, "en")
        assert result == ""

    def test_empty_prompt_with_language(self):
        """Test handling empty prompt with non-English language."""
        result = apply_language_to_system_prompt("", "cs")
        assert "Czech" in result

    def test_empty_prompt_english(self):
        """Test handling empty prompt with English."""
        result = apply_language_to_system_prompt("", "en")
        assert result == ""

    def test_prompt_separator(self):
        """Test that language instruction is properly separated from prompt."""
        original = "You are helpful."
        result = apply_language_to_system_prompt(original, "cs")
        
        # Should have double newline separator
        assert "\n\n" in result
        parts = result.split("\n\n")
        assert parts[0] == original

    def test_multiple_languages(self):
        """Test applying different languages to same prompt."""
        original = "You are helpful."
        
        cs_result = apply_language_to_system_prompt(original, "cs")
        de_result = apply_language_to_system_prompt(original, "de")
        
        assert "Czech" in cs_result
        assert "German" in de_result
        assert cs_result != de_result

    @pytest.mark.parametrize(
        "language,expected_in_result",
        [
            ("cs", "Czech"),
            ("sk", "Slovak"),
            ("de", "German"),
            ("es", "Spanish"),
            ("fr", "French"),
        ],
    )
    def test_language_specific_instructions(self, language, expected_in_result):
        """Test that each language gets correct instruction."""
        result = apply_language_to_system_prompt("Be helpful.", language)
        assert expected_in_result in result

    def test_preserves_original_prompt(self):
        """Test that original prompt is preserved exactly."""
        original = "You are a helpful assistant with special instructions.\nBe kind."
        result = apply_language_to_system_prompt(original, "cs")
        
        # Original should be at the start, unchanged
        assert result.startswith(original)


class TestLanguageNames:
    """Test suite for LANGUAGE_NAMES constant."""

    def test_language_names_coverage(self):
        """Test that LANGUAGE_NAMES has expected languages."""
        expected_languages = ["en", "cs", "sk", "de", "es", "fr"]
        for lang in expected_languages:
            assert lang in LANGUAGE_NAMES

    def test_language_names_format(self):
        """Test that language names are properly formatted."""
        for code, name in LANGUAGE_NAMES.items():
            assert isinstance(code, str)
            assert isinstance(name, str)
            assert len(code) == 2  # Two-letter code
            assert len(name) > 0  # Non-empty name

    def test_czech_name(self):
        """Test Czech language name format."""
        assert LANGUAGE_NAMES["cs"] == "Czech (cs-CZ)"

    def test_english_name(self):
        """Test English language name."""
        assert LANGUAGE_NAMES["en"] == "English"
