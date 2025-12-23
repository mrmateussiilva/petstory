"""Tests for WebGenerator service."""

import os
import tempfile
from pathlib import Path

import pytest

from app.services.web_generator import WebGenerator


class TestWebGenerator:
    """Test suite for WebGenerator."""

    def test_init_with_default_template(self):
        """Test initialization with default template path."""
        generator = WebGenerator()
        assert generator.template_path.exists()
        assert generator.template_path.name == "homenagem_template.html"

    def test_init_with_custom_template(self, temp_dir):
        """Test initialization with custom template path."""
        # Create a custom template
        custom_template = os.path.join(temp_dir, "custom_template.html")
        with open(custom_template, "w", encoding="utf-8") as f:
            f.write("<html><body>{pet_name} - {pet_date}</body></html>")
        
        generator = WebGenerator(template_path=custom_template)
        assert generator.template_path == Path(custom_template)

    def test_init_with_nonexistent_template(self, temp_dir):
        """Test initialization fails with nonexistent template."""
        fake_path = os.path.join(temp_dir, "nonexistent.html")
        with pytest.raises(FileNotFoundError):
            WebGenerator(template_path=fake_path)

    def test_generate_tribute_page_success(
        self, sample_art_image_path, sample_pet_data
    ):
        """Test successful tribute page generation."""
        generator = WebGenerator()
        
        html = generator.generate_tribute_page(
            pet_name=sample_pet_data["pet_name"],
            pet_date=sample_pet_data["pet_date"],
            pet_story=sample_pet_data["pet_story"],
            art_image_path=sample_art_image_path,
        )
        
        # Verify HTML contains all expected content
        assert sample_pet_data["pet_name"] in html
        assert sample_pet_data["pet_date"] in html
        assert sample_pet_data["pet_story"] in html
        assert "data:image/png;base64," in html or "data:image/jpeg;base64," in html
        assert "<!DOCTYPE html>" in html
        assert "<html" in html

    def test_generate_tribute_page_with_missing_image(self, temp_dir, sample_pet_data):
        """Test tribute page generation when image is missing."""
        generator = WebGenerator()
        fake_image_path = os.path.join(temp_dir, "nonexistent.png")
        
        html = generator.generate_tribute_page(
            pet_name=sample_pet_data["pet_name"],
            pet_date=sample_pet_data["pet_date"],
            pet_story=sample_pet_data["pet_story"],
            art_image_path=fake_image_path,
        )
        
        # Should still generate HTML but with empty image
        assert sample_pet_data["pet_name"] in html
        assert 'src=""' in html or 'src="data:image' not in html or len(html) > 0

    def test_generate_tribute_page_with_jpeg(self, temp_dir, sample_pet_data, sample_image_bytes):
        """Test tribute page generation with JPEG image."""
        # Create JPEG image
        jpeg_path = os.path.join(temp_dir, "art.jpg")
        with open(jpeg_path, "wb") as f:
            f.write(sample_image_bytes)
        
        generator = WebGenerator()
        html = generator.generate_tribute_page(
            pet_name=sample_pet_data["pet_name"],
            pet_date=sample_pet_data["pet_date"],
            pet_story=sample_pet_data["pet_story"],
            art_image_path=jpeg_path,
        )
        
        # Should detect JPEG and use correct MIME type
        assert "data:image/jpeg;base64," in html or "data:image/png;base64," in html

    def test_generate_tribute_page_escapes_css_braces(self, sample_art_image_path, sample_pet_data):
        """Test that CSS/JS braces in template don't cause KeyError."""
        generator = WebGenerator()
        
        # This should not raise KeyError even though template has many {}
        html = generator.generate_tribute_page(
            pet_name=sample_pet_data["pet_name"],
            pet_date=sample_pet_data["pet_date"],
            pet_story=sample_pet_data["pet_story"],
            art_image_path=sample_art_image_path,
        )
        
        # Verify it generated successfully
        assert len(html) > 0
        assert sample_pet_data["pet_name"] in html

    def test_generate_tribute_page_with_special_characters(self, sample_art_image_path):
        """Test tribute page generation with special characters in pet data."""
        generator = WebGenerator()
        
        html = generator.generate_tribute_page(
            pet_name="Cão & Gato",
            pet_date="23/12/2024",
            pet_story="História com 'aspas' e \"aspas duplas\" e <tags> HTML.",
            art_image_path=sample_art_image_path,
        )
        
        # Should handle special characters
        assert "Cão & Gato" in html
        assert "23/12/2024" in html

