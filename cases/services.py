from django.conf import settings
from rave_python import Rave
import uuid

class FlutterwaveService:
    def __init__(self):
        self.rave = Rave(
            publicKey=settings.FLUTTERWAVE_PUBLIC_KEY,
            secretKey=settings.FLUTTERWAVE_SECRET_KEY,
            usingEnv=False
        )
    
    def initialize_payment(self, user, case, amount, currency='USD', is_anonymous=False):
        tx_ref = f"bcf-{uuid.uuid4().hex[:8]}"
        
        payment_data = {
            "tx_ref": tx_ref,
            "amount": amount,
            "currency": currency,
            "payment_options": "card,mobilemoney,ussd",
            "customer": {
                "email": user.email,
                "name": "Anonymous Donor" if is_anonymous else user.get_full_name(),
            },
            "customizations": {
                "title": f"Donation for {case.title}",
                "description": f"Supporting case #{case.id}",
                "logo": "https://your-logo-url.com/logo.png"
            },
            "meta": {
                "case_id": case.id,
                "user_id": user.id,
                "is_anonymous": is_anonymous
            }
        }
        
        return self.rave.payment.initialize(**payment_data)