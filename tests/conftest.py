"""Pytest configuration and shared fixtures."""

import io
import os
import tempfile
from pathlib import Path

import pytest
from PIL import Image


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def sample_image_bytes():
    """Create a sample PNG image as bytes for testing."""
    # Create a simple 100x100 red square image
    img = Image.new("RGB", (100, 100), color="red")
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def sample_image_path(temp_dir, sample_image_bytes):
    """Create a sample image file on disk."""
    image_path = os.path.join(temp_dir, "sample_image.png")
    with open(image_path, "wb") as f:
        f.write(sample_image_bytes)
    return image_path


@pytest.fixture
def sample_art_image_bytes():
    """Create a sample art image (line art style) as bytes."""
    # Create a simple black and white line art style image
    img = Image.new("RGB", (200, 200), color="white")
    # Draw a simple black border
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    draw.rectangle([10, 10, 190, 190], outline="black", width=5)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


@pytest.fixture
def sample_art_image_path(temp_dir, sample_art_image_bytes):
    """Create a sample art image file on disk."""
    art_path = os.path.join(temp_dir, "art_image.png")
    with open(art_path, "wb") as f:
        f.write(sample_art_image_bytes)
    return art_path


@pytest.fixture
def multiple_art_images(temp_dir, sample_art_image_bytes):
    """Create multiple art image files for testing."""
    art_paths = []
    for i in range(3):
        art_path = os.path.join(temp_dir, f"art_{i+1}.png")
        with open(art_path, "wb") as f:
            f.write(sample_art_image_bytes)
        art_paths.append(art_path)
    return art_paths


@pytest.fixture
def sample_pet_data():
    """Sample pet data for testing."""
    return {
        "pet_name": "Spike",
        "pet_date": "23 de dezembro de 2024",
        "pet_story": "Spike é um cão muito brincalhão e carinhoso. Ele adora correr no parque e brincar com bolinhas.",
    }

