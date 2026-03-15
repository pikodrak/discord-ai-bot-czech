"""
Tests for API validation utilities.

Tests the reusable validation wrapper functions for request validation,
error catching, and HTTPException raising.
"""

import pytest
from fastapi import HTTPException, status
from pydantic import BaseModel

from src.api.validation import (
    validate_config_update,
    validate_update_data,
    extract_update_data
)


class TestConfigModel(BaseModel):
    """Test configuration model."""
    field1: str | None = None
    field2: int | None = None
    field3: bool | None = None


class TestValidateUpdateData:
    """Tests for validate_update_data function."""

    def test_validate_update_data_with_data(self):
        """Test validation passes with non-empty data."""
        update_data = {"field1": "value1", "field2": 42}
        # Should not raise
        validate_update_data(update_data, "test configuration")

    def test_validate_update_data_empty_dict(self):
        """Test validation fails with empty dict."""
        with pytest.raises(HTTPException) as exc_info:
            validate_update_data({}, "test configuration")

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "No test configuration updates provided" in exc_info.value.detail

    def test_validate_update_data_custom_config_type(self):
        """Test validation uses custom config type in error message."""
        with pytest.raises(HTTPException) as exc_info:
            validate_update_data({}, "Discord settings")

        assert "No Discord settings updates provided" in exc_info.value.detail


class TestExtractUpdateData:
    """Tests for extract_update_data function."""

    def test_extract_all_fields_set(self):
        """Test extraction with all fields set."""
        config = TestConfigModel(field1="test", field2=42, field3=True)
        result = extract_update_data(config)

        assert result == {"field1": "test", "field2": 42, "field3": True}

    def test_extract_partial_fields_set(self):
        """Test extraction with only some fields set."""
        config = TestConfigModel(field1="test")
        result = extract_update_data(config)

        assert result == {"field1": "test"}
        assert "field2" not in result
        assert "field3" not in result

    def test_extract_no_fields_set(self):
        """Test extraction with no fields set."""
        config = TestConfigModel()
        result = extract_update_data(config)

        assert result == {}

    def test_extract_none_values_excluded(self):
        """Test that None values are excluded."""
        config = TestConfigModel(field1="test", field2=None)
        result = extract_update_data(config)

        assert result == {"field1": "test"}
        assert "field2" not in result


class TestValidateConfigUpdateDecorator:
    """Tests for validate_config_update decorator."""

    @pytest.mark.asyncio
    async def test_successful_update(self):
        """Test decorator allows successful updates through."""
        @validate_config_update("test configuration")
        async def mock_endpoint():
            return {"message": "Success"}

        result = await mock_endpoint()
        assert result == {"message": "Success"}

    @pytest.mark.asyncio
    async def test_catches_value_error(self):
        """Test decorator catches ValueError and raises 400."""
        @validate_config_update("test configuration")
        async def mock_endpoint():
            raise ValueError("Invalid value")

        with pytest.raises(HTTPException) as exc_info:
            await mock_endpoint()

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "Validation error: Invalid value" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_catches_generic_exception(self):
        """Test decorator catches generic Exception and raises 500."""
        @validate_config_update("test configuration")
        async def mock_endpoint():
            raise RuntimeError("Something went wrong")

        with pytest.raises(HTTPException) as exc_info:
            await mock_endpoint()

        assert exc_info.value.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
        assert "Failed to update test configuration" in exc_info.value.detail
        assert "Something went wrong" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_reraises_http_exception(self):
        """Test decorator re-raises HTTPException as-is."""
        @validate_config_update("test configuration")
        async def mock_endpoint():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Custom error"
            )

        with pytest.raises(HTTPException) as exc_info:
            await mock_endpoint()

        assert exc_info.value.status_code == status.HTTP_403_FORBIDDEN
        assert exc_info.value.detail == "Custom error"

    @pytest.mark.asyncio
    async def test_custom_config_type_in_error(self):
        """Test decorator uses custom config_type in error messages."""
        @validate_config_update("Discord settings")
        async def mock_endpoint():
            raise RuntimeError("Error occurred")

        with pytest.raises(HTTPException) as exc_info:
            await mock_endpoint()

        assert "Failed to update Discord settings" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_custom_success_message(self):
        """Test decorator with custom success message."""
        custom_message = "Discord configuration updated successfully"

        @validate_config_update(
            "Discord configuration",
            success_message=custom_message
        )
        async def mock_endpoint():
            return {"message": custom_message}

        result = await mock_endpoint()
        assert result["message"] == custom_message

    @pytest.mark.asyncio
    async def test_preserves_function_metadata(self):
        """Test decorator preserves original function metadata."""
        @validate_config_update("test configuration")
        async def mock_endpoint():
            """Original docstring."""
            pass

        assert mock_endpoint.__name__ == "mock_endpoint"
        assert mock_endpoint.__doc__ == "Original docstring."

    @pytest.mark.asyncio
    async def test_with_args_and_kwargs(self):
        """Test decorator works with function arguments."""
        @validate_config_update("test configuration")
        async def mock_endpoint(arg1: str, arg2: int, kwarg1: str = "default"):
            return {"arg1": arg1, "arg2": arg2, "kwarg1": kwarg1}

        result = await mock_endpoint("test", 42, kwarg1="custom")
        assert result == {"arg1": "test", "arg2": 42, "kwarg1": "custom"}

    @pytest.mark.asyncio
    async def test_integration_with_pydantic_model(self):
        """Test decorator integration with Pydantic model extraction."""
        @validate_config_update("test configuration")
        async def mock_endpoint(config: TestConfigModel):
            update_data = extract_update_data(config)
            validate_update_data(update_data, "test configuration")
            return {"message": "Success", "data": update_data}

        config = TestConfigModel(field1="value1", field2=42)
        result = await mock_endpoint(config)

        assert result["message"] == "Success"
        assert result["data"] == {"field1": "value1", "field2": 42}

    @pytest.mark.asyncio
    async def test_integration_with_empty_pydantic_model(self):
        """Test decorator integration with empty Pydantic model."""
        @validate_config_update("test configuration")
        async def mock_endpoint(config: TestConfigModel):
            update_data = extract_update_data(config)
            validate_update_data(update_data, "test configuration")
            return {"message": "Success"}

        config = TestConfigModel()

        with pytest.raises(HTTPException) as exc_info:
            await mock_endpoint(config)

        assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
        assert "No test configuration updates provided" in exc_info.value.detail
