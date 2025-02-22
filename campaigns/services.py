import requests
from django.conf import settings
import uuid
import logging

logger = logging.getLogger(__name__)

class FlutterwaveService:
    def __init__(self):
        self.base_url = "https://api.flutterwave.com/v3"
        self.headers = {
            "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
            "Content-Type": "application/json",
        }

    def initialize_payment(self, user, campaign, amount, currency='NGN', is_anonymous=False):
        try:
            tx_ref = f"bcf-camp-{uuid.uuid4().hex[:8]}"
            
            payload = {
                "tx_ref": tx_ref,
                "amount": str(round(float(amount), 2)),
                "currency": currency,
                "redirect_url": f"{settings.SITE_URL}/campaigns/payment/verify/",
                "payment_options": "card",
                "customer": {
                    "email": user.email,
                    "name": "Anonymous Donor" if is_anonymous else user.get_full_name(),
                },
                "customizations": {
                    "title": f"Donation for {campaign.title}",
                    "description": f"Supporting campaign #{campaign.id}",
                    "logo": f"{settings.SITE_URL}/static/img/logo.png"
                },
                "meta": {
                    "campaign_id": campaign.id,
                    "user_id": user.id,
                    "is_anonymous": is_anonymous
                }
            }

            response = requests.post(
                f"{self.base_url}/payments",
                headers=self.headers,
                json=payload
            )

            response_data = response.json()
            logger.info(f"Payment initialization response: {response_data}")

            if response.status_code == 200 and response_data.get('status') == 'success':
                return {
                    'status': 'success',
                    'tx_ref': tx_ref,
                    'data': response_data.get('data', {})
                }
            else:
                logger.error(f"Payment initialization failed: {response_data}")
                return {
                    'status': 'error',
                    'message': response_data.get('message', 'Payment initialization failed')
                }

        except Exception as e:
            logger.error(f"Payment initialization error: {str(e)}")
            return {
                'status': 'error',
                'message': str(e)
            }