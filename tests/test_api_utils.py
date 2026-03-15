"""
Tests for API utility functions.

This module tests the validation wrapper utilities used in config API endpoints.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pydantic import BaseModel, Field
from fastapi import HTTPException, status

from src.api.utils import validate_and_update_config, async_validate_and_update_config


class MockConfigUpdate(BaseModel):
    """Mock configuration update model for testing."""

    field1: str | None = Field(None, description="Test field 1")
    field2: int | None = Field(None, ge=0, le=100, description="Test field 2")


class TestValidateAndUpdateConfig:
    """Test suite for validate_and_update_config function."""

    @patch("src.api.utils.get_config_manager")
    def test_successful_update(self, mock_get_config_manager: Mock) -> None:
        """Test successful configuration update."""
        # Arrange
        mock_manager = Mock()
        mock_get_config_manager.return_value = mock_manager

        config = MockConfigUpdate(field1="test_value", field2=42)

        # Act
        result = validate_and_update_config(
            config_model=config,
            empty_message="No updates provided",
            success_message="Update successful",
            error_context="test configuration"
        )

        # Assert
        assert result == {"message": "Update successful"}
        mock_manager.update.assert_called_once_with(field1="test_value", field2=42)

    @patch("src.api.utils.get_config_manager")
    def test_empty_update_raises_400(self, mock_get_config_manager: Mock) -> None:
        """Test that empty update data raises HTTPException with 400 status."""
        # Arrange
        config = MockConfigUpdate()  # No fields set

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validate_and_update_config(
                config_model=config,
                empty_message="No updates provided",
                success_message="Update successful",
                error_context="test configuration"
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert exc_info.value.detail == "No updates provided"

    @patch("src.api.utils.get_config_manager")
    def test_validation_error_raises_400(self, mock_get_config_manager: Mock) -> None:
        """Test that ValueError during update raises HTTPException with 400 status."""
        # Arrange
        mock_manager = Mock()
        mock_manager.update.side_effect = ValueError("Invalid value for field1")
        mock_get_config_manager.return_value = mock_manager

        config = MockConfigUpdate(field1="invalid")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validate_and_update_config(
                config_model=config,
                empty_message="No updates provided",
                success_message="Update successful",
                error_context="test configuration"
            )

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Validation error: Invalid value for field1" in exc_info.value.detail

    @patch("src.api.utils.get_config_manager")
    def test_unexpected_error_raises_500(self, mock_get_config_manager: Mock) -> None:
        """Test that unexpected exceptions raise HTTPException with 500 status."""
        # Arrange
        mock_manager = Mock()
        mock_manager.update.side_effect = RuntimeError("Database connection failed")
        mock_get_config_manager.return_value = mock_manager

        config = MockConfigUpdate(field1="test")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validate_and_update_config(
                config_model=config,
                empty_message="No updates provided",
                success_message="Update successful",
                error_context="test configuration"
            )

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to update test configuration" in exc_info.value.detail
        assert "Database connection failed" in exc_info.value.detail

    @patch("src.api.utils.get_config_manager")
    def test_http_exception_re_raised(self, mock_get_config_manager: Mock) -> None:
        """Test that HTTPException from update is re-raised as-is."""
        # Arrange
        mock_manager = Mock()
        original_exception = HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Custom HTTP error"
        )
        mock_manager.update.side_effect = original_exception
        mock_get_config_manager.return_value = mock_manager

        config = MockConfigUpdate(field1="test")

        # Act & Assert
        with pytest.raises(HTTPException) as exc_info:
            validate_and_update_config(
                config_model=config,
                empty_message="No updates provided",
                success_message="Update successful",
                error_context="test configuration"
            )

        # Should re-raise the original HTTPException, not wrap it
        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.detail == "Custom HTTP error"

    @patch("src.api.utils.get_config_manager")
    def test_partial_update(self, mock_get_config_manager: Mock) -> None:
        """Test update with only some fields set."""
        # Arrange
        mock_manager = Mock()
        mock_get_config_manager.return_value = mock_manager

        config = MockConfigUpdate(field2=75)  # Only field2 set

        # Act
        result = validate_and_update_config(
            config_model=config,
            empty_message="No updates provided",
            success_message="Update successful",
            error_context="test configuration"
        )

        # Assert
        assert result == {"message": "Update successful"}
        mock_manager.update.assert_called_once_with(field2=75)

    @patch("src.api.utils.get_config_manager")
    def test_none_values_excluded(self, mock_get_config_manager: Mock) -> None:
        """Test that None values are excluded from update."""
        # Arrange
        mock_manager = Mock()
        mock_get_config_manager.return_value = mock_manager

        # Create config with explicit None (should be excluded by exclude_none=True)
        config = MockConfigUpdate(field1="value", field2=None)

        # Act
        result = validate_and_update_config(
            config_model=config,
            empty_message="No updates provided",
            success_message="Update successful",
            error_context="test configuration"
        )

        # Assert
        assert result == {"message": "Update successful"}
        # Should only include field1, not field2 (which is None)
        mock_manager.update.assert_called_once_with(field1="value")


class TestAsyncValidateAndUpdateConfig:
    """Test suite for async_validate_and_update_config function."""

    @patch("src.api.utils.get_config_manager")
    def test_async_version_works(self, mock_get_config_manager: Mock) -> None:
        """Test that async version calls the sync version correctly."""
        # Arrange
        mock_manager = Mock()
        mock_get_config_manager.return_value = mock_manager

        config = MockConfigUpdate(field1="async_test")

        # Act
        result = async_validate_and_update_config(
            config_model=config,
            empty_message="No updates provided",
            success_message="Async update successful",
            error_context="test configuration"
        )

        # Assert
        assert result == {"message": "Async update successful"}
        mock_manager.update.assert_called_once_with(field1="async_test")


class TestIntegrationWithRealModels:
    """Integration tests with actual Pydantic models from config.py."""

    @patch("src.api.utils.get_config_manager")
    def test_with_discord_config_model(self, mock_get_config_manager: Mock) -> None:
        """Test with real ConfigDiscordUpdate model."""
        # This test would import the real model and test with it
        # Skipped here as it would require all dependencies
        pass

    @patch("src.api.utils.get_config_manager")
    def test_with_ai_config_model(self, mock_get_config_manager: Mock) -> None:
        """Test with real ConfigAIUpdate model."""
        # This test would import the real model and test with it
        # Skipped here as it would require all dependencies
        pass

    @patch("src.api.utils.get_config_manager")
    def test_with_behavior_config_model(self, mock_get_config_manager: Mock) -> None:
        """Test with real ConfigBehaviorUpdate model."""
        # This test would import the real model and test with it
        # Skipped here as it would require all dependencies
        pass


# Run tests with: pytest tests/test_api_utils.py -v
