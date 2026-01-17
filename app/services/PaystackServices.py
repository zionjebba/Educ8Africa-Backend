# Enhanced PaystackService with Transfer API for automated payouts
import httpx
import asyncio
from typing import Dict, Any, Optional, List
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

class PaystackService:
    BASE_URL = "https://api.paystack.co"
    
    @classmethod
    def _is_test_mode(cls) -> bool:
        """Check if we're in test mode based on secret key"""
        return settings.PAYSTACK_SECRET_KEY.startswith('sk_test_')
    
    @classmethod
    async def _make_request(cls, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict[str, Any]:
        """Make HTTP request to Paystack API"""
        headers = {
            "Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}",
            "Content-Type": "application/json"
        }
        
        # Log test mode status
        if cls._is_test_mode():
            logger.info(f"Paystack API call in TEST mode: {method} {endpoint}")
        
        async with httpx.AsyncClient() as client:
            try:
                if method.upper() == "POST":
                    response = await client.post(f"{cls.BASE_URL}{endpoint}", json=data, headers=headers)
                elif method.upper() == "GET":
                    response = await client.get(f"{cls.BASE_URL}{endpoint}", headers=headers, params=params)
                elif method.upper() == "PUT":
                    response = await client.put(f"{cls.BASE_URL}{endpoint}", json=data, headers=headers)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")
                
                # Log response status
                logger.info(f"Paystack API response status: {response.status_code}")
                
                response.raise_for_status()
                return response.json()
                
            except httpx.HTTPStatusError as e:
                logger.error(f"Paystack API error: {e.response.status_code} - {e.response.text}")
                raise Exception(f"Paystack API error: {e.response.text}")
            except Exception as e:
                logger.error(f"Paystack request failed: {str(e)}")
                raise

    @classmethod
    async def initialize_payment(cls, data) -> Dict[str, Any]:
        """Initialize payment with Paystack"""
        amount_in_pesewas = int(data.amount * 100)
        payload = {
            "amount": amount_in_pesewas,
            "email": data.email,
            "callback_url": data.callback_url,
            "reference": data.reference,
            "metadata": data.payment_metadata or {},
            "channels": ["card", "bank", "ussd", "qr", "mobile_money", "bank_transfer"],
            "redirect_url": data.callback_url,
        }
        
        if hasattr(data, 'send_email_notification'):
            if not data.send_email_notification:
                payload["channels"] = ["card", "bank", "ussd", "qr", "mobile_money", "bank_transfer"]
        
        if hasattr(data, 'subaccount') and data.subaccount:
            payload["subaccount"] = data.subaccount
            payload["transaction_charge"] = getattr(data, 'transaction_charge', 0)
            payload["bearer"] = getattr(data, 'bearer', 'account')
        
        response = await cls._make_request("POST", "/transaction/initialize", payload)
        
        if not response.get("status"):
            raise Exception(response.get("message", "Payment initialization failed"))
        
        return {
            "status": True,
            "message": response.get("message"),
            "data": response.get("data", {})
        }   

    @classmethod
    async def verify_transaction(cls, reference: str) -> Dict[str, Any]:
        """Verify transaction with Paystack"""
        response = await cls._make_request("GET", f"/transaction/verify/{reference}")
        
        if not response.get("status"):
            raise Exception(response.get("message", "Transaction verification failed"))
        
        return response.get("data", {})

    # ========== TRANSFER API METHODS (NEW) ==========
    
    @classmethod
    async def create_transfer_recipient(
        cls,
        account_number: str,
        bank_code: str,
        name: str,
        description: str = None,
        currency: str = "GHS",
        recipient_type: str = "nuban"  # nuban for bank accounts, mobile_money for momo
    ) -> Dict[str, Any]:
        """
        Create a transfer recipient for payouts
        This stores the beneficiary details for future transfers
        """
        if cls._is_test_mode():
            logger.warning("Creating transfer recipient in TEST mode")
        
        payload = {
            "type": recipient_type,
            "name": name,
            "account_number": account_number,
            "bank_code": bank_code,
            "currency": currency
        }
        
        if description:
            payload["description"] = description
        
        response = await cls._make_request("POST", "/transferrecipient", payload)
        
        if not response.get("status"):
            raise Exception(response.get("message", "Failed to create transfer recipient"))
        
        return response.get("data", {})
    
    @classmethod
    async def initiate_transfer(
        cls,
        amount: float,
        recipient_code: str,
        reason: str = None,
        reference: str = None,
        currency: str = "GHS"
    ) -> Dict[str, Any]:
        """
        Initiate a transfer (payout) to a recipient
        Amount should be in Cedis (not pesewas) - will be converted automatically
        """
        if cls._is_test_mode():
            logger.warning(f"Initiating transfer in TEST mode: GHS {amount} to {recipient_code}")
        
        amount_in_pesewas = int(amount * 100)
        
        payload = {
            "source": "balance",  # Use your Paystack balance
            "amount": amount_in_pesewas,
            "recipient": recipient_code,
            "currency": currency
        }
        
        if reason:
            payload["reason"] = reason
        
        if reference:
            payload["reference"] = reference
        
        response = await cls._make_request("POST", "/transfer", payload)
        
        if not response.get("status"):
            raise Exception(response.get("message", "Transfer initiation failed"))
        
        return response.get("data", {})
    
    @classmethod
    async def verify_transfer(cls, reference: str) -> Dict[str, Any]:
        """
        Verify the status of a transfer
        Returns transfer details including status (success, failed, pending)
        """
        response = await cls._make_request("GET", f"/transfer/verify/{reference}")
        
        if not response.get("status"):
            raise Exception(response.get("message", "Transfer verification failed"))
        
        return response.get("data", {})
    
    @classmethod
    async def finalize_transfer(cls, transfer_code: str, otp: str) -> Dict[str, Any]:
        """
        Finalize a transfer that requires OTP
        Some transfers may require OTP verification for security
        """
        payload = {
            "transfer_code": transfer_code,
            "otp": otp
        }
        
        response = await cls._make_request("POST", "/transfer/finalize_transfer", payload)
        
        if not response.get("status"):
            raise Exception(response.get("message", "Transfer finalization failed"))
        
        return response.get("data", {})
    
    @classmethod
    async def list_transfers(
        cls,
        page: int = 1,
        per_page: int = 50,
        status: str = None,
        from_date: str = None,
        to_date: str = None
    ) -> Dict[str, Any]:
        """
        List all transfers
        Status can be: success, failed, pending
        """
        params = {
            "page": page,
            "perPage": per_page
        }
        
        if status:
            params["status"] = status
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        
        response = await cls._make_request("GET", "/transfer", params=params)
        
        if not response.get("status"):
            raise Exception(response.get("message", "Failed to fetch transfers"))
        
        return response.get("data", {})
    
    @classmethod
    async def get_transfer_fee(cls, amount: float) -> Dict[str, Any]:
        """
        Check the transfer fee for a given amount
        Returns the fee that Paystack will charge
        """
        amount_in_pesewas = int(amount * 100)
        
        params = {"amount": amount_in_pesewas}
        
        response = await cls._make_request("GET", "/transfer/fee", params=params)
        
        if not response.get("status"):
            raise Exception(response.get("message", "Failed to get transfer fee"))
        
        # Convert fee from pesewas to cedis
        data = response.get("data", {})
        if "fee" in data:
            data["fee_in_cedis"] = data["fee"] / 100
        
        return data
    
    @classmethod
    async def disable_otp_for_transfers(cls) -> Dict[str, Any]:
        """
        Disable OTP requirement for transfers
        WARNING: This reduces security. Use with caution.
        """
        response = await cls._make_request("POST", "/transfer/disable_otp")
        
        if not response.get("status"):
            raise Exception(response.get("message", "Failed to disable OTP"))
        
        return response.get("data", {})
    
    @classmethod
    async def enable_otp_for_transfers(cls) -> Dict[str, Any]:
        """
        Enable OTP requirement for transfers
        Recommended for security
        """
        response = await cls._make_request("POST", "/transfer/enable_otp")
        
        if not response.get("status"):
            raise Exception(response.get("message", "Failed to enable OTP"))
        
        return response.get("data", {})
    
    # ========== MOBILE MONEY TRANSFER METHODS ==========
    
    @classmethod
    async def create_mobile_money_recipient(
        cls,
        mobile_number: str,
        provider: str,  # 'mtn', 'vodafone', 'tgo' (AirtelTigo)
        name: str,
        description: str = None
    ) -> Dict[str, Any]:
        """
        Create a mobile money transfer recipient
        Provider must be one of: mtn, vodafone, tgo
        """
        if cls._is_test_mode():
            logger.warning("Creating mobile money recipient in TEST mode")
        
        payload = {
            "type": "mobile_money",
            "name": name,
            "account_number": mobile_number,
            "bank_code": provider.upper(),  # MTN, VOD, TGO
            "currency": "GHS"
        }
        
        if description:
            payload["description"] = description
        
        response = await cls._make_request("POST", "/transferrecipient", payload)
        
        if not response.get("status"):
            raise Exception(response.get("message", "Failed to create mobile money recipient"))
        
        return response.get("data", {})

    # ========== EXISTING METHODS (UNCHANGED) ==========

    @classmethod
    async def create_subaccount(
        cls,
        business_name: str,
        bank_code: str,
        account_number: str,
        percentage_charge: float = 0,
        description: str = None
    ) -> Dict[str, Any]:
        """Create a subaccount for split payments"""
        
        if cls._is_test_mode():
            logger.warning("Creating subaccount in TEST mode - settlements won't be real")
        
        payload = {
            "business_name": business_name,
            "settlement_bank": bank_code,
            "account_number": account_number,
            "percentage_charge": percentage_charge,
            "description": description or f"Subaccount for {business_name}"
        }
        
        response = await cls._make_request("POST", "/subaccount", payload)
        
        if not response.get("status"):
            raise Exception(response.get("message", "Subaccount creation failed"))
        
        return response.get("data", {})

    @classmethod
    async def list_subaccounts(cls, page: int = 1, per_page: int = 50) -> Dict[str, Any]:
        """List all subaccounts"""
        params = {
            "page": page,
            "perPage": per_page
        }
        
        response = await cls._make_request("GET", "/subaccount", params=params)
        
        if not response.get("status"):
            raise Exception(response.get("message", "Failed to fetch subaccounts"))
        
        return response.get("data", {})

    @classmethod
    async def update_subaccount(
        cls,
        subaccount_code: str,
        business_name: str = None,
        bank_code: str = None,
        account_number: str = None,
        percentage_charge: float = None,
        description: str = None
    ) -> Dict[str, Any]:
        """Update an existing subaccount"""
        
        if cls._is_test_mode():
            logger.warning("Updating subaccount in TEST mode - changes won't affect real settlements")
        
        payload = {}
        
        if business_name:
            payload["business_name"] = business_name
        if bank_code:
            payload["settlement_bank"] = bank_code
        if account_number:
            payload["account_number"] = account_number
        if percentage_charge is not None:
            payload["percentage_charge"] = percentage_charge
        if description:
            payload["description"] = description
        
        response = await cls._make_request("PUT", f"/subaccount/{subaccount_code}", payload)
        
        if not response.get("status"):
            raise Exception(response.get("message", "Subaccount update failed"))
        
        return response.get("data", {})

    @classmethod
    async def resolve_account(cls, account_number: str, bank_code: str) -> Dict[str, Any]:
        """Resolve account number to get account name"""
        
        if cls._is_test_mode():
            logger.info("Resolving account in TEST mode - use real account details for accurate results")
        
        params = {
            "account_number": account_number,
            "bank_code": bank_code
        }
        
        response = await cls._make_request("GET", "/bank/resolve", params=params)
        
        if not response.get("status"):
            raise Exception(response.get("message", "Account resolution failed"))
        
        return response.get("data", {})

    @classmethod
    async def list_banks(cls, country: str = "ghana") -> Dict[str, Any]:
        """List all supported banks"""
        params = {"country": country, "use_cursor": "false", "perPage": 100}
        
        response = await cls._make_request("GET", "/bank", params=params)
        
        if not response.get("status"):
            raise Exception(response.get("message", "Failed to fetch banks"))
        
        return response.get("data", {})

    @classmethod
    async def get_subaccount(cls, subaccount_code: str) -> Dict[str, Any]:
        """Get details of a specific subaccount"""
        response = await cls._make_request("GET", f"/subaccount/{subaccount_code}")
        
        if not response.get("status"):
            raise Exception(response.get("message", "Failed to fetch subaccount details"))
        
        return response.get("data", {})


# ========== HELPER CLASS FOR PAYOUT OPERATIONS ==========

class PaystackPayoutHelper:
    """Helper methods for common payout operations"""
    
    @staticmethod
    async def process_distributor_payout(
        distributor_name: str,
        account_number: str,
        bank_code: str,
        amount: float,
        withdrawal_id: str,
        recipient_code: str = None
    ) -> Dict[str, Any]:
        """
        Complete process for distributor payout
        1. Create recipient if not exists
        2. Initiate transfer
        3. Return transfer details
        """
        try:
            # Step 1: Create or use existing recipient
            if not recipient_code:
                logger.info(f"Creating transfer recipient for {distributor_name}")
                recipient_data = await PaystackService.create_transfer_recipient(
                    account_number=account_number,
                    bank_code=bank_code,
                    name=distributor_name,
                    description=f"Distributor payout recipient - {distributor_name}"
                )
                recipient_code = recipient_data.get("recipient_code")
                logger.info(f"Recipient created: {recipient_code}")
            
            # Step 2: Check transfer fee
            fee_data = await PaystackService.get_transfer_fee(amount)
            transfer_fee = fee_data.get("fee_in_cedis", 0)
            logger.info(f"Transfer fee for GHS {amount}: GHS {transfer_fee}")
            
            # Step 3: Initiate transfer
            logger.info(f"Initiating transfer of GHS {amount} to {recipient_code}")
            transfer_data = await PaystackService.initiate_transfer(
                amount=amount,
                recipient_code=recipient_code,
                reason=f"Distributor withdrawal payout - {withdrawal_id}",
                reference=f"PAYOUT-{withdrawal_id}"
            )
            
            logger.info(f"Transfer initiated: {transfer_data.get('transfer_code')}")
            
            return {
                "success": True,
                "recipient_code": recipient_code,
                "transfer_code": transfer_data.get("transfer_code"),
                "transfer_id": transfer_data.get("id"),
                "amount": amount,
                "fee": transfer_fee,
                "status": transfer_data.get("status"),
                "reference": transfer_data.get("reference"),
                "message": "Payout initiated successfully"
            }
            
        except Exception as e:
            logger.error(f"Payout processing failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Payout processing failed"
            }
    
    @staticmethod
    async def verify_payout_status(reference: str) -> Dict[str, Any]:
        """
        Check the status of a payout
        Returns: success, failed, pending, or reversed
        """
        try:
            transfer_data = await PaystackService.verify_transfer(reference)
            
            return {
                "success": True,
                "status": transfer_data.get("status"),
                "amount": transfer_data.get("amount") / 100,  # Convert from pesewas
                "transfer_code": transfer_data.get("transfer_code"),
                "recipient": transfer_data.get("recipient"),
                "reason": transfer_data.get("reason"),
                "transferred_at": transfer_data.get("transferred_at"),
                "message": f"Transfer status: {transfer_data.get('status')}"
            }
            
        except Exception as e:
            logger.error(f"Payout verification failed: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "message": "Payout verification failed"
            }


# Test utilities for development
class PaystackTestUtils:
    """Utilities for testing Paystack integration"""
    
    TEST_CARDS = {
        "success": "4084084084084081",
        "declined": "4084084084084008",
        "insufficient_funds": "4084084084084016",
        "invalid_pin": "4084084084084024"
    }
    
    TEST_BANK_ACCOUNTS = {
        "gtb": {
            "bank_code": "058",
            "account_number": "0123456789"
        },
        "access": {
            "bank_code": "044", 
            "account_number": "0987654321"
        }
    }
    
    # Test transfer recipient details
    TEST_TRANSFER_RECIPIENT = {
        "name": "Test Distributor",
        "account_number": "0123456789",
        "bank_code": "058"  # GTBank
    }
    
    @classmethod
    def get_test_email(cls) -> str:
        """Get a test email for transactions"""
        return "test@example.com"
    
    @classmethod
    def generate_test_reference(cls) -> str:
        """Generate a test transaction reference"""
        import uuid
        return f"test_{uuid.uuid4().hex[:8]}"
    
    @classmethod
    def get_test_mobile_money(cls, provider: str = "mtn") -> Dict[str, str]:
        """Get test mobile money details"""
        providers = {
            "mtn": {"number": "0244000000", "code": "MTN"},
            "vodafone": {"number": "0204000000", "code": "VOD"},
            "airteltigo": {"number": "0264000000", "code": "TGO"}
        }
        return providers.get(provider.lower(), providers["mtn"])