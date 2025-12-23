"""FastAPI application main entry point."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.services.email_service import EmailService
from app.services.gemini_service import GeminiGenerator
from app.worker import process_pet_story

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.DEBUG else logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Global instances (initialized in lifespan)
gemini_service: GeminiGenerator = None
email_service: EmailService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global gemini_service, email_service
    
    # Initialize services on startup
    logger.info("Initializing services...")
    try:
        gemini_service = GeminiGenerator()
        email_service = EmailService()
        logger.info("Services initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing services: {e}", exc_info=True)
        raise
    
    # Create temp directory if it doesn't exist
    temp_dir = Path(settings.TEMP_DIR)
    temp_dir.mkdir(parents=True, exist_ok=True)
    logger.info(f"Temp directory ready: {temp_dir.absolute()}")
    
    yield
    
    # Cleanup on shutdown
    logger.info("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    description="API para transformar fotos de pets em desenhos de colorir",
    version="0.1.0",
    lifespan=lifespan,
)

# Configure CORS for frontend (GitHub Pages)
# In debug mode, allow all origins for easier development
cors_origins = ["*"] if settings.DEBUG else settings.cors_origins_list

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": "0.1.0",
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/api/upload")
async def upload_pet_story(
    background_tasks: BackgroundTasks,
    nome_pet: str = Form(...),
    pet_date: str = Form(...),
    pet_story: str = Form(...),
    email: str = Form(...),
    fotos: List[UploadFile] = File(...),
):
    """Process pet story submission with multiple photos.
    
    Args:
        background_tasks: FastAPI background tasks
        nome_pet: Pet's name
        pet_date: Pet's date/birthday
        pet_story: Pet's story/biography
        email: Recipient email address
        fotos: List of uploaded pet photo files (1-10 photos)
        
    Returns:
        JSON response with job status
    """
    # Validate email
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Email inválido")
    
    # Validate required fields
    if not nome_pet or not nome_pet.strip():
        raise HTTPException(status_code=400, detail="Nome do pet é obrigatório")
    
    if not pet_story or not pet_story.strip():
        raise HTTPException(status_code=400, detail="História do pet é obrigatória")
    
    # Validate files
    if not fotos or len(fotos) == 0:
        raise HTTPException(status_code=400, detail="Pelo menos uma foto do pet é obrigatória")
    
    if len(fotos) > 10:
        raise HTTPException(status_code=400, detail="Máximo de 10 fotos permitidas")
    
    allowed_content_types = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
    photo_paths = []
    
    try:
        # Create unique temp directory for this order
        from app.utils.slug import get_unique_order_dir
        from datetime import datetime
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        order_temp_dir = get_unique_order_dir(
            base_dir=settings.TEMP_DIR,
            email=email,
            pet_name=nome_pet,
            timestamp=timestamp
        )
        Path(order_temp_dir).mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Created unique order directory: {order_temp_dir} for {nome_pet} ({email})")
        
        # Process each photo
        for idx, foto in enumerate(fotos, 1):
            # Validate content type
            if foto.content_type not in allowed_content_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tipo de arquivo inválido: {foto.content_type} (arquivo: {foto.filename}). "
                    f"Tipos permitidos: {', '.join(allowed_content_types)}",
                )
            
            # Read photo
            photo_bytes = await foto.read()
            if len(photo_bytes) == 0:
                raise HTTPException(status_code=400, detail=f"Arquivo da foto {idx} está vazio")
            
            # Validate image size (max 10MB)
            if len(photo_bytes) > 10 * 1024 * 1024:
                raise HTTPException(status_code=400, detail=f"Foto {idx} ({foto.filename}) excede o limite de 10MB")
            
            # Save photo temporarily
            photo_filename = f"foto_{idx}_{timestamp}{Path(foto.filename).suffix}"
            photo_path = os.path.join(order_temp_dir, photo_filename)
            
            with open(photo_path, "wb") as f:
                f.write(photo_bytes)
            
            photo_paths.append(photo_path)
            logger.info(f"Received photo {idx}/{len(fotos)}: {foto.filename} ({len(photo_bytes)} bytes) -> {photo_path}")
        
        # Add background task with list of photo paths
        background_tasks.add_task(
            process_pet_story,
            nome_pet=nome_pet.strip(),
            pet_date=pet_date.strip(),
            pet_story=pet_story.strip(),
            email=email.strip(),
            photo_paths=photo_paths,
        )
        
        logger.info(f"Background task queued for {nome_pet} ({email}) with {len(photo_paths)} photos")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"História de {nome_pet} está sendo processada! Você receberá um e-mail em {email} quando estiver pronta.",
                "nome_pet": nome_pet,
                "email": email,
                "fotos_count": len(photo_paths),
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao processar upload: {str(e)}")

