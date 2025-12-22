"""Background worker for processing pet stories into digital kits."""

import logging
import os
from datetime import datetime
from pathlib import Path

from app.core.config import settings
from app.services.email_service import EmailService
from app.services.gemini_service import GeminiGenerator
from app.services.pdf_service import PDFService
from app.services.web_generator import WebGenerator
from app.utils.slug import get_user_backup_dir

logger = logging.getLogger(__name__)



def process_pet_story(
    nome_pet: str,
    pet_date: str,
    pet_story: str,
    email: str,
    photo_path: str,
) -> dict:
    """Orchestrate the complete pet story processing workflow.
    
    Args:
        nome_pet: Pet's name
        pet_date: Pet's date/birthday
        pet_story: Pet's story/biography
        email: User email address
        photo_path: Path to the uploaded pet photo
        
    Returns:
        Dictionary with processing results
    """
    print(f"🚀 Iniciando processamento da história de {nome_pet}...")
    
    try:
        # Initialize services
        gemini_service = GeminiGenerator()
        pdf_service = PDFService()
        web_generator = WebGenerator()
        email_service = EmailService()
        
        # Get user temp directory
        user_temp_dir = os.path.dirname(photo_path)
        
        # Step 1: Generate art with Gemini
        print(f"📸 Passo 1/4: Gerando arte com IA para {nome_pet}...")
        try:
            art_path = gemini_service.generate_art(photo_path, output_dir=user_temp_dir)
            print(f"✅ Arte gerada com sucesso: {art_path}")
        except Exception as e:
            print(f"❌ Erro ao gerar arte: {str(e)}")
            raise
        
        # Step 2: Create PDF with create_digital_kit
        print(f"📄 Passo 2/4: Criando PDF do kit digital...")
        try:
            pdf_path = pdf_service.create_digital_kit(
                pet_name=nome_pet,
                pet_date=pet_date,
                pet_story=pet_story,
                art_image_path=art_path,
                output_dir=user_temp_dir,
                original_image_path=photo_path,
            )
            print(f"✅ PDF criado com sucesso: {pdf_path}")
        except Exception as e:
            print(f"❌ Erro ao criar PDF: {str(e)}")
            raise
        
        # Step 3: Generate web page HTML
        print(f"🌐 Passo 3/4: Gerando página web de homenagem...")
        try:
            html_content = web_generator.generate_tribute_page(
                pet_name=nome_pet,
                pet_date=pet_date,
                pet_story=pet_story,
                art_image_path=art_path,
            )
            
            # Save HTML file
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            html_path = os.path.join(user_temp_dir, f"homenagem_{timestamp}.html")
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            print(f"✅ Página web gerada: {html_path}")
        except Exception as e:
            print(f"❌ Erro ao gerar página web: {str(e)}")
            raise
        
        # Step 4: Send email with PDF and HTML
        print(f"📧 Passo 4/4: Enviando e-mail para {email}...")
        try:
            # Read PDF bytes
            with open(pdf_path, "rb") as f:
                pdf_bytes = f.read()
            
            # Send email with attachments
            import asyncio
            email_sent = asyncio.run(
                email_service.send_pet_story_email(
                    to_email=email,
                    pet_name=nome_pet,
                    pdf_bytes=pdf_bytes,
                    html_content=html_content,
                    pdf_filename=os.path.basename(pdf_path),
                )
            )
            
            if email_sent:
                print(f"✅ E-mail enviado com sucesso!")
            else:
                print(f"⚠️ Falha ao enviar e-mail")
        except Exception as e:
            print(f"❌ Erro ao enviar e-mail: {str(e)}")
            raise
        
        print(f"🎉 Processamento completo para {nome_pet}!")
        return {
            "success": True,
            "nome_pet": nome_pet,
            "email": email,
            "art_path": art_path,
            "pdf_path": pdf_path,
            "html_path": html_path,
            "email_sent": email_sent,
        }
        
    except Exception as e:
        error_msg = f"Erro no processamento: {str(e)}"
        print(f"❌ {error_msg}")
        logger.error(error_msg, exc_info=True)
        return {
            "success": False,
            "error": error_msg,
            "nome_pet": nome_pet,
            "email": email,
        }

