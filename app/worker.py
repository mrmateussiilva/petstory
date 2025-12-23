"""Background worker for processing pet stories into digital kits."""

import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import List

from app.core.config import settings
from app.services.email_service import EmailService
from app.services.gemini_service import GeminiGenerator
from app.services.pdf_service import PDFService
from app.services.web_generator import WebGenerator

logger = logging.getLogger(__name__)



def process_pet_story(
    nome_pet: str,
    pet_date: str,
    pet_story: str,
    email: str,
    photo_paths: List[str],
) -> dict:
    """Orchestrate the complete pet story processing workflow.
    
    Args:
        nome_pet: Pet's name
        pet_date: Pet's date/birthday
        pet_story: Pet's story/biography
        email: User email address
        photo_paths: List of paths to uploaded pet photos
        
    Returns:
        Dictionary with processing results
    """
    print(f"🚀 Iniciando processamento da história de {nome_pet} com {len(photo_paths)} foto(s)...")
    
    try:
        # Initialize services
        gemini_service = GeminiGenerator()
        pdf_service = PDFService()
        web_generator = WebGenerator()
        email_service = EmailService()
        
        # Get user temp directory (all photos are in the same directory)
        user_temp_dir = os.path.dirname(photo_paths[0])
        
        # Step 1: Generate art with Gemini for each photo
        print(f"📸 Passo 1/4: Gerando arte com IA para {len(photo_paths)} foto(s)...")
        generated_arts = []
        
        for idx, photo_path in enumerate(photo_paths, 1):
            try:
                print(f"  🎨 Processando foto {idx}/{len(photo_paths)}: {os.path.basename(photo_path)}")
                art_path = gemini_service.generate_art(photo_path, output_dir=user_temp_dir)
                generated_arts.append(art_path)
                print(f"  ✅ Arte {idx} gerada: {art_path}")
                
                # Sleep between generations to avoid rate limit (except for last one)
                if idx < len(photo_paths):
                    print(f"  ⏳ Aguardando 2 segundos antes da próxima geração...")
                    time.sleep(2)
                    
            except Exception as e:
                print(f"  ❌ Erro ao gerar arte para foto {idx}: {str(e)}")
                logger.error(f"Error generating art for photo {idx}: {e}", exc_info=True)
                # Continue processing other photos
                continue
        
        if not generated_arts:
            raise Exception("Nenhuma arte foi gerada com sucesso. Verifique os logs para mais detalhes.")
        
        print(f"✅ {len(generated_arts)} arte(s) gerada(s) com sucesso!")
        
        # Step 2: Create PDF with create_digital_kit
        print(f"📄 Passo 2/4: Criando PDF do kit digital...")
        try:
            pdf_path = pdf_service.create_digital_kit(
                pet_name=nome_pet,
                pet_date=pet_date,
                pet_story=pet_story,
                original_image_paths=photo_paths,
                generated_art_paths=generated_arts,
                output_dir=user_temp_dir,
            )
            print(f"✅ PDF criado com sucesso: {pdf_path}")
        except Exception as e:
            print(f"❌ Erro ao criar PDF: {str(e)}")
            raise
        
        # Step 3: Generate web page HTML (use first art)
        print(f"🌐 Passo 3/4: Gerando página web de homenagem...")
        try:
            html_content = web_generator.generate_tribute_page(
                pet_name=nome_pet,
                pet_date=pet_date,
                pet_story=pet_story,
                art_image_path=generated_arts[0],  # Use first art for web page
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
        email_sent = False
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
                logger.info(f"Email sent successfully to {email} for {nome_pet}")
            else:
                print(f"⚠️ Falha ao enviar e-mail - verifique logs/email.log para detalhes")
                logger.warning(f"Failed to send email to {email} for {nome_pet} - check logs/email.log")
        except Exception as e:
            error_msg = f"Erro ao enviar e-mail: {str(e)}"
            print(f"❌ {error_msg}")
            logger.error(error_msg, exc_info=True)
            # Não levanta exceção - continua e retorna resultado indicando falha no email
        
        print(f"🎉 Processamento completo para {nome_pet}!")
        return {
            "success": True,
            "nome_pet": nome_pet,
            "email": email,
            "photos_count": len(photo_paths),
            "arts_generated": len(generated_arts),
            "art_paths": generated_arts,
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

