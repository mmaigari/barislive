import requests
from django.conf import settings
import logging
import json

logger = logging.getLogger(__name__)

def initialize_flutterwave_payment(amount, email, tx_ref, callback_url):
    """
    Initialize a Flutterwave payment using the v3 API
    """
    try:
        url = "https://api.flutterwave.com/v3/payments"
        
        headers = {
            "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
            "Content-Type": "application/json",
        }

        # Format amount properly
        formatted_amount = str(round(float(amount), 2))

        payload = {
            "tx_ref": tx_ref,
            "amount": formatted_amount,
            "currency": "NGN",
            "redirect_url": callback_url,
            "payment_options": "card",
            "customer": {
                "email": email,
            },
            "customizations": {
                "title": "Baris Charity Foundation",
                "description": "Campaign Donation",
                "logo": f"{settings.SITE_URL}/static/img/logo.png"
            }
        }

        # Log request details
        logger.debug(f"Initializing payment with tx_ref: {tx_ref}")
        
        response = requests.post(
            url, 
            json=payload,
            headers=headers,
        )

        # Log the response for debugging
        logger.debug(f"Flutterwave response status: {response.status_code}")
        logger.debug(f"Flutterwave response: {response.text}")

        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"Payment initialization failed with status {response.status_code}")
            raise ValueError(f"Payment initialization failed: {response.text}")

    except Exception as e:
        logger.error(f"Payment initialization error: {str(e)}")
        raise

def verify_flutterwave_payment(transaction_id):
    """
    Verify a Flutterwave payment transaction
    """
    try:
        url = f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify"
        headers = {
            "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
            "Content-Type": "application/json",
        }
        
        # Make the request and handle response
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        try:
            return response.json()
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON response from Flutterwave: {response.text}")
            raise ValueError("Invalid response from payment provider")
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Flutterwave request error: {str(e)}")
        raise ValueError("Failed to connect to payment provider")
    except Exception as e:
        logger.error(f"Flutterwave payment verification error: {str(e)}")
        raise