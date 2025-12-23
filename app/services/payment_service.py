"""Payment service for Mercado Pago integration."""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

import mercadopago

from app.core.config import settings

logger = logging.getLogger(__name__)


class PaymentService:
    """Service for handling Mercado Pago payments."""

    def __init__(self, access_token: Optional[str] = None):
        """Initialize payment service.
        
        Args:
            access_token: Mercado Pago access token. If None, uses settings.
        """
        self.access_token = access_token or settings.MERCADOPAGO_ACCESS_TOKEN
        if not self.access_token:
            raise ValueError("MERCADOPAGO_ACCESS_TOKEN must be set")
        
        self.sdk = mercadopago.SDK(self.access_token)
        self.price = settings.MERCADOPAGO_PRODUCT_PRICE

    def create_payment_preference(
        self,
        email: str,
        pet_name: str,
        success_url: str,
        failure_url: str,
        pending_url: str,
    ) -> Dict:
        """Create a payment preference in Mercado Pago.
        
        Args:
            email: Customer email
            pet_name: Pet name (for order description)
            success_url: URL to redirect after successful payment
            failure_url: URL to redirect after failed payment
            pending_url: URL to redirect after pending payment
            
        Returns:
            Dictionary with preference data including init_point (checkout URL)
        """
        try:
            preference_data = {
                "items": [
                    {
                        "title": f"Kit Digital do {pet_name} - PetStory",
                        "description": f"Kit digital completo com livro de colorir e página de homenagem para {pet_name}",
                        "quantity": 1,
                        "currency_id": "BRL",
                        "unit_price": float(self.price),
                    }
                ],
                "payer": {
                    "email": email,
                },
                "back_urls": {
                    "success": success_url,
                    "failure": failure_url,
                    "pending": pending_url,
                },
                "auto_return": "approved",  # Redirect automatically if approved
                "notification_url": f"{settings.API_BASE_URL.rstrip('/')}/api/payment/webhook",  # Webhook URL
                "external_reference": f"{email}_{pet_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                "statement_descriptor": "PetStory Art",
                "expires": True,
                "expiration_date_from": datetime.now().isoformat(),
                "expiration_date_to": (datetime.now() + timedelta(days=1)).isoformat(),  # Valid for 1 day
            }

            logger.info(f"Creating payment preference for {email} - {pet_name}")
            preference_response = self.sdk.preference().create(preference_data)
            
            if preference_response["status"] == 201:
                preference = preference_response["response"]
                logger.info(f"Payment preference created: {preference.get('id')}")
                return {
                    "id": preference.get("id"),
                    "init_point": preference.get("init_point"),  # Checkout URL
                    "sandbox_init_point": preference.get("sandbox_init_point"),  # Sandbox URL
                    "status": "success",
                }
            else:
                error_msg = preference_response.get("message", "Unknown error")
                logger.error(f"Failed to create payment preference: {error_msg}")
                raise Exception(f"Failed to create payment preference: {error_msg}")
                
        except Exception as e:
            logger.error(f"Error creating payment preference: {e}", exc_info=True)
            raise

    def get_payment_info(self, payment_id: str) -> Optional[Dict]:
        """Get payment information by ID.
        
        Args:
            payment_id: Mercado Pago payment ID
            
        Returns:
            Payment information dictionary or None if not found
        """
        try:
            payment_response = self.sdk.payment().get(payment_id)
            
            if payment_response["status"] == 200:
                return payment_response["response"]
            else:
                logger.warning(f"Payment {payment_id} not found or error: {payment_response.get('message')}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting payment info for {payment_id}: {e}", exc_info=True)
            return None

    def verify_payment_status(self, payment_id: str) -> Optional[str]:
        """Verify payment status.
        
        Args:
            payment_id: Mercado Pago payment ID
            
        Returns:
            Payment status: 'approved', 'pending', 'rejected', 'cancelled', or None
        """
        payment_info = self.get_payment_info(payment_id)
        if payment_info:
            return payment_info.get("status")
        return None

    def is_payment_approved(self, payment_id: str) -> bool:
        """Check if payment is approved.
        
        Args:
            payment_id: Mercado Pago payment ID
            
        Returns:
            True if payment is approved, False otherwise
        """
        status = self.verify_payment_status(payment_id)
        return status == "approved"

