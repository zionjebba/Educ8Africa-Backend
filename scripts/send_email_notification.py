import sys
import os
import asyncio
from datetime import datetime
from typing import Dict, List

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

from app.services.MicrosoftGraphClientPublic import MicrosoftGraphClientPublic
from app.core.config import settings

def get_graph_client() -> MicrosoftGraphClientPublic:
    """Create and return a Microsoft Graph Public client instance."""
    return MicrosoftGraphClientPublic(
        tenant_id=settings.MICROSOFT_TENANT_ID,
        client_id=settings.MICROSOFT_CLIENT_ID,
        client_secret=settings.MICROSOFT_CLIENT_SECRET,
        default_sender="ideotronix@ideationaxis.com"
    )

# ============================
# 1. CUSTOMER NOTIFICATION
# ============================

async def send_customer_verification_notice(customer_data: dict, purchase_data: dict, graph_client: MicrosoftGraphClientPublic):
    """Send verification completion notice to customer."""
    
    email_subject = f"✅ Purchase Verified - {purchase_data['product_name']} Order Confirmed"
    
    email_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #0a2463 0%, #1e4db7 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 28px;">✅ Order Verified & Confirmed! 🎉</h1>
            <p style="color: #e0e0e0; margin: 10px 0 0 0;">Your purchase has been successfully verified</p>
        </div>
        
        <div style="background: white; padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
            <p style="font-size: 16px; margin-top: 0;">Dear <strong>{customer_data["name"]}</strong>,</p>
            
            <div style="background: #d4edda; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745;">
                <p style="margin: 0; color: #155724;">
                    <strong>✓ Payment Verified Successfully!</strong><br>
                    We noticed you completed your payment but didn't wait for our verification process. No worries - we've now verified your purchase and your order is confirmed!
                </p>
            </div>
            
            <p>Thank you for your purchase of <strong>{purchase_data["product_name"]}</strong>. Your order is now being processed.</p>
            
            <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #0a2463; margin-top: 0;">Order Summary</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <strong>Product:</strong>
                        </td>
                        <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6; text-align: right;">
                            {purchase_data["product_name"]}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <strong>Quantity:</strong>
                        </td>
                        <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6; text-align: right;">
                            {purchase_data["quantity"]} unit(s)
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                            <strong>Unit Price:</strong>
                        </td>
                        <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6; text-align: right;">
                            GHS {purchase_data["unit_price"]:.2f}
                        </td>
                    </tr>
                    <tr>
                        <td style="padding: 15px 0; font-size: 18px;">
                            <strong>Total Amount:</strong>
                        </td>
                        <td style="padding: 15px 0; text-align: right; font-size: 18px; color: #0a2463;">
                            <strong>GHS {purchase_data["total_amount"]:.2f}</strong>
                        </td>
                    </tr>
                </table>
            </div>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <h3 style="color: #0a2463; margin-top: 0;">Delivery Information</h3>
                <p style="margin: 5px 0;"><strong>Institution:</strong> {customer_data["institution"]}</p>
                <p style="margin: 5px 0;"><strong>Contact:</strong> {customer_data["phone"]}</p>
                <p style="margin: 5px 0;"><strong>Email:</strong> {customer_data["email"]}</p>
            </div>
            
            {f'''
            <div style="background: #d4edda; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745;">
                <p style="margin: 0; color: #155724;">
                    <strong>✓ Distributor Discount Applied (10%):</strong> {purchase_data["distributor_code"]}<br>
                    <small>You saved with this distributor code!</small>
                </p>
            </div>
            ''' if purchase_data.get("distributor_code") else ""}
            
            <div style="background: #e8f4f8; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #0a2463;">
                <p style="margin: 0; color: #0a2463;">
                    <strong>Payment Reference:</strong> {purchase_data["payment_reference"]}<br>
                    <strong>Payment Date:</strong> {purchase_data["payment_date"]}<br>
                    <strong>Verification Date:</strong> {datetime.now().strftime("%B %d, %Y at %I:%M %p")}
                </p>
            </div>
            
            <div style="background: #fff9e6; padding: 20px; border-radius: 8px; margin: 25px 0;">
                <h3 style="color: #0a2463; margin-top: 0;">📦 What's Next?</h3>
                <ol style="margin: 10px 0; padding-left: 20px;">
                    <li style="margin: 10px 0;">Our team will prepare your order</li>
                    <li style="margin: 10px 0;">You'll receive a shipping confirmation email</li>
                    <li style="margin: 10px 0;">Delivery typically takes 3-5 business days</li>
                    <li style="margin: 10px 0;">We'll contact you for delivery coordination</li>
                </ol>
            </div>
            
            <div style="background: #e7f3ff; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #17a2b8;">
                <p style="margin: 0; color: #004085;">
                    <strong>💡 Quick Tip:</strong> In the future, please wait for our verification email before leaving the payment page. This helps us process your order faster!
                </p>
            </div>
            
            <div style="margin: 30px 0; padding: 20px; background: #f1f3f5; border-radius: 8px; text-align: center;">
                <p style="margin: 0 0 15px 0; color: #495057;">Need help with your order?</p>
                <a href="mailto:ideotronix@ideationaxis.com" style="display: inline-block; background: #0a2463; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-weight: bold;">Contact Support</a>
            </div>
            
            <p style="color: #666; font-size: 14px; margin-top: 30px;">
                Thank you for choosing Ideotronix. We appreciate your business!
            </p>
        </div>
        
        <div style="background: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; margin-top: 20px;">
            <p style="margin: 5px 0; color: #666; font-size: 12px;">
                © {datetime.now().year} Ideotronix - Ideation Axis<br>
                Empowering Innovation Through Electronics
            </p>
        </div>
    </body>
    </html>
    """
    
    try:
        await graph_client.send_email(
            to_emails=[customer_data['email']],
            subject=email_subject,
            body_html=email_body,
            department="products"
        )
        return True
    except Exception as e:
        print(f"Failed to send customer email to {customer_data['email']}: {str(e)}")
        return False
# ============================
# 2. DISTRIBUTOR NOTIFICATION
# ============================

async def send_distributor_commission_notice(customer_data: dict, purchase_data: dict, distributor_data: dict, graph_client: MicrosoftGraphClientPublic):
    """Send commission earned notice to distributor."""
    
    email_subject = f"💰 Commission Earned (Verified) - GHS {purchase_data['commission_earned']:.2f}"
    
    email_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
    </head>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
            <h1 style="color: white; margin: 0; font-size: 28px;">💰 Commission Verified!</h1>
            <p style="color: #e0e0e0; margin: 10px 0 0 0;">Your sale has been verified and commission credited</p>
        </div>
        
        <div style="background: white; padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
            <p style="font-size: 16px; margin-top: 0;">Dear <strong>{distributor_data["full_name"]}</strong>,</p>
            
            <div style="background: #fff3cd; padding: 20px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #ffc107;">
                <p style="margin: 0; color: #856404;">
                    <strong>ℹ️ Purchase Verification Notice</strong><br>
                    We noticed that customer <strong>{customer_data["name"]}</strong> completed their payment but didn't wait for our automatic verification process. We've now manually verified their purchase and your commission has been credited!
                </p>
            </div>
            
            <div style="background: #d4edda; padding: 25px; border-radius: 8px; margin: 25px 0; text-align: center; border: 2px solid #28a745;">
                <h2 style="color: #155724; margin: 0 0 10px 0; font-size: 32px;">GHS {purchase_data["commission_earned"]:.2f}</h2>
                <p style="color: #155724; margin: 0; font-size: 18px;">Commission Earned</p>
            </div>
            
            <h3 style="color: #28a745; border-bottom: 2px solid #28a745; padding-bottom: 10px;">Sale Details</h3>
            <table style="width: 100%; margin: 15px 0; border-collapse: collapse;">
                <tr style="background: #f8f9fa;">
                    <td style="padding: 12px 8px; border-bottom: 1px solid #dee2e6;"><strong>Product:</strong></td>
                    <td style="padding: 12px 8px; border-bottom: 1px solid #dee2e6; text-align: right;">{purchase_data["product_name"]}</td>
                </tr>
                <tr>
                    <td style="padding: 12px 8px; border-bottom: 1px solid #dee2e6;"><strong>Quantity:</strong></td>
                    <td style="padding: 12px 8px; border-bottom: 1px solid #dee2e6; text-align: right;">{purchase_data["quantity"]} unit(s)</td>
                </tr>
                <tr style="background: #f8f9fa;">
                    <td style="padding: 12px 8px; border-bottom: 1px solid #dee2e6;"><strong>Unit Price:</strong></td>
                    <td style="padding: 12px 8px; border-bottom: 1px solid #dee2e6; text-align: right;">GHS {purchase_data["unit_price"]:.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 12px 8px; border-bottom: 1px solid #dee2e6;"><strong>Sale Total:</strong></td>
                    <td style="padding: 12px 8px; border-bottom: 1px solid #dee2e6; text-align: right;">GHS {purchase_data["total_amount"]:.2f}</td>
                </tr>
                <tr style="background: #d4edda;">
                    <td style="padding: 15px 8px; font-size: 16px;"><strong>Your Commission:</strong></td>
                    <td style="padding: 15px 8px; text-align: right; font-size: 16px; color: #28a745;"><strong>GHS {purchase_data["commission_earned"]:.2f}</strong></td>
                </tr>
            </table>
            
            <h3 style="color: #28a745; border-bottom: 2px solid #28a745; padding-bottom: 10px; margin-top: 30px;">Customer Information</h3>
            <table style="width: 100%; margin: 15px 0;">
                <tr style="background: #f8f9fa;">
                    <td style="padding: 10px 8px;"><strong>Name:</strong></td>
                    <td style="padding: 10px 8px; text-align: right;">{customer_data["name"]}</td>
                </tr>
                <tr>
                    <td style="padding: 10px 8px;"><strong>Institution:</strong></td>
                    <td style="padding: 10px 8px; text-align: right;">{customer_data["institution"]}</td>
                </tr>
                <tr style="background: #f8f9fa;">
                    <td style="padding: 10px 8px;"><strong>Contact:</strong></td>
                    <td style="padding: 10px 8px; text-align: right;">{customer_data["phone"]}</td>
                </tr>
            </table>
            
            <div style="background: #e7f3ff; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #0a2463;">
                <p style="margin: 0; color: #004085;">
                    <strong>Transaction Reference:</strong> {purchase_data["payment_reference"]}<br>
                    <strong>Payment Date:</strong> {purchase_data["payment_date"]}<br>
                    <strong>Verification Date:</strong> {datetime.now().strftime("%B %d, %Y at %I:%M %p")}
                </p>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="https://ideotronix.ideationaxis.com/ideotronix/distributor/dashboard" style="display: inline-block; background: #28a745; color: white; padding: 15px 40px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;">View Dashboard</a>
            </div>
            
            <p style="color: #666; font-size: 14px; margin-top: 30px; text-align: center;">
                Keep up the excellent work! 🎉
            </p>
        </div>
        
        <div style="background: #f8f9fa; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; margin-top: 20px;">
            <p style="margin: 5px 0; color: #666; font-size: 12px;">
                © {datetime.now().year} Ideotronix - Distributor Program
            </p>
        </div>
    </body>
    </html>
    """
    
    try:
        await graph_client.send_email(
            to_emails=[distributor_data['email']],
            subject=email_subject,
            body_html=email_body,
            department="distributors"
        )
        return True
    except Exception as e:
        print(f"Failed to send distributor email to {distributor_data['email']}: {str(e)}")
        return False

# ============================
# 3. ADMIN NOTIFICATION
# ============================

async def send_admin_new_purchase_notice(customer_data: dict, purchase_data: dict, graph_client: MicrosoftGraphClientPublic, admin_emails: list):
    """Send new purchase notification to admins."""
    
    email_subject = f"🛒 New Verified Purchase - {purchase_data['product_name']} - GHS {purchase_data['total_amount']:.2f}"
    
    email_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
        <div style="background: #0a2463; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
            <h2 style="color: white; margin: 0;">🛒 New Product Order (Manually Verified)</h2>
        </div>
        
        <div style="background: white; padding: 25px; border: 1px solid #e0e0e0;">
            <div style="background: #fff3cd; color: #856404; padding: 15px; border-radius: 5px; margin-bottom: 20px; border-left: 4px solid #ffc107;">
                <h3 style="margin: 0;">⚠️ Manual Verification Notice</h3>
                <p style="margin: 5px 0 0 0; font-size: 14px;">Customer completed payment but didn't wait for automatic verification. Purchase has been manually verified and emails sent.</p>
            </div>
            
            <div style="background: #28a745; color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; text-align: center;">
                <h3 style="margin: 0;">Payment Confirmed & Verified</h3>
                <p style="margin: 5px 0 0 0; font-size: 14px;">Order ready for processing</p>
            </div>
            
            <h3 style="color: #0a2463; border-bottom: 2px solid #0a2463; padding-bottom: 10px;">Order Details</h3>
            <table style="width: 100%; margin: 15px 0;">
                <tr>
                    <td style="padding: 8px 0;"><strong>Product:</strong></td>
                    <td style="padding: 8px 0;">{purchase_data["product_name"]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;"><strong>Quantity:</strong></td>
                    <td style="padding: 8px 0;">{purchase_data["quantity"]} unit(s)</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;"><strong>Unit Price:</strong></td>
                    <td style="padding: 8px 0;">GHS {purchase_data["unit_price"]:.2f}</td>
                </tr>
                <tr style="background: #f8f9fa;">
                    <td style="padding: 12px 8px; font-size: 16px;"><strong>Total Amount:</strong></td>
                    <td style="padding: 12px 8px; font-size: 16px; color: #28a745;"><strong>GHS {purchase_data["total_amount"]:.2f}</strong></td>
                </tr>
            </table>
            
            <h3 style="color: #0a2463; border-bottom: 2px solid #0a2463; padding-bottom: 10px; margin-top: 30px;">Customer Information</h3>
            <table style="width: 100%; margin: 15px 0;">
                <tr>
                    <td style="padding: 8px 0;"><strong>Name:</strong></td>
                    <td style="padding: 8px 0;">{customer_data["name"]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;"><strong>Email:</strong></td>
                    <td style="padding: 8px 0;"><a href="mailto:{customer_data['email']}" style="color: #0a2463;">{customer_data["email"]}</a></td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;"><strong>Phone:</strong></td>
                    <td style="padding: 8px 0;"><a href="tel:{customer_data['phone']}" style="color: #0a2463;">{customer_data["phone"]}</a></td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;"><strong>Institution:</strong></td>
                    <td style="padding: 8px 0;">{customer_data["institution"]}</td>
                </tr>
            </table>
            
            <h3 style="color: #0a2463; border-bottom: 2px solid #0a2463; padding-bottom: 10px; margin-top: 30px;">Payment Information</h3>
            <table style="width: 100%; margin: 15px 0;">
                <tr>
                    <td style="padding: 8px 0;"><strong>Reference:</strong></td>
                    <td style="padding: 8px 0; font-family: monospace;">{purchase_data["payment_reference"]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;"><strong>Payment Date:</strong></td>
                    <td style="padding: 8px 0;">{purchase_data["payment_date"]}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;"><strong>Verification Date:</strong></td>
                    <td style="padding: 8px 0;">{datetime.now().strftime("%B %d, %Y at %I:%M %p")}</td>
                </tr>
                <tr>
                    <td style="padding: 8px 0;"><strong>Status:</strong></td>
                    <td style="padding: 8px 0;"><span style="background: #28a745; color: white; padding: 3px 10px; border-radius: 3px; font-size: 12px;">VERIFIED</span></td>
                </tr>
            </table>
            
            {f'''
            <div style="background: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745;">
                <p style="margin: 0 0 5px 0; color: #155724;">
                    <strong>✓ Distributor Code Applied (10% discount):</strong> {purchase_data["distributor_code"]}
                </p>
                <p style="margin: 5px 0 0 0; color: #155724; font-size: 14px;">Commission: GHS {purchase_data["commission_earned"]:.2f}</p>
            </div>
            ''' if purchase_data.get("distributor_code") else ""}
            
            <div style="background: #e7f3ff; padding: 20px; border-radius: 5px; margin: 25px 0; border-left: 4px solid #17a2b8;">
                <h4 style="margin-top: 0; color: #0c5460;">📧 Notifications Sent</h4>
                <ul style="margin: 10px 0; padding-left: 20px; color: #0c5460;">
                    <li>✅ Customer confirmation email sent</li>
                    {f'<li>✅ Distributor commission notification sent</li>' if purchase_data.get("distributor_code") else ''}
                    <li>✅ Admin team notified</li>
                </ul>
            </div>
            
            <div style="background: #fff9e6; padding: 20px; border-radius: 5px; margin: 25px 0; border-left: 4px solid #ffc107;">
                <h4 style="margin-top: 0; color: #856404;">⚠️ Action Required</h4>
                <ul style="margin: 10px 0; padding-left: 20px; color: #856404;">
                    <li>Prepare order for shipment</li>
                    <li>Update inventory records</li>
                    <li>Contact customer for delivery coordination</li>
                    <li>Process distributor commission if applicable</li>
                </ul>
            </div>
            
            <div style="text-align: center; margin-top: 30px;">
                <a href="mailto:{customer_data['email']}" style="display: inline-block; background: #0a2463; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 5px;">Contact Customer</a>
            </div>
        </div>
        
        <div style="background: #f8f9fa; padding: 15px; text-align: center; border-radius: 0 0 8px 8px; margin-top: 20px;">
            <p style="margin: 0; color: #666; font-size: 12px;">
                Ideotronix Admin Notification System
            </p>
        </div>
    </body>
    </html>
    """
    
    try:
        await graph_client.send_admin_notification(
            admin_emails=admin_emails,
            subject=email_subject,
            template_html=email_body,
            template_vars={},
            reply_to_applicant=customer_data["email"]
        )
        return True
    except Exception as e:
        print(f"Failed to send admin emails: {str(e)}")
        return False

# ============================
# 4. MAIN EXECUTION FUNCTION
# ============================

async def send_all_notifications():
    """
    Main function to send all notifications.
    """
    print("\n" + "="*80)
    print("🚀 STARTING EMAIL NOTIFICATION CAMPAIGN")
    print("="*80)
    
    # Initialize Graph client
    graph_client = get_graph_client()
    
    # ===========================================
    # 1. DISTRIBUTOR DATA (from your provided data)
    # ===========================================
    distributor_data = {
        "id": "f43e7ca2-4cf0-4068-a044-cf28c270dbd5",
        "full_name": "Eugene Amankwah",
        "email": "eugamankwah@gmail.com",
        "phone": "+233248068242",
        "institution": "University of Mines and Technology (UMaT)",
        "location": "Takoradi",
        "distributor_code": "IDTR-SIUC6V",
        "total_earnings": 15.56,  # From your data
        "status": "ACTIVE"
    }
    
    # ===========================================
    # 2. CUSTOMER & PURCHASE DATA (example)
    # ===========================================
    customer_data = {
        "name": "Offei Rockson Junior",
        "email": "rocksonoffeijnr@gmail.com",
        "phone": "+233546781261",
        "institution": "University of Mines and Technology (UMaT)"
    }
    
    purchase_data = {
        "product_name": "Arduino Starter Kit",
        "quantity": 1,
        "unit_price": 500.00,
        "total_amount": 450.00,
        "commission_earned": 77.80,
        "payment_reference": "PAY-20260109092702-10",
        "payment_date": "January 09, 2026 at 09:27 AM",
        "distributor_code": "IDTR-SIUC6V",
    }
    
    # ===========================================
    # 3. ADMIN EMAILS
    # ===========================================
    ADMIN_EMAILS = ["philipgyimah@ideationaxis.com", "kelvingbolo@ideationaxis.com", "bernardephraim@ideationaxis.com", "kwameyeboah@ideationaxis.com"]
    
    admin_emails = ADMIN_EMAILS
    
    # ===========================================
    # 4. SEND ALL NOTIFICATIONS
    # ===========================================
    results = []
    
    print(f"\n📧 Distributor: {distributor_data['full_name']}")
    print(f"📧 Customer: {customer_data['name']}")
    print(f"💰 Purchase Amount: GHS {purchase_data['total_amount']:.2f}")
    print(f"💸 Commission: GHS {purchase_data['commission_earned']:.2f}\n")
    
    # Send customer notification
    print("1. Sending customer notification...")
    customer_result = await send_customer_verification_notice(
        customer_data, 
        purchase_data,
        graph_client=graph_client
    )
    results.append(customer_result)
    
    # Add small delay
    await asyncio.sleep(1)
    
    # Send distributor notification
    print("\n2. Sending distributor notification...")
    distributor_result = await send_distributor_commission_notice(
        customer_data, 
        purchase_data,
        distributor_data=distributor_data,
        graph_client=graph_client
    )
    results.append(distributor_result)
    
    # Add small delay
    await asyncio.sleep(1)
    
    # Send admin notification
    print("\n3. Sending admin notification...")
    admin_result = await send_admin_new_purchase_notice(
        customer_data=customer_data,
        purchase_data=purchase_data,
        graph_client=graph_client,
        admin_emails=admin_emails
    )
    results.append(admin_result)
    
    # ===========================================
    # 5. PRINT SUMMARY
    # ===========================================
    print(f"\n{'='*80}")
    print("📊 NOTIFICATION SUMMARY")
    print(f"{'='*80}")
    
    success_count = sum(1 for r in results if r.get("status") == "success")
    error_count = sum(1 for r in results if r.get("status") == "error")
    
    for result in results:
        if result.get("status") == "success":
            print(f"✅ {result.get('type', 'Unknown')}: Sent to {result.get('recipient', result.get('recipients', 'Unknown'))}")
        else:
            print(f"❌ {result.get('type', 'Unknown')}: Error - {result.get('error', 'Unknown error')}")
    
    print(f"\n📈 Total: {len(results)} notifications")
    print(f"✅ Successfully sent: {success_count}")
    print(f"❌ Failed: {error_count}")
    print(f"{'='*80}\n")
    
    return results

# ============================
# 5. SCRIPT ENTRY POINT
# ============================

if __name__ == "__main__":
    print("\n🚀 Starting Product Purchase Notification System...\n")
    
    try:
        # Run the notification campaign
        results = asyncio.run(send_all_notifications())
        
        print("✅ Notification campaign completed!\n")
        
        # Exit with appropriate code
        if all(r.get("status") == "success" for r in results):
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️ Process interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)