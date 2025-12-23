"""Simple in-memory storage for payment status (for MVP).
In production, this should be replaced with a database."""

import logging
from typing import Dict, Optional
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PaymentStorage:
    """Simple in-memory storage for payment status.
    
    This is a temporary solution for MVP. In production, use a database.
    """

    def __init__(self):
        """Initialize payment storage."""
        # Format: {payment_id: {"status": "approved", "email": "...", "pet_name": "...", "timestamp": ...}}
        self._payments: Dict[str, Dict] = {}
        # Format: {external_reference: payment_id}
        self._references: Dict[str, str] = {}
        # Cleanup old entries periodically (older than 7 days)
        self._cleanup_threshold = timedelta(days=7)

    def save_payment(
        self,
        payment_id: str,
        status: str,
        email: str,
        pet_name: Optional[str] = None,
        external_reference: Optional[str] = None,
    ) -> None:
        """Save payment information.
        
        Args:
            payment_id: Mercado Pago payment ID
            status: Payment status (approved, pending, rejected, etc.)
            email: Customer email
            pet_name: Pet name (optional)
            external_reference: External reference from Mercado Pago
        """
        self._payments[payment_id] = {
            "status": status,
            "email": email,
            "pet_name": pet_name,
            "timestamp": datetime.now(),
        }
        
        if external_reference:
            self._references[external_reference] = payment_id
        
        logger.info(f"Saved payment {payment_id} with status {status} for {email}")

    def get_payment(self, payment_id: str) -> Optional[Dict]:
        """Get payment information.
        
        Args:
            payment_id: Mercado Pago payment ID
            
        Returns:
            Payment information dictionary or None
        """
        return self._payments.get(payment_id)

    def get_payment_by_reference(self, external_reference: str) -> Optional[Dict]:
        """Get payment by external reference.
        
        Args:
            external_reference: External reference from Mercado Pago
            
        Returns:
            Payment information dictionary or None
        """
        payment_id = self._references.get(external_reference)
        if payment_id:
            return self.get_payment(payment_id)
        return None

    def is_payment_approved(self, payment_id: str) -> bool:
        """Check if payment is approved.
        
        Args:
            payment_id: Mercado Pago payment ID
            
        Returns:
            True if payment is approved, False otherwise
        """
        payment = self.get_payment(payment_id)
        if payment:
            return payment["status"] == "approved"
        return False

    def can_upload(self, email: str, pet_name: str) -> bool:
        """Check if user can upload (has approved payment).
        
        Args:
            email: Customer email
            pet_name: Pet name
            
        Returns:
            True if user has an approved payment for this pet, False otherwise
        """
        # Check if there's any approved payment for this email and pet
        for payment_id, payment_data in self._payments.items():
            if (
                payment_data["email"] == email
                and payment_data.get("pet_name") == pet_name
                and payment_data["status"] == "approved"
            ):
                # Check if payment is not too old (within 24 hours)
                age = datetime.now() - payment_data["timestamp"]
                if age < timedelta(hours=24):
                    return True
        return False

    def cleanup_old_payments(self) -> None:
        """Remove payments older than cleanup threshold."""
        now = datetime.now()
        to_remove = []
        
        for payment_id, payment_data in self._payments.items():
            age = now - payment_data["timestamp"]
            if age > self._cleanup_threshold:
                to_remove.append(payment_id)
        
        for payment_id in to_remove:
            del self._payments[payment_id]
            # Also remove from references
            self._references = {
                ref: pid for ref, pid in self._references.items() if pid != payment_id
            }
        
        if to_remove:
            logger.info(f"Cleaned up {len(to_remove)} old payment records")


# Global instance
payment_storage = PaymentStorage()

