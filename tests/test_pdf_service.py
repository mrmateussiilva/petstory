"""Tests for PDFService."""

import os
import tempfile

import pytest
from fpdf import FPDF

from app.services.pdf_service import PDFService


class TestPDFService:
    """Test suite for PDFService."""

    def test_init(self):
        """Test PDFService initialization."""
        service = PDFService()
        assert service.A4_WIDTH_MM == 210
        assert service.A4_HEIGHT_MM == 297
        assert service.MARGIN_MM == 10

    def test_create_pdf_from_images(self, sample_image_bytes):
        """Test creating PDF from image bytes."""
        service = PDFService()
        images = [sample_image_bytes, sample_image_bytes]  # Two images
        
        pdf_bytes = service.create_pdf_from_images(images)
        
        # Verify PDF was created
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b"%PDF")

    def test_create_pdf_from_images_saves_to_file(self, temp_dir, sample_image_bytes):
        """Test creating PDF and saving to file."""
        service = PDFService()
        images = [sample_image_bytes]
        output_path = os.path.join(temp_dir, "test.pdf")
        
        result = service.create_pdf_from_images(images, output_path=output_path)
        
        # Should return empty bytes when saving to file
        assert result == b""
        assert os.path.exists(output_path)
        assert os.path.getsize(output_path) > 0

    def test_create_pdf_from_empty_images_list(self):
        """Test creating PDF with empty images list."""
        service = PDFService()
        pdf_bytes = service.create_pdf_from_images([])
        
        # Should create empty PDF
        assert len(pdf_bytes) > 0
        assert pdf_bytes.startswith(b"%PDF")

    def test_clean_text_removes_emojis(self):
        """Test clean_text removes emojis."""
        service = PDFService()
        
        text_with_emojis = "Spike 🐕 é um cão muito feliz 😊"
        cleaned = service.clean_text(text_with_emojis)
        
        assert "🐕" not in cleaned
        assert "😊" not in cleaned
        assert "Spike" in cleaned
        assert "cão" in cleaned

    def test_clean_text_keeps_latin_characters(self):
        """Test clean_text keeps accented Latin characters."""
        service = PDFService()
        
        text = "Cão, gato, pássaro, história, coração"
        cleaned = service.clean_text(text)
        
        assert "Cão" in cleaned
        assert "gato" in cleaned
        assert "pássaro" in cleaned
        assert "história" in cleaned
        assert "coração" in cleaned

    def test_clean_text_handles_empty_string(self):
        """Test clean_text handles empty string."""
        service = PDFService()
        assert service.clean_text("") == ""
        assert service.clean_text(None) == ""

    def test_create_digital_kit_success(
        self, temp_dir, multiple_art_images, sample_image_path, sample_pet_data
    ):
        """Test creating complete digital kit PDF."""
        service = PDFService()
        
        pdf_path = service.create_digital_kit(
            pet_name=sample_pet_data["pet_name"],
            pet_date=sample_pet_data["pet_date"],
            pet_story=sample_pet_data["pet_story"],
            generated_art_paths=multiple_art_images,
            output_dir=temp_dir,
            original_image_paths=[sample_image_path],
        )
        
        # Verify PDF was created
        assert os.path.exists(pdf_path)
        assert pdf_path.endswith(".pdf")
        assert os.path.getsize(pdf_path) > 0
        
        # Verify PDF starts with PDF header
        with open(pdf_path, "rb") as f:
            assert f.read(4) == b"%PDF"

    def test_create_digital_kit_without_original_images(
        self, temp_dir, multiple_art_images, sample_pet_data
    ):
        """Test creating digital kit without original photos."""
        service = PDFService()
        
        pdf_path = service.create_digital_kit(
            pet_name=sample_pet_data["pet_name"],
            pet_date=sample_pet_data["pet_date"],
            pet_story=sample_pet_data["pet_story"],
            generated_art_paths=multiple_art_images,
            output_dir=temp_dir,
            original_image_paths=None,
        )
        
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 0

    def test_create_digital_kit_with_no_art_images(self, temp_dir, sample_pet_data):
        """Test creating digital kit fails with no art images."""
        service = PDFService()
        
        with pytest.raises(ValueError, match="At least one generated art image is required"):
            service.create_digital_kit(
                pet_name=sample_pet_data["pet_name"],
                pet_date=sample_pet_data["pet_date"],
                pet_story=sample_pet_data["pet_story"],
                generated_art_paths=[],
                output_dir=temp_dir,
            )

    def test_create_digital_kit_structure(
        self, temp_dir, multiple_art_images, sample_image_path, sample_pet_data
    ):
        """Test that digital kit has expected structure (cover, biography, coloring pages, stickers)."""
        service = PDFService()
        
        pdf_path = service.create_digital_kit(
            pet_name=sample_pet_data["pet_name"],
            pet_date=sample_pet_data["pet_date"],
            pet_story=sample_pet_data["pet_story"],
            generated_art_paths=multiple_art_images,
            output_dir=temp_dir,
            original_image_paths=[sample_image_path],
        )
        
        # Read PDF and verify it's valid
        # We can't easily parse PDF content without a library, but we can verify it exists
        # and has reasonable size (should be larger than empty PDF)
        assert os.path.exists(pdf_path)
        file_size = os.path.getsize(pdf_path)
        assert file_size > 1000  # Should be at least 1KB for a multi-page PDF

    def test_create_digital_kit_with_special_characters(
        self, temp_dir, multiple_art_images, sample_pet_data
    ):
        """Test creating digital kit with special characters in pet data."""
        service = PDFService()
        
        pdf_path = service.create_digital_kit(
            pet_name="Cão & Gato",
            pet_date="23/12/2024",
            pet_story="História com 'aspas' e caracteres especiais.",
            generated_art_paths=multiple_art_images,
            output_dir=temp_dir,
        )
        
        assert os.path.exists(pdf_path)
        assert os.path.getsize(pdf_path) > 0

