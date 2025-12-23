"""PDF generation service for compiling coloring book pages."""

import io
import logging
import re
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
    
    def clean_text(self, text: str) -> str:
        """Remove emojis and non-Latin characters that FPDF cannot handle.
        
        Args:
            text: Input text that may contain emojis or special characters
            
        Returns:
            Cleaned text with only Latin characters, numbers, and basic punctuation
        """
        if not text:
            return ""
        
        # Remove emojis using regex
        # This pattern matches most emoji ranges
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # emoticons
            "\U0001F300-\U0001F5FF"  # symbols & pictographs
            "\U0001F680-\U0001F6FF"  # transport & map symbols
            "\U0001F1E0-\U0001F1FF"  # flags
            "\U00002702-\U000027B0"  # dingbats
            "\U000024C2-\U0001F251"  # enclosed characters
            "]+",
            flags=re.UNICODE
        )
        
        # Remove emojis
        text = emoji_pattern.sub('', text)
        
        # Keep only ASCII printable characters plus common Latin characters
        # This allows accented characters (á, é, í, ó, ú, ç, ã, etc.)
        text = ''.join(char for char in text if ord(char) < 256)
        
        return text.strip()
    
    def _add_polaroid_frame(self, pdf: FPDF, x: float, y: float, width: float, height: float):
        """Add a Polaroid-style frame around an image.
        
        Args:
            pdf: FPDF instance
            x: X position
            y: Y position
            width: Frame width
            height: Frame height (including bottom margin for Polaroid effect)
        """
        # Polaroid frame: white background with border
        frame_bottom_margin = 20  # Space for "caption" area at bottom
        image_height = height - frame_bottom_margin
        
        # White background
        pdf.set_fill_color(255, 255, 255)
        pdf.rect(x, y, width, height, style='F')
        
        # Border
        pdf.set_line_width(2)
        pdf.set_draw_color(200, 200, 200)
        pdf.rect(x, y, width, height, style='D')
        
        return image_height
    
    def create_digital_kit(
        self,
        pet_name: str,
        pet_date: str,
        pet_story: str,
        generated_art_paths: List[str],
        output_dir: str = ".",
        original_image_paths: Optional[List[str]] = None,
        sticker_paths: Optional[List[str]] = None,
    ) -> str:
        """Create a digital kit PDF with multiple pages: cover, biography, coloring pages, and sticker grid.
        
        Args:
            pet_name: Pet's name
            pet_date: Pet's date/birthday
            pet_story: Pet's story/biography text
            generated_art_paths: List of paths to generated art images (line art)
            output_dir: Directory to save the PDF
            original_image_paths: List of paths to original photos - used for biography page
            sticker_paths: List of paths to sticker images. If None, uses generated_art_paths as fallback
            
        Returns:
            Path to the created PDF file
        """
        import os
        from datetime import datetime
        
        # Clean text inputs to avoid FPDF encoding issues
        clean_pet_name = self.clean_text(pet_name)
        clean_pet_date = self.clean_text(pet_date)
        clean_pet_story = self.clean_text(pet_story)
        
        # Ensure we have at least one art
        if not generated_art_paths or len(generated_art_paths) == 0:
            raise ValueError("At least one generated art image is required")
        
        # Use first art for cover and biography fallback
        first_art_path = generated_art_paths[0]
        
        # Use first original photo for biography, fallback to first art if not available
        biography_image_path = first_art_path
        if original_image_paths and len(original_image_paths) > 0:
            first_original_path = original_image_paths[0]
            if os.path.exists(first_original_path):
                biography_image_path = first_original_path
        
        pdf = FPDF(orientation="P", unit="mm", format="A4")
        pdf.set_auto_page_break(auto=False)  # Disable auto page break for better control
        
        # ============================================
        # PAGE 1: COVER - Uses FIRST ART IMAGE (Line Art)
        # ============================================
        pdf.add_page()
        
        # Title: "Livro de Colorir do [pet_name]"
        pdf.set_font("Helvetica", "B", 32)
        title_y = 60
        pdf.set_y(title_y)
        title_text = f"Livro de Colorir do {clean_pet_name}"
        pdf.cell(0, 15, title_text, ln=1, align="C")
        
        # Image centered below title - USE FIRST ART IMAGE
        try:
            img = Image.open(first_art_path)
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            img_width, img_height = img.size
            aspect_ratio = img_width / img_height
            
            # Image dimensions for cover (large but with margins)
            max_width = 160
            max_height = 140
            
            if aspect_ratio > (max_width / max_height):
                width = max_width
                height = max_width / aspect_ratio
            else:
                height = max_height
                width = max_height * aspect_ratio
            
            # Center image horizontally and position below title
            x = (self.A4_WIDTH_MM - width) / 2
            y = title_y + 25
            
            temp_buffer = io.BytesIO()
            img.save(temp_buffer, format="PNG")
            temp_buffer.seek(0)
            
            pdf.image(temp_buffer, x=x, y=y, w=width, h=height)
        except Exception as e:
            logger.warning(f"Could not add art image to cover: {e}")
        
        # ============================================
        # PAGE 2: THE STORY (A História)
        # ============================================
        pdf.add_page()
        
        # Decorative border (rectangle around the page with margin)
        border_margin = 15
        pdf.set_line_width(2)
        pdf.rect(
            border_margin, 
            border_margin, 
            self.A4_WIDTH_MM - (2 * border_margin), 
            self.A4_HEIGHT_MM - (2 * border_margin)
        )
        
        # Title: "Quem é [pet_name]?"
        pdf.set_font("Helvetica", "B", 24)
        title_y = border_margin + 20
        pdf.set_y(title_y)
        title_text = f"Quem é {clean_pet_name}?"
        pdf.cell(0, 12, title_text, ln=1, align="C")
        
        # Subtitle: Date (italic, gray-like effect with smaller font)
        if clean_pet_date:
            pdf.set_font("Helvetica", "I", 14)
            pdf.set_text_color(100, 100, 100)  # Gray color
            pdf.set_y(pdf.get_y() + 5)
            pdf.cell(0, 8, clean_pet_date, ln=1, align="C")
            pdf.set_text_color(0, 0, 0)  # Reset to black
        
        # Polaroid-style photo frame with ORIGINAL IMAGE (Foto Real)
        polaroid_width = 80
        polaroid_height = 100
        polaroid_x = (self.A4_WIDTH_MM - polaroid_width) / 2
        polaroid_y = pdf.get_y() + 10
        
        try:
            img = Image.open(biography_image_path)
            if img.mode != "RGB":
                img = img.convert("RGB")
            
            img_width, img_height = img.size
            aspect_ratio = img_width / img_height
            
            # Calculate image size within Polaroid frame (leave space for bottom margin)
            frame_bottom_margin = 15
            image_area_height = polaroid_height - frame_bottom_margin
            image_area_width = polaroid_width - 6  # 3mm margin on each side
            
            if aspect_ratio > (image_area_width / image_area_height):
                photo_width = image_area_width
                photo_height = image_area_width / aspect_ratio
            else:
                photo_height = image_area_height
                photo_width = image_area_height * aspect_ratio
            
            # Center image within frame
            photo_x = polaroid_x + (polaroid_width - photo_width) / 2
            photo_y = polaroid_y + 3  # Small top margin
            
            # Draw Polaroid frame
            self._add_polaroid_frame(pdf, polaroid_x, polaroid_y, polaroid_width, polaroid_height)
            
            # Add photo inside frame
            temp_buffer = io.BytesIO()
            img.save(temp_buffer, format="PNG")
            temp_buffer.seek(0)
            
            pdf.image(temp_buffer, x=photo_x, y=photo_y, w=photo_width, h=photo_height)
            
            # Update Y position for text below Polaroid
            text_start_y = polaroid_y + polaroid_height + 15
        except Exception as e:
            logger.warning(f"Could not add original photo to biography page: {e}")
            text_start_y = pdf.get_y() + 15
        
        # Body text: Story with generous margins (book-like layout)
        text_margin = 25
        pdf.set_font("Helvetica", "", 12)
        pdf.set_xy(text_margin, text_start_y)
        
        # Calculate available width for text
        text_width = self.A4_WIDTH_MM - (2 * text_margin)
        
        # Multi-cell with justified text for book-like appearance
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(
            text_width, 
            7, 
            clean_pet_story, 
            align="J"  # Justified text
        )
        
        # ============================================
        # PAGES 3+: COLORING PAGES (Páginas de Colorir) - One page per art
        # ============================================
        for idx, art_path in enumerate(generated_art_paths, 1):
            pdf.add_page()
            
            # Title for this coloring page
            pdf.set_font("Helvetica", "B", 18)
            pdf.set_y(15)
            pdf.cell(0, 12, f"Desenho #{idx}", ln=1, align="C")
            
            try:
                img = Image.open(art_path)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                
                img_width, img_height = img.size
                aspect_ratio = img_width / img_height
                
                # Calculate dimensions to fill entire A4 page (full bleed)
                # Use small margins to ensure full coverage
                bleed_margin = 5
                available_width = self.A4_WIDTH_MM - (2 * bleed_margin)
                available_height = self.A4_HEIGHT_MM - 40  # Leave space for title
                
                # Fill page maintaining aspect ratio
                if aspect_ratio > (available_width / available_height):
                    # Image is wider
                    width = available_width
                    height = available_width / aspect_ratio
                    # Center vertically
                    x = bleed_margin
                    y = (self.A4_HEIGHT_MM - height) / 2
                else:
                    # Image is taller
                    height = available_height
                    width = available_height * aspect_ratio
                    # Center horizontally
                    x = (self.A4_WIDTH_MM - width) / 2
                    y = 40
                
                temp_buffer = io.BytesIO()
                img.save(temp_buffer, format="PNG")
                temp_buffer.seek(0)
                
                pdf.image(temp_buffer, x=x, y=y, w=width, h=height)
            except Exception as e:
                logger.error(f"Error adding coloring page {idx} image: {e}")
        
        # ============================================
        # LAST PAGE: STICKERS (Adesivos) - Grid 3x3 - Uses sticker images if available
        # ============================================
        pdf.add_page()
        
        # Title
        pdf.set_font("Helvetica", "B", 18)
        pdf.set_y(15)
        pdf.cell(0, 12, "Adesivos", ln=1, align="C")
        
        # Use sticker_paths if provided, otherwise fallback to generated_art_paths
        sticker_images = sticker_paths if sticker_paths and len(sticker_paths) > 0 else generated_art_paths
        
        # Grid 3x3 configuration (9 stickers total)
        sticker_size = 50
        spacing = 10
        grid_width = (3 * sticker_size) + (2 * spacing)
        start_x = (self.A4_WIDTH_MM - grid_width) / 2
        start_y = 40
        
        # Fill grid with stickers (repeat if necessary to fill 9 slots)
        sticker_index = 0
        for row in range(3):
            for col in range(3):
                # Cycle through available stickers
                sticker_path = sticker_images[sticker_index % len(sticker_images)]
                sticker_index += 1
                
                try:
                    img = Image.open(sticker_path)
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    
                    x = start_x + col * (sticker_size + spacing)
                    y = start_y + row * (sticker_size + spacing)
                    
                    temp_buffer = io.BytesIO()
                    img.save(temp_buffer, format="PNG")
                    temp_buffer.seek(0)
                    
                    pdf.image(temp_buffer, x=x, y=y, w=sticker_size, h=sticker_size)
                except Exception as e:
                    logger.error(f"Error adding sticker {row * 3 + col + 1} from {sticker_path}: {e}")
        
        # Save PDF
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = os.path.join(output_dir, f"kit_digital_{timestamp}.pdf")
        pdf.output(pdf_filename)
        
        logger.info(f"Digital kit PDF created: {pdf_filename}")
        return pdf_filename

