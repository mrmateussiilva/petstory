"""Gemini Image Generation implementation using the new API."""

import base64
import io
import logging
from typing import Optional

import google.generativeai as genai
from PIL import Image

from app.core.config import settings
from app.interfaces.image_generator import ImageGenerator

logger = logging.getLogger(__name__)


class GeminiGenerator(ImageGenerator):
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

