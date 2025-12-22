"""PDF generation service for compiling coloring book pages."""

import io
import logging
from typing import List, Optional

from fpdf import FPDF
from PIL import Image

logger = logging.getLogger(__name__)


class PDFService:
    """Service for creating PDFs from images."""

    # A4 dimensions in mm
    A4_WIDTH_MM = 210
    A4_HEIGHT_MM = 297
    MARGIN_MM = 10

    def __init__(self):
        """Initialize PDF service."""
        pass

    def create_pdf_from_images(
        self, images: List[bytes], output_path: Optional[str] = None
    ) -> bytes:
        """Create a PDF from a list of image bytes.
        
        Args:
            images: List of image bytes (PNG/JPEG)
            output_path: Optional path to save PDF. If None, returns bytes.
            
        Returns:
            PDF as bytes
        """
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        
        for idx, image_bytes in enumerate(images):
            try:
                # Load image
                img = Image.open(io.BytesIO(image_bytes))
                
                # Convert to RGB if necessary
                if img.mode != "RGB":
                    img = img.convert("RGB")
                
                # Calculate dimensions to fit A4 with margins
                available_width = self.A4_WIDTH_MM - (2 * self.MARGIN_MM)
                available_height = self.A4_HEIGHT_MM - (2 * self.MARGIN_MM)
                
                img_width, img_height = img.size
                aspect_ratio = img_width / img_height
                
                # Fit image to available space maintaining aspect ratio
                if aspect_ratio > (available_width / available_height):
                    # Image is wider
                    width = available_width
                    height = available_width / aspect_ratio
                else:
                    # Image is taller
                    height = available_height
                    width = available_height * aspect_ratio
                
                # Center image
                x_offset = (self.A4_WIDTH_MM - width) / 2
                y_offset = (self.A4_HEIGHT_MM - height) / 2
                
                # Save image to temporary file for FPDF
                temp_buffer = io.BytesIO()
                img.save(temp_buffer, format="PNG")
                temp_buffer.seek(0)
                
                # Add page
                pdf.add_page()
                
                # Add image to PDF
                pdf.image(
                    temp_buffer,
                    x=x_offset,
                    y=y_offset,
                    w=width,
                    h=height,
                )
                
                logger.info(f"Added image {idx + 1}/{len(images)} to PDF")
                
            except Exception as e:
                logger.error(
                    f"Error adding image {idx + 1} to PDF: {str(e)}",
                    exc_info=True,
                )
                # Continue with next image even if one fails
                continue
        
        if output_path:
            pdf.output(output_path)
            logger.info(f"PDF saved to {output_path}")
            return b""
        else:
            # Return PDF as bytes
            # pdf.output(dest="S") returns bytes/bytearray, not a string
            pdf_output = pdf.output(dest="S")
            if isinstance(pdf_output, bytearray):
                pdf_bytes = bytes(pdf_output)
            elif isinstance(pdf_output, bytes):
                pdf_bytes = pdf_output
            else:
                # If it's a string, encode it
                pdf_bytes = pdf_output.encode("latin-1")
            logger.info(f"PDF generated ({len(pdf_bytes)} bytes)")
            return pdf_bytes

