from django.conf import settings
import requests
import time
import logging
import json

logger = logging.getLogger(__name__)

def initialize_flutterwave_payment(user, case, amount, is_anonymous=False):
    url = "https://api.flutterwave.com/v3/payments"
    
    # Generate transaction reference
    tx_ref = f"bcf-{case.id}-{user.id}-{int(time.time())}"
    
    headers = {
        "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "tx_ref": tx_ref,
        "amount": "{:.2f}".format(float(amount)),
        "currency": "NGN",
        "redirect_url": f"{settings.SITE_URL}/cases/payment/verify/",
        "payment_type": "card",
        "customer": {
            "email": user.email,
            "name": "Anonymous Donor" if is_anonymous else user.get_full_name() or user.username,
            "phonenumber": ""
        },
        "customizations": {
            "title": "BCF Donation",
            "description": f"Donation for case #{case.id}",
            "logo": f"{settings.SITE_URL}/static/img/logo.png"
        },
        "meta": {
            "case_id": case.id,
            "user_id": user.id,
            "is_anonymous": is_anonymous,
            "tx_ref": tx_ref  # Include tx_ref in meta for reference
        }
    }
    
    try:
        logger.info(f"Initializing payment for case {case.id} by user {user.id}")
        logger.debug(f"Payment payload: {json.dumps(payload, indent=2)}")
        
        response = requests.post(url, headers=headers, json=payload)
        response_data = response.json()
        
        logger.debug(f"Flutterwave response: {json.dumps(response_data, indent=2)}")
        
        if response.status_code != 200:
            raise ValueError(f"Payment initialization failed: HTTP {response.status_code}")
            
        if response_data.get('status') != 'success':
            error_msg = response_data.get('message', 'Unknown error')
            raise ValueError(f"Payment initialization failed: {error_msg}")
            
        # Add tx_ref to response data for donation creation
        response_data['tx_ref'] = tx_ref
        return response_data
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Flutterwave API request error: {str(e)}")
        raise ValueError("Payment service unavailable")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from Flutterwave: {str(e)}")
        raise ValueError("Invalid response from payment service")
    except Exception as e:
        logger.error(f"Unexpected error in payment initialization: {str(e)}")
        raise ValueError(str(e))

def verify_flutterwave_payment(transaction_id):
    """
    Verify a Flutterwave payment using the transaction ID
    """
    url = f"https://api.flutterwave.com/v3/transactions/{transaction_id}/verify"
    headers = {
        "Authorization": f"Bearer {settings.FLUTTERWAVE_SECRET_KEY}",
        "Content-Type": "application/json"
    }
    
    try:
        logger.info(f"Verifying transaction: {transaction_id}")
        response = requests.get(url, headers=headers)
        response_data = response.json()
        
        logger.debug(f"Verification response: {json.dumps(response_data, indent=2)}")
        
        if response.status_code == 200 and response_data.get('status') == 'success':
            data = response_data.get('data', {})
            return {
                'status': 'success',
                'amount': data.get('amount'),
                'currency': data.get('currency'),
                'tx_ref': data.get('tx_ref'),
                'transaction_id': data.get('id')
            }
        else:
            logger.error(f"Verification failed: {response_data.get('message')}")
            return {
                'status': 'failed',
                'message': response_data.get('message', 'Verification failed')
            }
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Verification request error: {str(e)}")
        return {
            'status': 'error',
            'message': 'Could not verify payment'
        }
    except Exception as e:
        logger.error(f"Unexpected verification error: {str(e)}")
        return {
            'status': 'error',
            'message': 'An error occurred during verification'
        }