"""PDF generation service for compiling coloring book pages."""

import io
import logging
import os
import re
from pathlib import Path
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
        # Get path to fonts directory
        self.fonts_dir = Path(__file__).parent.parent.parent / "fonts"
        self.custom_font_path = self.fonts_dir / "PatrickHand-Regular.ttf"
        self.font_name = "PatrickHand"
    
    def _add_custom_font(self, pdf: FPDF) -> None:
        """Add custom font to PDF if available.
        
        Args:
            pdf: FPDF instance to add font to
        """
        try:
            if self.custom_font_path.exists():
                # Add font to FPDF (True = use font file, False = don't embed subset)
                pdf.add_font(
                    self.font_name,
                    "",
                    str(self.custom_font_path),
                    uni=True
                )
                logger.info(f"Custom font loaded: {self.font_name}")
            else:
                logger.warning(f"Custom font not found at {self.custom_font_path}, using default")
        except Exception as e:
            logger.warning(f"Could not load custom font: {e}, using default")
    
    def _set_font(self, pdf: FPDF, style: str = "", size: int = 12) -> None:
        """Set font with fallback to Helvetica if custom font not available.
        
        Args:
            pdf: FPDF instance
            style: Font style ("", "B", "I", "BI")
            size: Font size
        """
        try:
            # Try to use custom font
            if self.custom_font_path.exists():
                pdf.set_font(self.font_name, style, size)
            else:
                # Fallback to Helvetica
                pdf.set_font("Helvetica", style, size)
        except Exception as e:
            logger.warning(f"Could not set custom font: {e}, using Helvetica")
            pdf.set_font("Helvetica", style, size)

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
        story_text: Optional[str] = None,
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
            story_text: Optional generated story text to be divided across coloring pages
            
        Returns:
            Path to the created PDF file
        """
        import os
        from datetime import datetime
        
        # Clean text inputs to avoid FPDF encoding issues
        clean_pet_name = self.clean_text(pet_name)
        clean_pet_date = self.clean_text(pet_date)
        clean_pet_story = self.clean_text(pet_story)
        
        # Parse and divide story text into parts (one per coloring page)
        story_parts = []
        if story_text:
            # Split by "---" separator
            parts = story_text.split("---")
            # Clean each part and remove empty lines
            for part in parts:
                # Remove "Parte X:" prefix if present
                cleaned_part = re.sub(r'^Parte\s+\d+:\s*', '', part.strip(), flags=re.IGNORECASE)
                # Remove extra whitespace and newlines
                cleaned_part = ' '.join(cleaned_part.split())
                if cleaned_part:
                    story_parts.append(self.clean_text(cleaned_part))
            
            # If we don't have enough parts, pad with empty strings
            while len(story_parts) < len(generated_art_paths):
                story_parts.append("")
            
            # If we have too many parts, truncate
            story_parts = story_parts[:len(generated_art_paths)]
        
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
        
        # Add custom font
        self._add_custom_font(pdf)
        
        # ============================================
        # PAGE 1: COVER - Uses FIRST ART IMAGE (Line Art)
        # ============================================
        pdf.add_page()
        
        # Decorative border/moldure around the page
        border_margin = 10
        pdf.set_line_width(3)
        pdf.set_draw_color(100, 150, 200)  # Light blue decorative border
        pdf.rect(
            border_margin, 
            border_margin, 
            self.A4_WIDTH_MM - (2 * border_margin), 
            self.A4_HEIGHT_MM - (2 * border_margin)
        )
        
        # Inner decorative border
        inner_margin = 15
        pdf.set_line_width(1)
        pdf.set_draw_color(200, 200, 200)  # Light gray inner border
        pdf.rect(
            inner_margin, 
            inner_margin, 
            self.A4_WIDTH_MM - (2 * inner_margin), 
            self.A4_HEIGHT_MM - (2 * inner_margin)
        )
        
        # Title: "Livro de Colorir do [pet_name]" - Using Times font for title
        pdf.set_font("Times", "B", 36)  # Different font for title
        title_y = 50
        pdf.set_y(title_y)
        title_text = f"Livro de Colorir do {clean_pet_name}"
        pdf.cell(0, 18, title_text, ln=1, align="C")
        
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
        # PAGE 2: THE STORY (A História) - Show ALL original photos
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
        self._set_font(pdf, "B", 24)
        title_y = border_margin + 15
        pdf.set_y(title_y)
        title_text = f"Quem é {clean_pet_name}?"
        pdf.cell(0, 12, title_text, ln=1, align="C")
        
        # Subtitle: Date (italic, gray-like effect with smaller font)
        if clean_pet_date:
            self._set_font(pdf, "I", 14)
            pdf.set_text_color(100, 100, 100)  # Gray color
            pdf.set_y(pdf.get_y() + 5)
            pdf.cell(0, 8, clean_pet_date, ln=1, align="C")
            pdf.set_text_color(0, 0, 0)  # Reset to black
        
        # Show ALL original photos in a grid layout
        photos_start_y = pdf.get_y() + 10
        
        # Get all original photos
        all_original_photos = []
        if original_image_paths and len(original_image_paths) > 0:
            for photo_path in original_image_paths:
                if os.path.exists(photo_path):
                    all_original_photos.append(photo_path)
        
        # If no original photos, use first art as fallback
        if not all_original_photos:
            if os.path.exists(biography_image_path):
                all_original_photos = [biography_image_path]
        
        # Calculate grid layout based on number of photos
        num_photos = len(all_original_photos)
        if num_photos > 0:
            # Determine grid: 1 photo = 1 column, 2-4 photos = 2 columns, 5+ = 3 columns
            if num_photos == 1:
                cols = 1
            elif num_photos <= 4:
                cols = 2
            else:
                cols = 3
            
            rows = (num_photos + cols - 1) // cols  # Ceiling division
            
            # Calculate photo size based on grid
            photo_spacing = 8
            available_width = self.A4_WIDTH_MM - (2 * border_margin) - (cols - 1) * photo_spacing
            available_height = 120  # Reserve space for text below
            
            photo_width = available_width / cols
            photo_height = min(available_height / rows, photo_width * 0.75)  # Keep reasonable aspect
            
            # Draw photos in grid
            current_y = photos_start_y
            photo_idx = 0
            
            for row in range(rows):
                if photo_idx >= num_photos:
                    break
                    
                current_x = border_margin
                
                for col in range(cols):
                    if photo_idx >= num_photos:
                        break
                    
                    photo_path = all_original_photos[photo_idx]
                    
                    try:
                        img = Image.open(photo_path)
                        if img.mode != "RGB":
                            img = img.convert("RGB")
                        
                        img_width, img_height = img.size
                        aspect_ratio = img_width / img_height
                        
                        # Calculate dimensions maintaining aspect ratio
                        if aspect_ratio > (photo_width / photo_height):
                            width = photo_width
                            height = photo_width / aspect_ratio
                        else:
                            height = photo_height
                            width = photo_height * aspect_ratio
                        
                        # Center within cell
                        cell_x = current_x + (photo_width - width) / 2
                        cell_y = current_y + (photo_height - height) / 2
                        
                        # Draw Polaroid-style frame
                        frame_margin = 2
                        self._add_polaroid_frame(
                            pdf, 
                            current_x - frame_margin, 
                            current_y - frame_margin, 
                            photo_width + (2 * frame_margin), 
                            photo_height + (2 * frame_margin) + 10
                        )
                        
                        # Add photo
                        temp_buffer = io.BytesIO()
                        img.save(temp_buffer, format="PNG")
                        temp_buffer.seek(0)
                        
                        pdf.image(temp_buffer, x=cell_x, y=cell_y, w=width, h=height)
                        
                        photo_idx += 1
                        current_x += photo_width + photo_spacing
                        
                    except Exception as e:
                        logger.warning(f"Could not add photo {photo_idx + 1} to biography page: {e}")
                        photo_idx += 1
                        current_x += photo_width + photo_spacing
                
                current_y += photo_height + photo_spacing
            
            # Update Y position for text below photos
            text_start_y = current_y + 10
        else:
            text_start_y = photos_start_y + 20
        
        # Body text: Story with generous margins (book-like layout) - 16pt font
        text_margin = 25
        self._set_font(pdf, "", 16)  # Changed to 16pt as requested
        pdf.set_xy(text_margin, text_start_y)
        
        # Calculate available width for text
        text_width = self.A4_WIDTH_MM - (2 * text_margin)
        
        # Multi-cell with justified text for book-like appearance
        pdf.multi_cell(
            text_width, 
            9,  # Increased line height for 16pt font
            clean_pet_story, 
            align="J"  # Justified text
        )
        
        # ============================================
        # PAGES 3+: COLORING PAGES (Páginas de Colorir) - One page per art
        # ============================================
        for idx, art_path in enumerate(generated_art_paths, 1):
            pdf.add_page()
            
            # Get story part for this page (if available)
            story_part = ""
            if story_parts and idx - 1 < len(story_parts):
                story_part = story_parts[idx - 1]
            
            # Title for this coloring page - Changed to more cute name
            self._set_font(pdf, "B", 18)
            pdf.set_y(15)
            # Use cute names instead of "Desenho #x"
            cute_names = ["Momentos Especiais", "Aventura", "Recordação", "Diversão", "Carinho", "Amizade", "Brincadeira", "Felicidade"]
            cute_name = cute_names[(idx - 1) % len(cute_names)]
            pdf.cell(0, 12, f"{cute_name} #{idx}", ln=1, align="C")
            
            # Add story text at the top if available - 16pt font
            if story_part:
                self._set_font(pdf, "", 16)  # Changed to 16pt
                pdf.set_y(pdf.get_y() + 5)
                # Calculate available width for text
                text_margin = 20
                text_width = self.A4_WIDTH_MM - (2 * text_margin)
                # Add story text with justified alignment
                pdf.set_x(text_margin)
                pdf.multi_cell(
                    text_width,
                    9,  # Increased line height for 16pt font
                    story_part,
                    align="J"  # Justified text
                )
                # Update Y position after text
                story_height = pdf.get_y()
            else:
                story_height = 40
            
            try:
                img = Image.open(art_path)
                if img.mode != "RGB":
                    img = img.convert("RGB")
                
                img_width, img_height = img.size
                aspect_ratio = img_width / img_height
                
                # Calculate dimensions to fill available space
                # Use small margins to ensure full coverage
                bleed_margin = 5
                available_width = self.A4_WIDTH_MM - (2 * bleed_margin)
                # Leave space for title and story text
                available_height = self.A4_HEIGHT_MM - story_height - 10
                
                # Fill page maintaining aspect ratio
                if aspect_ratio > (available_width / available_height):
                    # Image is wider
                    width = available_width
                    height = available_width / aspect_ratio
                    # Center vertically
                    x = bleed_margin
                    y = story_height + 5
                else:
                    # Image is taller
                    height = available_height
                    width = available_height * aspect_ratio
                    # Center horizontally
                    x = (self.A4_WIDTH_MM - width) / 2
                    y = story_height + 5
                
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
        self._set_font(pdf, "B", 18)
        pdf.set_y(15)
        pdf.cell(0, 12, "Adesivos", ln=1, align="C")
        
        # Use sticker_paths if provided, otherwise fallback to generated_art_paths
        sticker_images = sticker_paths if sticker_paths and len(sticker_paths) > 0 else generated_art_paths
        
        # If we have original images, also include them in stickers to have more variety
        all_sticker_images = list(sticker_images)
        if original_image_paths and len(original_image_paths) > 0:
            # Add original images as additional sticker options
            for orig_path in original_image_paths:
                if os.path.exists(orig_path) and orig_path not in all_sticker_images:
                    all_sticker_images.append(orig_path)
        
        # Use all available images for stickers
        if len(all_sticker_images) > 0:
            sticker_images = all_sticker_images
        
        # Grid 3x3 configuration (9 stickers total)
        sticker_size = 50
        spacing = 10
        grid_width = (3 * sticker_size) + (2 * spacing)
        start_x = (self.A4_WIDTH_MM - grid_width) / 2
        start_y = 40
        
        # Fill grid with stickers (use all available, repeat only if needed)
        sticker_index = 0
        for row in range(3):
            for col in range(3):
                # Use all available stickers, cycle only if we have less than 9
                if len(sticker_images) > 0:
                    sticker_path = sticker_images[sticker_index % len(sticker_images)]
                    sticker_index += 1
                else:
                    # Fallback: skip this cell if no stickers available
                    continue
                
                try:
                    img = Image.open(sticker_path)
                    if img.mode != "RGB":
                        img = img.convert("RGB")
                    
                    # Get image dimensions and aspect ratio
                    img_width, img_height = img.size
                    aspect_ratio = img_width / img_height
                    
                    # Calculate dimensions maintaining aspect ratio
                    # Fit within sticker_size x sticker_size square
                    if aspect_ratio > 1:
                        # Image is wider than tall
                        width = sticker_size
                        height = sticker_size / aspect_ratio
                    else:
                        # Image is taller than wide or square
                        height = sticker_size
                        width = sticker_size * aspect_ratio
                    
                    # Center the sticker within its grid cell
                    cell_x = start_x + col * (sticker_size + spacing)
                    cell_y = start_y + row * (sticker_size + spacing)
                    
                    # Center image within cell
                    x = cell_x + (sticker_size - width) / 2
                    y = cell_y + (sticker_size - height) / 2
                    
                    temp_buffer = io.BytesIO()
                    img.save(temp_buffer, format="PNG")
                    temp_buffer.seek(0)
                    
                    # Add image maintaining aspect ratio
                    pdf.image(temp_buffer, x=x, y=y, w=width, h=height)
                except Exception as e:
                    logger.error(f"Error adding sticker {row * 3 + col + 1} from {sticker_path}: {e}")
        
        # Save PDF
        os.makedirs(output_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = os.path.join(output_dir, f"kit_digital_{timestamp}.pdf")
        pdf.output(pdf_filename)
        
        logger.info(f"Digital kit PDF created: {pdf_filename}")
        return pdf_filename

