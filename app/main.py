"""FastAPI application main entry point."""

import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import (
    BackgroundTasks,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    Request,
    UploadFile,
)
from typing import List
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse

from app.core.config import settings
from app.services.email_service import EmailService
from app.services.gemini_service import GeminiGenerator
from app.services.payment_service import PaymentService
from app.services.payment_storage import payment_storage
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
payment_service: PaymentService = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    global gemini_service, email_service, payment_service
    
    # Initialize services on startup
    logger.info("Initializing services...")
    try:
        gemini_service = GeminiGenerator()
        email_service = EmailService()
        # Initialize payment service only if token is configured
        if settings.MERCADOPAGO_ACCESS_TOKEN:
            try:
                payment_service = PaymentService()
                logger.info("Payment service initialized successfully")
            except Exception as e:
                logger.warning(f"Payment service not available: {e}")
                payment_service = None
        else:
            logger.warning("MERCADOPAGO_ACCESS_TOKEN not set - payment features disabled")
            payment_service = None
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


@app.post("/api/payment/create")
async def create_payment(
    email: str = Form(...),
    pet_name: str = Form(...),
):
    """Create a Mercado Pago payment preference.
    
    Args:
        email: Customer email
        pet_name: Pet name
        
    Returns:
        JSON response with checkout URL
    """
    if not payment_service:
        raise HTTPException(status_code=503, detail="Payment service not configured")
    
    # Validate email
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Email inválido")
    
    # Validate pet name
    if not pet_name or not pet_name.strip():
        raise HTTPException(status_code=400, detail="Nome do pet é obrigatório")
    
    try:
        base_url = settings.API_BASE_URL.rstrip("/")
        success_url = f"{base_url}/api/payment/success?email={email}&pet_name={pet_name}"
        failure_url = f"{base_url}/api/payment/failure"
        pending_url = f"{base_url}/api/payment/pending"
        
        preference = payment_service.create_payment_preference(
            email=email.strip(),
            pet_name=pet_name.strip(),
            success_url=success_url,
            failure_url=failure_url,
            pending_url=pending_url,
        )
        
        # Use sandbox URL if available (for testing), otherwise use init_point
        checkout_url = preference.get("sandbox_init_point") or preference.get("init_point")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "checkout_url": checkout_url,
                "preference_id": preference.get("id"),
            },
        )
    except Exception as e:
        logger.error(f"Error creating payment: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao criar pagamento: {str(e)}")


@app.post("/api/payment/webhook")
async def payment_webhook(request: Request):
    """Handle Mercado Pago webhook notifications.
    
    This endpoint receives notifications when payment status changes.
    """
    try:
        data = await request.json()
        logger.info(f"Received webhook: {data}")
        
        # Extract payment information
        if "data" in data and "id" in data["data"]:
            payment_id = data["data"]["id"]
            
            # Get payment info from Mercado Pago
            if payment_service:
                payment_info = payment_service.get_payment_info(payment_id)
                if payment_info:
                    status = payment_info.get("status")
                    email = payment_info.get("payer", {}).get("email", "")
                    external_reference = payment_info.get("external_reference", "")
                    
                    # Extract pet name from external_reference if possible
                    pet_name = None
                    if external_reference:
                        parts = external_reference.split("_")
                        if len(parts) >= 2:
                            pet_name = parts[1] if len(parts) > 1 else None
                    
                    # Save payment status
                    payment_storage.save_payment(
                        payment_id=payment_id,
                        status=status,
                        email=email,
                        pet_name=pet_name,
                        external_reference=external_reference,
                    )
                    
                    logger.info(f"Payment {payment_id} status updated to {status} for {email}")
        
        return JSONResponse(status_code=200, content={"status": "ok"})
        
    except Exception as e:
        logger.error(f"Error processing webhook: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"status": "error", "message": str(e)})


@app.get("/api/payment/success")
async def payment_success(
    email: str = Query(...),
    pet_name: str = Query(...),
    payment_id: str = Query(None),
    status: str = Query(None),
):
    """Handle successful payment redirect.
    
    Redirects user to upload page or returns success message.
    """
    # If payment_id is provided, verify it
    if payment_id and payment_service:
        payment_info = payment_service.get_payment_info(payment_id)
        if payment_info:
            status = payment_info.get("status")
            # Save payment status
            payment_storage.save_payment(
                payment_id=payment_id,
                status=status,
                email=email,
                pet_name=pet_name,
            )
    
    # Return success page (frontend should redirect to upload form)
    return JSONResponse(
        status_code=200,
        content={
            "status": "success",
            "message": "Pagamento aprovado! Agora você pode enviar as fotos do seu pet.",
            "email": email,
            "pet_name": pet_name,
            "upload_url": f"/api/upload",
        },
    )


@app.get("/api/payment/failure")
async def payment_failure():
    """Handle failed payment redirect."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "failure",
            "message": "Pagamento não foi aprovado. Tente novamente.",
        },
    )


@app.get("/api/payment/pending")
async def payment_pending():
    """Handle pending payment redirect."""
    return JSONResponse(
        status_code=200,
        content={
            "status": "pending",
            "message": "Pagamento está sendo processado. Você receberá um e-mail quando for aprovado.",
        },
    )


@app.post("/api/upload")
async def upload_pet_story(
    background_tasks: BackgroundTasks,
    nome_pet: str = Form(...),
    pet_date: str = Form(...),
    pet_story: str = Form(...),
    email: str = Form(...),
    fotos: List[UploadFile] = File(...),
    payment_id: str = Form(None),  # Optional payment ID for verification
):
    """Process pet story submission with multiple photos.
    
    Args:
        background_tasks: FastAPI background tasks
        nome_pet: Pet's name
        pet_date: Pet's date/birthday
        pet_story: Pet's story/biography
        email: Recipient email address
        fotos: List of uploaded pet photo files (1-10 photos)
        payment_id: Optional payment ID to verify payment
        
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
    
    # Verify payment if payment service is enabled
    if payment_service:
        payment_verified = False
        
        # If payment_id is provided, verify it
        if payment_id:
            if payment_service.is_payment_approved(payment_id):
                payment_verified = True
                logger.info(f"Payment {payment_id} verified for {email}")
        else:
            # Check if user has any approved payment for this pet
            if payment_storage.can_upload(email, nome_pet):
                payment_verified = True
                logger.info(f"Payment verified from storage for {email} - {nome_pet}")
        
        if not payment_verified:
            raise HTTPException(
                status_code=402,
                detail="Pagamento não verificado. Por favor, complete o pagamento primeiro.",
            )
    
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
        
        # Read photos into memory (don't save to disk yet - let background task do it)
        # This allows the API to return immediately
        photo_data_list = []
        
        for idx, foto in enumerate(fotos, 1):
            # Validate content type
            if foto.content_type not in allowed_content_types:
                raise HTTPException(
                    status_code=400,
                    detail=f"Tipo de arquivo inválido: {foto.content_type} (arquivo: {foto.filename}). "
                    f"Tipos permitidos: {', '.join(allowed_content_types)}",
                )
            
            # Read photo into memory
            photo_bytes = await foto.read()
            if len(photo_bytes) == 0:
                raise HTTPException(status_code=400, detail=f"Arquivo da foto {idx} está vazio")
            
            # Validate image size (max 10MB)
            if len(photo_bytes) > 10 * 1024 * 1024:
                raise HTTPException(status_code=400, detail=f"Foto {idx} ({foto.filename}) excede o limite de 10MB")
            
            # Store photo data (will be saved by background task)
            photo_filename = f"foto_{idx}_{timestamp}{Path(foto.filename).suffix}"
            photo_data_list.append({
                "bytes": photo_bytes,
                "filename": photo_filename,
                "original_filename": foto.filename,
            })
            
            logger.info(f"Received photo {idx}/{len(fotos)}: {foto.filename} ({len(photo_bytes)} bytes) - queued for background processing")
        
        # Add background task with photo data (not paths)
        # The background task will save photos to disk and process them
        background_tasks.add_task(
            process_pet_story,
            nome_pet=nome_pet.strip(),
            pet_date=pet_date.strip(),
            pet_story=pet_story.strip(),
            email=email.strip(),
            order_temp_dir=order_temp_dir,
            photo_data_list=photo_data_list,
            timestamp=timestamp,
        )
        
        logger.info(f"Background task queued for {nome_pet} ({email}) with {len(photo_data_list)} photos")
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": f"História de {nome_pet} está sendo processada! Você receberá um e-mail em {email} quando estiver pronta.",
                "nome_pet": nome_pet,
                "email": email,
                "fotos_count": len(photo_data_list),
            },
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing upload: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Erro ao processar upload: {str(e)}")

