"""Email service for sending PDFs via SMTP (native Python)."""

import logging
import os
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

from app.core.config import settings

# Configure email-specific logger that writes to email.log
email_logger = logging.getLogger("email_service")
email_logger.setLevel(logging.DEBUG)

# Create logs directory if it doesn't exist
logs_dir = Path("logs")
logs_dir.mkdir(exist_ok=True)

# File handler for email.log
email_log_file = logs_dir / "email.log"
file_handler = logging.FileHandler(email_log_file, encoding="utf-8")
file_handler.setLevel(logging.DEBUG)

# Format for file logging
file_formatter = logging.Formatter(
    "%(asctime)s - %(levelname)s - %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(file_formatter)

# Add handler to logger (avoid duplicates)
if not email_logger.handlers:
    email_logger.addHandler(file_handler)

# Also use standard logger for console output
logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails via SMTP."""

    def __init__(
        self,
        smtp_server: Optional[str] = None,
        smtp_port: Optional[int] = None,
        smtp_user: Optional[str] = None,
        smtp_password: Optional[str] = None,
    ):
        """Initialize email service.
        
        Args:
            smtp_server: SMTP server address. If None, uses settings.SMTP_SERVER
            smtp_port: SMTP server port. If None, uses settings.SMTP_PORT
            smtp_user: SMTP username. If None, uses settings.SMTP_USER
            smtp_password: SMTP password. If None, uses settings.SMTP_PASSWORD
        """
        self.smtp_server = smtp_server or settings.SMTP_SERVER
        self.smtp_port = smtp_port or settings.SMTP_PORT
        self.smtp_user = smtp_user or settings.SMTP_USER
        self.smtp_password = smtp_password or settings.SMTP_PASSWORD
        self.from_email = settings.EMAIL_FROM
        self.from_name = settings.EMAIL_FROM_NAME
        
        # Check if SMTP is configured
        if self.smtp_user and self.smtp_password:
            self.enabled = True
            msg = (
                f"Email service initialized with SMTP server: {self.smtp_server}:{self.smtp_port} | "
                f"From: {self.from_email} | User: {self.smtp_user}"
            )
            logger.info(msg)
            email_logger.info(msg)
        else:
            self.enabled = False
            msg = (
                "SMTP credentials not provided, email service will log only. "
                f"SMTP_USER: {'Set' if self.smtp_user else 'Not set'}, "
                f"SMTP_PASSWORD: {'Set' if self.smtp_password else 'Not set'}"
            )
            logger.warning(msg)
            email_logger.warning(msg)

    async def send_pdf(
        self, to_email: str, subject: str, pdf_bytes: bytes, pdf_filename: str = "livro_pet.pdf"
    ) -> bool:
        """Send PDF via email using SMTP.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            pdf_bytes: PDF file as bytes
            pdf_filename: Name for the PDF attachment
            
        Returns:
            True if sent successfully, False otherwise
        """
        try:
            if not self.enabled:
                # Simulate sending (log only)
                logger.info(
                    f"[SIMULATED] Would send email to {to_email} "
                    f"with PDF ({len(pdf_bytes)} bytes) as {pdf_filename}"
                )
                logger.info(f"[SIMULATED] Subject: {subject}")
                return True
            
            # Create multipart message
            msg = MIMEMultipart("mixed")
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email
            msg["Subject"] = subject
            
            # Create HTML body
            body_html = """
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px;">
                    <h2>Seu livro de colorir PetStory está pronto! 🎨</h2>
                    <p>Olá!</p>
                    <p>Seu livro de colorir personalizado com seus pets foi gerado com sucesso.</p>
                    <p>Você pode encontrar o PDF anexado neste email.</p>
                    <p>Divirta-se colorindo! 🐾</p>
                    <hr>
                    <p style="color: #666; font-size: 12px;">
                        PetStory - Transformando memórias em arte
                    </p>
                </body>
            </html>
            """
            
            # Attach HTML body
            msg.attach(MIMEText(body_html, "html", "utf-8"))
            
            # Attach PDF
            pdf_attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
            pdf_attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=pdf_filename,
            )
            msg.attach(pdf_attachment)
            
            # Connect to SMTP server and send
            try:
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                    # Enable debug (optional, can be removed in production)
                    if settings.DEBUG:
                        server.set_debuglevel(1)
                    
                    # Start TLS encryption
                    server.starttls()
                    
                    # Login
                    server.login(self.smtp_user, self.smtp_password)
                    
                    # Send email
                    server.send_message(msg)
                    
                logger.info(f"Email sent successfully to {to_email}")
                return True
                
            except smtplib.SMTPAuthenticationError as e:
                logger.error(f"SMTP authentication failed: {str(e)}")
                return False
            except smtplib.SMTPException as e:
                logger.error(f"SMTP error occurred: {str(e)}")
                return False
            except Exception as e:
                logger.error(f"Unexpected error sending email: {str(e)}", exc_info=True)
                return False
            
        except Exception as e:
            logger.error(f"Error sending email to {to_email}: {str(e)}", exc_info=True)
            return False
    
    async def send_pet_story_email(
        self,
        to_email: str,
        pet_name: str,
        pdf_bytes: bytes,
        html_content: str,
        pdf_filename: str = "kit_digital.pdf",
    ) -> bool:
        """Send pet story email with PDF and HTML attachments.
        
        Args:
            to_email: Recipient email address
            pet_name: Pet's name (for subject)
            pdf_bytes: PDF file as bytes
            html_content: HTML content for the tribute page
            pdf_filename: Name for the PDF attachment
            
        Returns:
            True if sent successfully, False otherwise
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        email_logger.info("=" * 80)
        email_logger.info(f"Attempting to send email to {to_email} for pet {pet_name}")
        email_logger.info(f"Timestamp: {timestamp}")
        
        try:
            if not self.enabled:
                # Simulate sending (log only)
                msg = (
                    f"[SIMULATED] Would send pet story email to {to_email} "
                    f"for {pet_name} with PDF ({len(pdf_bytes)} bytes) and HTML"
                )
                logger.warning(msg)
                email_logger.warning(msg)
                email_logger.warning("Email service is NOT enabled - check SMTP credentials in .env")
                return False  # Return False instead of True to indicate failure
            
            # Validate email address
            if not to_email or "@" not in to_email:
                error_msg = f"Invalid email address: {to_email}"
                logger.error(error_msg)
                email_logger.error(error_msg)
                return False
            
            email_logger.info(f"SMTP Configuration: Server={self.smtp_server}, Port={self.smtp_port}")
            email_logger.info(f"From: {self.from_name} <{self.from_email}>")
            email_logger.info(f"To: {to_email}")
            email_logger.info(f"PDF size: {len(pdf_bytes)} bytes")
            email_logger.info(f"HTML content size: {len(html_content)} bytes")
            
            # Create multipart message
            msg = MIMEMultipart("mixed")
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = to_email
            msg["Subject"] = f"O Kit Digital de {pet_name} está pronto! 🎨🐾"
            
            email_logger.debug(f"Email subject: {msg['Subject']}")
            
            # Create HTML body
            body_html = f"""
            <html>
                <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #f5f5f5;">
                    <div style="max-width: 600px; margin: 0 auto; background-color: white; padding: 30px; border-radius: 10px;">
                        <h2 style="color: #7c3aed;">🎉 O Kit Digital do {pet_name} está pronto!</h2>
                        <p>Olá!</p>
                        <p>Ficamos felizes em compartilhar que o kit digital personalizado do <strong>{pet_name}</strong> foi criado com sucesso!</p>
                        <p>Você encontrará anexos:</p>
                        <ul>
                            <li><strong>PDF do Kit Digital</strong> - com capa, biografia, página para colorir e adesivos</li>
                            <li><strong>Página Web de Homenagem</strong> - uma página HTML linda que você pode compartilhar ou guardar</li>
                        </ul>
                        <p>Divirta-se colorindo e compartilhando as memórias do {pet_name}! 🐾</p>
                        <hr style="margin: 30px 0; border: none; border-top: 1px solid #e0e0e0;">
                        <p style="color: #666; font-size: 12px; text-align: center;">
                            PetStory - Transformando memórias em arte<br>
                            Criado com ❤️ para você
                        </p>
                    </div>
                </body>
            </html>
            """
            
            # Attach HTML body
            msg.attach(MIMEText(body_html, "html", "utf-8"))
            email_logger.debug("HTML body attached")
            
            # Attach PDF
            pdf_attachment = MIMEApplication(pdf_bytes, _subtype="pdf")
            pdf_attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=pdf_filename,
            )
            msg.attach(pdf_attachment)
            email_logger.debug(f"PDF attachment added: {pdf_filename}")
            
            # Attach HTML file
            html_attachment = MIMEText(html_content, "html", "utf-8")
            html_attachment.add_header(
                "Content-Disposition",
                "attachment",
                filename=f"homenagem_{pet_name.replace(' ', '_')}.html",
            )
            msg.attach(html_attachment)
            email_logger.debug("HTML file attachment added")
            
            # Connect to SMTP server and send
            try:
                email_logger.info(f"Connecting to SMTP server {self.smtp_server}:{self.smtp_port}...")
                with smtplib.SMTP(self.smtp_server, self.smtp_port, timeout=30) as server:
                    # Enable debug (optional, can be removed in production)
                    if settings.DEBUG:
                        server.set_debuglevel(1)
                    
                    # Start TLS encryption
                    email_logger.debug("Starting TLS encryption...")
                    server.starttls()
                    email_logger.debug("TLS encryption started")
                    
                    # Login
                    email_logger.debug(f"Attempting to login with user: {self.smtp_user}")
                    server.login(self.smtp_user, self.smtp_password)
                    email_logger.debug("Login successful")
                    
                    # Send email
                    email_logger.info(f"Sending email message to {to_email}...")
                    send_result = server.send_message(msg)
                    email_logger.debug(f"SMTP send_message result: {send_result}")
                    
                    # Check if there were any rejected recipients
                    if send_result:
                        rejected = send_result.get(to_email, [])
                        if rejected:
                            error_msg = f"Email rejected by server. Recipients: {rejected}"
                            email_logger.error(error_msg)
                            logger.error(error_msg)
                            return False
                    
                    email_logger.info(f"✓ Email sent successfully to {to_email}")
                    logger.info(f"Pet story email sent successfully to {to_email}")
                    email_logger.info("=" * 80)
                    return True
                
            except smtplib.SMTPAuthenticationError as e:
                error_msg = f"SMTP authentication failed: {str(e)}"
                email_logger.error(error_msg)
                email_logger.error(f"Check your SMTP_USER and SMTP_PASSWORD in .env file")
                email_logger.error(f"For Gmail, you need to use an App Password, not your regular password")
                logger.error(error_msg)
                email_logger.info("=" * 80)
                return False
            except smtplib.SMTPServerDisconnected as e:
                error_msg = f"SMTP server disconnected: {str(e)}"
                email_logger.error(error_msg)
                email_logger.error(f"Server: {self.smtp_server}:{self.smtp_port}")
                logger.error(error_msg)
                email_logger.info("=" * 80)
                return False
            except smtplib.SMTPRecipientsRefused as e:
                error_msg = f"SMTP recipients refused: {str(e)}"
                email_logger.error(error_msg)
                email_logger.error(f"Recipient {to_email} was refused by the server")
                logger.error(error_msg)
                email_logger.info("=" * 80)
                return False
            except smtplib.SMTPDataError as e:
                error_msg = f"SMTP data error: {str(e)}"
                email_logger.error(error_msg)
                email_logger.error("The server refused the message data")
                logger.error(error_msg)
                email_logger.info("=" * 80)
                return False
            except smtplib.SMTPException as e:
                error_msg = f"SMTP error occurred: {str(e)}"
                email_logger.error(error_msg)
                email_logger.error(f"SMTP Error Code: {e.smtp_code if hasattr(e, 'smtp_code') else 'N/A'}")
                email_logger.error(f"SMTP Error Message: {e.smtp_error if hasattr(e, 'smtp_error') else 'N/A'}")
                logger.error(error_msg)
                email_logger.info("=" * 80)
                return False
            except TimeoutError as e:
                error_msg = f"Timeout connecting to SMTP server: {str(e)}"
                email_logger.error(error_msg)
                email_logger.error(f"Server: {self.smtp_server}:{self.smtp_port}")
                logger.error(error_msg)
                email_logger.info("=" * 80)
                return False
            except Exception as e:
                error_msg = f"Unexpected error sending email: {str(e)}"
                email_logger.error(error_msg, exc_info=True)
                logger.error(error_msg, exc_info=True)
                email_logger.info("=" * 80)
                return False
            
        except Exception as e:
            error_msg = f"Error sending pet story email to {to_email}: {str(e)}"
            email_logger.error(error_msg, exc_info=True)
            logger.error(error_msg, exc_info=True)
            email_logger.info("=" * 80)
            return False

