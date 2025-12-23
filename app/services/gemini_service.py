"""Gemini Image Generation implementation using the new API."""

import base64
import io
import logging
import os
from datetime import datetime
from typing import Optional

import google.generativeai as genai
from PIL import Image

from app.core.config import settings

logger = logging.getLogger(__name__)

# Export prompts for use in other modules
__all__ = ["BOBBIE_GOODS_PROMPT", "STICKER_PROMPT", "GeminiGenerator"]

# System Prompt para estilo Bobbie Goods
# BOBBIE_GOODS_PROMPT = (
#     "Create a vector-style coloring book page of this pet, reimagined as a 'Bobbie Goods' character. "
#     "Do NOT trace the photo realistically. Instead, caricature the pet to look extra chubby and soft. "
#     "MANDATORY STYLE RULES: "
#     "1. BODY SHAPE: Make the pet look round, squishy, and potato-shaped. Shorten the legs to be cute and stubby. "
#     "2. FACE: Ignore realistic eyes. Use widely spaced, small black dots for eyes (kawaii style). Small, simple nose. "
#     "3. LINE WORK: Use extremely thick, mono-weight, bold black lines (like a thick Sharpie marker). "
#     "4. PAWS: Simplify paws into rounded 'nubs' or simple shapes. No realistic claws or toes. "
#     "5. DECORATION: Add small floating sparkles, stars, or hearts around the pet to fill empty space. "
#     "6. TECH SPECS: Pure white background. STRICTLY NO SHADING, NO GRAYSCALE, NO TEXTURE."
# )

BOBBIE_GOODS_PROMPT = (
    "Convert this pet photo into a clean, realistic line art illustration suitable for a coloring book.\n\n"

    "CORE GOAL:\n"
    "- Preserve the pet's REAL appearance, proportions, and expression.\n"
    "- The pet must remain clearly recognizable to its owner.\n\n"

    "STYLE RULES:\n"
    "- Create a black-and-white outline drawing (line art).\n"
    "- Follow the natural contours of the pet from the photo.\n"
    "- Use smooth, confident, continuous black lines.\n\n"

    "LINE WORK:\n"
    "- Medium-to-thick clean outlines.\n"
    "- No sketchy lines.\n"
    "- No cross-hatching.\n"
    "- No shading, no gradients, no gray tones.\n\n"

    "DETAIL CONTROL:\n"
    "- Simplify fur into clean contour shapes.\n"
    "- Keep facial features accurate but simplified.\n"
    "- Eyes, nose, and mouth should reflect the real pet.\n\n"

    "COLORING BOOK REQUIREMENTS:\n"
    "- Pure white background.\n"
    "- Black lines only.\n"
    "- Large enclosed areas suitable for coloring.\n\n"

    "COMPOSITION:\n"
    "- Center the pet.\n"
    "- Remove background elements completely.\n\n"

    "FINAL OUTPUT:\n"
    "- Clean, printable coloring book page.\n"
    "- No artistic style exaggeration.\n"
)

# Prompt específico para adesivos (stickers)
STICKER_PROMPT = (
    "Convert this pet photo into a sticker-style illustration optimized for small format printing.\n\n"
    
    "CORE GOAL:\n"
    "- Create a simplified, cute version of the pet suitable for stickers.\n"
    "- The pet should be recognizable but stylized for sticker use.\n\n"
    
    "STICKER-SPECIFIC REQUIREMENTS:\n"
    "- Design should work well at small sizes (2-3cm).\n"
    "- Use bold, clear outlines that remain visible when small.\n"
    "- Simplify details while keeping the pet's character.\n"
    "- Make the pet look friendly and appealing.\n\n"
    
    "STYLE RULES:\n"
    "- Black-and-white line art (no colors).\n"
    "- Thicker outlines than regular coloring pages (for visibility at small size).\n"
    "- Simplified features: larger eyes, simpler shapes.\n"
    "- Cute, kawaii-inspired style works well for stickers.\n\n"
    
    "COMPOSITION:\n"
    "- Center the pet in the frame.\n"
    "- Leave some white space around edges (for sticker border).\n"
    "- Pet should fill most of the frame but not touch edges.\n\n"
    
    "TECHNICAL:\n"
    "- Pure white background.\n"
    "- Black lines only, no shading.\n"
    "- High contrast for clear printing at small sizes.\n"
    "- Clean, vector-like appearance.\n\n"
    
    "FINAL OUTPUT:\n"
    "- Sticker-ready illustration that looks great when printed small.\n"
    "- Cute, recognizable pet character suitable for adhesive stickers.\n"
)


class GeminiGenerator:
    """Gemini Image Generation implementation of ImageGenerator.
    
    Uses the new Gemini image generation API (Nano Banana / Nano Banana Pro).
    See: https://ai.google.dev/gemini-api/docs/image-generation
    """

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        """Initialize Gemini client.
        
        Args:
            api_key: Gemini API key. If None, uses settings.GEMINI_API_KEY
            model_name: Model name. If None, uses settings.GEMINI_IMAGE_MODEL
        """
        self.api_key = api_key or settings.GEMINI_API_KEY
        genai.configure(api_key=self.api_key)
        self.model_name = model_name or settings.GEMINI_IMAGE_MODEL
        self.model = genai.GenerativeModel(self.model_name)

    async def generate(self, image_bytes: bytes, prompt: str) -> bytes:
        """Generate a coloring book style image from input photo.
        
        Args:
            image_bytes: Input image as bytes
            prompt: Text prompt for transformation
            
        Returns:
            Generated image as PNG bytes
            
        Raises:
            Exception: If generation fails
        """
        try:
            # Load image from bytes
            input_image = Image.open(io.BytesIO(image_bytes))
            
            # Convert to RGB if necessary (remove alpha channel)
            if input_image.mode != "RGB":
                input_image = input_image.convert("RGB")
            
            # Generate image using Gemini
            # The API supports image-to-image transformation
            response = self.model.generate_content(
                [prompt, input_image],
                generation_config={
                    "temperature": 0.4,
                },
            )
            
            # Extract generated image from response
            if not response.candidates or not response.candidates[0].content.parts:
                raise ValueError("No image generated in response")
            
            # The response contains parts, and one of them should be the generated image
            # According to documentation: https://ai.google.dev/gemini-api/docs/image-generation
            generated_image = None
            for part in response.candidates[0].content.parts:
                # Method 1: Check if part has text (shouldn't happen for image generation, but log it)
                if hasattr(part, 'text') and part.text:
                    logger.debug(f"Response part contains text: {part.text[:100]}")
                
                # Method 2: Check if part has inline_data
                if hasattr(part, 'inline_data') and part.inline_data:
                    try:
                        inline_data = part.inline_data
                        mime_type = getattr(inline_data, 'mime_type', 'N/A')
                        logger.info(f"Found inline_data: mime_type={mime_type}")
                        
                        # Try to get data - it might be bytes or base64 string
                        data = inline_data.data
                        logger.info(f"Data type: {type(data)}, length: {len(data) if hasattr(data, '__len__') else 'N/A'}")
                        
                        # If data is a string, try to decode as base64
                        if isinstance(data, str):
                            logger.debug("Data is string, decoding as base64")
                            image_data = base64.b64decode(data)
                        # If data is bytes, use directly
                        elif isinstance(data, bytes):
                            logger.debug("Data is bytes, using directly")
                            image_data = data
                        else:
                            # Try to convert to bytes
                            logger.debug(f"Converting data to bytes from type {type(data)}")
                            image_data = bytes(data)
                        
                        logger.info(f"Image data length: {len(image_data)} bytes")
                        
                        # Try to open as image
                        generated_image = Image.open(io.BytesIO(image_data))
                        logger.info("Successfully extracted image from inline_data")
                        break
                    except Exception as e:
                        logger.error(f"Failed to decode inline_data: {e}", exc_info=True)
                        # Try to save raw data for inspection
                        try:
                            if 'image_data' in locals():
                                with open('/tmp/gemini_raw_data.bin', 'wb') as f:
                                    f.write(image_data)
                                logger.error(f"Saved raw data to /tmp/gemini_raw_data.bin for inspection")
                        except:
                            pass
                        continue
                
                # Method 3: Check if part has file_data
                if hasattr(part, 'file_data') and part.file_data:
                    try:
                        file_data = part.file_data
                        logger.debug(f"Found file_data: mime_type={getattr(file_data, 'mime_type', 'N/A')}")
                        # Similar processing as inline_data
                        data = file_data.data
                        if isinstance(data, str):
                            image_data = base64.b64decode(data)
                        elif isinstance(data, bytes):
                            image_data = data
                        else:
                            image_data = bytes(data)
                        generated_image = Image.open(io.BytesIO(image_data))
                        logger.info("Successfully extracted image from file_data")
                        break
                    except Exception as e:
                        logger.warning(f"Failed to decode file_data: {e}")
                        continue
                
                # Method 4: Check if part has as_image method (PIL Image)
                if hasattr(part, 'as_image'):
                    try:
                        generated_image = part.as_image()
                        logger.info("Extracted image using as_image() method")
                        break
                    except Exception as e:
                        logger.debug(f"as_image() method failed: {e}")
                        continue
            
            if generated_image is None:
                # Log detailed information for debugging
                logger.error("No image data found. Response details:")
                logger.error(f"Number of candidates: {len(response.candidates)}")
                for i, part in enumerate(response.candidates[0].content.parts):
                    logger.error(f"Part {i}:")
                    logger.error(f"  Type: {type(part)}")
                    logger.error(f"  Has text: {hasattr(part, 'text') and bool(part.text)}")
                    logger.error(f"  Has inline_data: {hasattr(part, 'inline_data') and bool(part.inline_data)}")
                    if hasattr(part, 'inline_data') and part.inline_data:
                        logger.error(f"  inline_data type: {type(part.inline_data)}")
                        logger.error(f"  inline_data attributes: {dir(part.inline_data)}")
                    logger.error(f"  Has file_data: {hasattr(part, 'file_data') and bool(part.file_data)}")
                raise ValueError("No image data found in response parts")
            
            # Convert to RGB and save as PNG bytes
            if generated_image.mode != "RGB":
                generated_image = generated_image.convert("RGB")
            
            output_buffer = io.BytesIO()
            generated_image.save(output_buffer, format="PNG")
            output_bytes = output_buffer.getvalue()
            
            logger.info(f"Successfully generated image ({len(output_bytes)} bytes)")
            return output_bytes
            
        except Exception as e:
            logger.error(f"Error generating image with Gemini: {str(e)}", exc_info=True)
            raise
    
    def generate_art(self, photo_path: str, output_dir: Optional[str] = None) -> str:
        """Generate art from a pet photo file and save to disk.
        
        Args:
            photo_path: Path to the input pet photo
            output_dir: Directory to save the generated art. If None, saves in same dir as photo.
            
        Returns:
            Path to the generated art image file
            
        Raises:
            Exception: If generation fails
        """
        try:
            # Read photo from file
            with open(photo_path, "rb") as f:
                photo_bytes = f.read()
            
            logger.info(f"Generating art from photo: {photo_path}")
            
            # Generate art using the async method (sync wrapper)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            art_bytes = loop.run_until_complete(
                self.generate(photo_bytes, BOBBIE_GOODS_PROMPT)
            )
            
            # Determine output path
            if output_dir is None:
                output_dir = os.path.dirname(photo_path)
            
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"arte_{timestamp}.png"
            output_path = os.path.join(output_dir, output_filename)
            
            # Save generated art
            with open(output_path, "wb") as f:
                f.write(art_bytes)
            
            logger.info(f"Art saved to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating art from {photo_path}: {str(e)}", exc_info=True)
            raise
    
    def generate_sticker(self, photo_path: str, output_dir: Optional[str] = None) -> str:
        """Generate sticker-style art from a pet photo file and save to disk.
        
        Args:
            photo_path: Path to the input pet photo
            output_dir: Directory to save the generated sticker. If None, saves in same dir as photo.
            
        Returns:
            Path to the generated sticker image file
            
        Raises:
            Exception: If generation fails
        """
        try:
            # Read photo from file
            with open(photo_path, "rb") as f:
                photo_bytes = f.read()
            
            logger.info(f"Generating sticker from photo: {photo_path}")
            
            # Generate sticker using the async method (sync wrapper)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            sticker_bytes = loop.run_until_complete(
                self.generate(photo_bytes, STICKER_PROMPT)
            )
            
            # Determine output path
            if output_dir is None:
                output_dir = os.path.dirname(photo_path)
            
            os.makedirs(output_dir, exist_ok=True)
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_filename = f"sticker_{timestamp}.png"
            output_path = os.path.join(output_dir, output_filename)
            
            # Save generated sticker
            with open(output_path, "wb") as f:
                f.write(sticker_bytes)
            
            logger.info(f"Sticker saved to: {output_path}")
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating sticker from {photo_path}: {str(e)}", exc_info=True)
            raise

