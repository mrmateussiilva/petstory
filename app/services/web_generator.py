"""Web generator service for creating tribute pages."""

import base64
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class WebGenerator:
    """Service for generating HTML tribute pages."""

    def __init__(self, template_path: Optional[str] = None):
        """Initialize web generator service.
        
        Args:
            template_path: Path to HTML template file. If None, uses default.
        """
        if template_path is None:
            # Default template path relative to this file
            template_dir = Path(__file__).parent / "templates"
            template_path = template_dir / "homenagem_template.html"
        
        self.template_path = Path(template_path)
        
        # Validate template exists
        if not self.template_path.exists():
            raise FileNotFoundError(
                f"Template file not found: {self.template_path}. "
                f"Please create the template file or provide a valid path."
            )
        
        logger.info(f"WebGenerator initialized with template: {self.template_path}")

    def _load_template(self) -> str:
        """Load HTML template from file.
        
        Returns:
            Template content as string
            
        Raises:
            IOError: If template file cannot be read
        """
        try:
            with open(self.template_path, "r", encoding="utf-8") as f:
                template_content = f.read()
            logger.debug(f"Template loaded successfully from {self.template_path}")
            return template_content
        except Exception as e:
            logger.error(f"Error loading template from {self.template_path}: {e}")
            raise

    def generate_tribute_page(
        self,
        pet_name: str,
        pet_date: str,
        pet_story: str,
        art_image_path: str,
    ) -> str:
        """Generate a beautiful HTML tribute page with Tailwind CSS.
        
        Args:
            pet_name: Pet's name
            pet_date: Pet's date/birthday
            pet_story: Pet's story/biography text
            art_image_path: Path to the generated art image
            
        Returns:
            HTML string with the tribute page
        """
        # Read and encode image as base64
        try:
            with open(art_image_path, "rb") as f:
                image_data = f.read()
                image_base64 = base64.b64encode(image_data).decode("utf-8")
                # Determine image MIME type from extension
                ext = Path(art_image_path).suffix.lower()
                mime_type = "image/png" if ext == ".png" else "image/jpeg"
                image_data_uri = f"data:{mime_type};base64,{image_base64}"
            logger.debug(f"Image encoded successfully: {len(image_data)} bytes")
        except Exception as e:
            logger.error(f"Error reading image for web page: {e}")
            image_data_uri = ""  # Fallback to empty image
        
        # Load template
        template = self._load_template()

        # Replace placeholders manually instead of using str.format.
        # The template contains many CSS/JS curly braces ({}) that would
        # conflict with str.format and cause KeyError for things like
        # "\n      margin". To avoid having to escape all CSS braces, we
        # perform simple string replacements only for our known markers.
        html = (
            template
            .replace("{pet_name}", pet_name)
            .replace("{pet_date}", pet_date)
            .replace("{pet_story}", pet_story)
            .replace("{image_data_uri}", image_data_uri)
        )
        
        logger.info(f"Tribute page generated successfully for {pet_name}")
        return html

