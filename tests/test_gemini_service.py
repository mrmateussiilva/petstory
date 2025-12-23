"""Tests for GeminiGenerator service."""

import io
import os
from unittest.mock import MagicMock, patch

import pytest
from PIL import Image

from app.services.gemini_service import GeminiGenerator, BOBBIE_GOODS_PROMPT


class TestGeminiGenerator:
    """Test suite for GeminiGenerator."""

    @pytest.fixture
    def mock_gemini_response(self):
        """Create a mock Gemini API response with image data."""
        # Create a simple test image
        test_image = Image.new("RGB", (100, 100), color="white")
        buffer = io.BytesIO()
        test_image.save(buffer, format="PNG")
        image_bytes = buffer.getvalue()
        
        # Create mock response structure
        mock_part = MagicMock()
        mock_part.inline_data = MagicMock()
        mock_part.inline_data.mime_type = "image/png"
        mock_part.inline_data.data = image_bytes
        
        mock_candidate = MagicMock()
        mock_candidate.content.parts = [mock_part]
        
        mock_response = MagicMock()
        mock_response.candidates = [mock_candidate]
        
        return mock_response

    def test_init_with_api_key(self):
        """Test initialization with API key."""
        with patch("app.services.gemini_service.genai.configure"):
            with patch("app.services.gemini_service.genai.GenerativeModel") as mock_model:
                generator = GeminiGenerator(api_key="test-key")
                assert generator.api_key == "test-key"
                mock_model.assert_called_once()

    def test_init_uses_settings(self):
        """Test initialization uses settings when no API key provided."""
        with patch("app.services.gemini_service.settings") as mock_settings:
            mock_settings.GEMINI_API_KEY = "settings-key"
            mock_settings.GEMINI_IMAGE_MODEL = "test-model"
            with patch("app.services.gemini_service.genai.configure"):
                with patch("app.services.gemini_service.genai.GenerativeModel"):
                    generator = GeminiGenerator()
                    assert generator.api_key == "settings-key"

    @pytest.mark.asyncio
    async def test_generate_success(self, sample_image_bytes, mock_gemini_response):
        """Test successful image generation."""
        with patch("app.services.gemini_service.genai.configure"):
            with patch("app.services.gemini_service.genai.GenerativeModel") as mock_model_class:
                mock_model = MagicMock()
                # generate_content is called synchronously (no await), so return value directly
                mock_model.generate_content = MagicMock(return_value=mock_gemini_response)
                mock_model_class.return_value = mock_model
                
                generator = GeminiGenerator(api_key="test-key")
                result = await generator.generate(sample_image_bytes, "test prompt")
                
                # Verify result is PNG bytes
                assert isinstance(result, bytes)
                assert len(result) > 0
                # Verify it's a valid PNG
                img = Image.open(io.BytesIO(result))
                assert img.format == "PNG"

    @pytest.mark.asyncio
    async def test_generate_with_rgb_conversion(self, sample_image_bytes, mock_gemini_response):
        """Test that non-RGB images are converted to RGB."""
        # Create RGBA image
        rgba_image = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        buffer = io.BytesIO()
        rgba_image.save(buffer, format="PNG")
        rgba_bytes = buffer.getvalue()
        
        with patch("app.services.gemini_service.genai.configure"):
            with patch("app.services.gemini_service.genai.GenerativeModel") as mock_model_class:
                mock_model = MagicMock()
                mock_model.generate_content = MagicMock(return_value=mock_gemini_response)
                mock_model_class.return_value = mock_model
                
                generator = GeminiGenerator(api_key="test-key")
                result = await generator.generate(rgba_bytes, "test prompt")
                
                # Should convert to RGB and return PNG
                assert isinstance(result, bytes)
                img = Image.open(io.BytesIO(result))
                assert img.mode == "RGB"

    @pytest.mark.asyncio
    async def test_generate_with_no_response(self, sample_image_bytes):
        """Test generation fails when API returns no image."""
        mock_response = MagicMock()
        mock_response.candidates = []
        
        with patch("app.services.gemini_service.genai.configure"):
            with patch("app.services.gemini_service.genai.GenerativeModel") as mock_model_class:
                mock_model = MagicMock()
                mock_model.generate_content = MagicMock(return_value=mock_response)
                mock_model_class.return_value = mock_model
                
                generator = GeminiGenerator(api_key="test-key")
                
                with pytest.raises(ValueError, match="No image generated"):
                    await generator.generate(sample_image_bytes, "test prompt")

    @pytest.mark.asyncio
    async def test_generate_handles_api_error(self, sample_image_bytes):
        """Test generation handles API errors gracefully."""
        with patch("app.services.gemini_service.genai.configure"):
            with patch("app.services.gemini_service.genai.GenerativeModel") as mock_model_class:
                mock_model = MagicMock()
                mock_model.generate_content = MagicMock(side_effect=Exception("API Error"))
                mock_model_class.return_value = mock_model
                
                generator = GeminiGenerator(api_key="test-key")
                
                with pytest.raises(Exception):
                    await generator.generate(sample_image_bytes, "test prompt")

    def test_generate_art_success(self, temp_dir, sample_image_path, mock_gemini_response):
        """Test generate_art method saves image to disk."""
        with patch("app.services.gemini_service.genai.configure"):
            with patch("app.services.gemini_service.genai.GenerativeModel") as mock_model_class:
                mock_model = MagicMock()
                mock_model.generate_content = MagicMock(return_value=mock_gemini_response)
                mock_model_class.return_value = mock_model
                
                generator = GeminiGenerator(api_key="test-key")
                output_path = generator.generate_art(sample_image_path, output_dir=temp_dir)
                
                # Verify file was created
                assert os.path.exists(output_path)
                assert output_path.endswith(".png")
                assert os.path.getsize(output_path) > 0
                # Verify it's a valid image
                img = Image.open(output_path)
                assert img.format == "PNG"

    def test_generate_art_uses_default_output_dir(self, sample_image_path, mock_gemini_response):
        """Test generate_art uses photo directory when output_dir is None."""
        photo_dir = os.path.dirname(sample_image_path)
        
        with patch("app.services.gemini_service.genai.configure"):
            with patch("app.services.gemini_service.genai.GenerativeModel") as mock_model_class:
                mock_model = MagicMock()
                mock_model.generate_content = MagicMock(return_value=mock_gemini_response)
                mock_model_class.return_value = mock_model
                
                generator = GeminiGenerator(api_key="test-key")
                output_path = generator.generate_art(sample_image_path, output_dir=None)
                
                # Should save in same directory as photo
                assert os.path.dirname(output_path) == photo_dir
                assert os.path.exists(output_path)

    def test_generate_art_handles_file_error(self, temp_dir):
        """Test generate_art handles missing photo file."""
        fake_photo_path = os.path.join(temp_dir, "nonexistent.jpg")
        
        with patch("app.services.gemini_service.genai.configure"):
            with patch("app.services.gemini_service.genai.GenerativeModel"):
                generator = GeminiGenerator(api_key="test-key")
                
                with pytest.raises(Exception):
                    generator.generate_art(fake_photo_path, output_dir=temp_dir)

    def test_bobbie_goods_prompt_defined(self):
        """Test that BOBBIE_GOODS_PROMPT is defined and not empty."""
        assert BOBBIE_GOODS_PROMPT
        assert len(BOBBIE_GOODS_PROMPT) > 0
        assert "coloring book" in BOBBIE_GOODS_PROMPT.lower() or "line art" in BOBBIE_GOODS_PROMPT.lower()

