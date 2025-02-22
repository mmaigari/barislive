import requests
from django.conf import settings
import logging
import uuid

logger = logging.getLogger(__name__)

class FlutterwaveService:
    def __init__(self):
        self.base_url = "https://api.flutterwave.com/v3"
        self.headers = {
            "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    def initialize_payment(self, user, amount, email, tx_ref, callback_url):
        """
        Initialize a payment with Flutterwave
        """
        try:
            payload = {
                "tx_ref": tx_ref,
                "amount": str(round(float(amount), 2)),
                "currency": "NGN",
                "redirect_url": callback_url,
                "payment_options": "card",
                "customer": {
                    "email": email,
                    "name": user.get_full_name() or user.username
                },
                "customizations": {
                    "title": "BCF Sponsorship",
                    "description": "Monthly Sponsorship Payment",
                    "logo": f"{settings.SITE_URL}/static/img/logo.png"
                },
                "meta": {
                    "user_id": user.id,
                    "transaction_type": "sponsorship"
                }
            }

            response = requests.post(
                f"{self.base_url}/payments",
                headers=self.headers,
                json=payload,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Flutterwave API error: {response.status_code} - {response.text}")
                raise ValueError(f"Payment initialization failed: {response.text}")

        except Exception as e:
            logger.error(f"Payment initialization error: {str(e)}")
            raise

    def verify_payment(self, transaction_id):
        """
        Verify a payment transaction
        """
        try:
            response = requests.get(
                f"{self.base_url}/transactions/{transaction_id}/verify",
                headers=self.headers,
                timeout=30
            )

            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"Payment verification failed: {response.status_code} - {response.text}")
                raise ValueError("Payment verification failed")

        except Exception as e:
            logger.error(f"Payment verification error: {str(e)}")
            raise