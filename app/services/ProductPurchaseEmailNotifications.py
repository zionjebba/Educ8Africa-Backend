"""
Email Service for Product Purchases
Update: app/services/ProductPurchaseEmailNotifications.py
"""

from typing import Dict, List
from datetime import datetime


async def notify_product_purchase_confirmation(
    purchase_data: Dict,
    graph_client
) -> Dict:
    """
    Send purchase confirmation email to customer
    """
    try:
        customer = purchase_data["customer"]
        purchase = purchase_data["purchase"]
        
        # Format payment date
        payment_date = purchase["payment_date"]
        if isinstance(payment_date, datetime):
            formatted_date = payment_date.strftime("%B %d, %Y at %I:%M %p")
        else:
            formatted_date = payment_date
        
        # Build order summary
        order_summary = f"""
        <div style="background: #f8f9fa; padding: 20px; border-radius: 8px; margin: 20px 0;">
            <h3 style="color: #0a2463; margin-top: 0;">Order Summary</h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                        <strong>Product:</strong>
                    </td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6; text-align: right;">
                        {purchase["product_name"]}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                        <strong>Quantity:</strong>
                    </td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6; text-align: right;">
                        {purchase["quantity"]} unit(s)
                    </td>
                </tr>
                <tr>
                    <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6;">
                        <strong>Unit Price:</strong>
                    </td>
                    <td style="padding: 10px 0; border-bottom: 1px solid #dee2e6; text-align: right;">
                        GHS {purchase["unit_price"]:.2f}
                    </td>
                </tr>
                <tr>
                    <td style="padding: 15px 0; font-size: 18px;">
                        <strong>Total Amount:</strong>
                    </td>
                    <td style="padding: 15px 0; text-align: right; font-size: 18px; color: #0a2463;">
                        <strong>GHS {purchase["total_amount"]:.2f}</strong>
                    </td>
                </tr>
            </table>
        </div>
        """
        
        # Add distributor info if applicable
        distributor_info = ""
        if purchase.get("distributor_code"):
            distributor_name = purchase.get("distributor_name", "")
            distributor_commission = purchase.get("distributor_commission")
            
            distributor_info = f"""
            <div style="background: #d4edda; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #28a745;">
                <p style="margin: 0; color: #155724;">
                    <strong>✓ Distributor Discount Applied (10%):</strong> {purchase["distributor_code"]}<br>
                    {f'<small>Referred by: {distributor_name}</small>' if distributor_name else ''}
                    <br><small>You saved with this distributor code!</small>
                </p>
            </div>
            """
        
        # Customer notes
        notes_section = ""
        if purchase.get("notes"):
            notes_section = f"""
            <div style="background: #e7f3ff; padding: 15px; border-radius: 8px; margin: 20px 0;">
                <p style="margin: 0; color: #004085;">
                    <strong>Your Notes:</strong><br>
                    {purchase["notes"]}
                </p>
            </div>
            """
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #0a2463 0%, #1e4db7 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">Order Confirmed! 🎉</h1>
                <p style="color: #e0e0e0; margin: 10px 0 0 0;">Thank you for your purchase</p>
            </div>
            
            <div style="background: white; padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
                <p style="font-size: 16px; margin-top: 0;">Dear {customer["name"]},</p>
                
                <p>Your order has been successfully confirmed! We're excited to get your <strong>{purchase["product_name"]}</strong> to you.</p>
                
                {order_summary}
                
                <div style="background: #f8f9fa; padding: 15px; border-radius: 8px; margin: 20px 0;">
                    <h3 style="color: #0a2463; margin-top: 0;">Delivery Information</h3>
                    <p style="margin: 5px 0;"><strong>Institution:</strong> {customer["institution"]}</p>
                    <p style="margin: 5px 0;"><strong>Contact:</strong> {customer["phone"]}</p>
                    <p style="margin: 5px 0;"><strong>Email:</strong> {customer["email"]}</p>
                </div>
                
                {distributor_info}
                {notes_section}
                
                <div style="background: #e8f4f8; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #0a2463;">
                    <p style="margin: 0; color: #0a2463;">
                        <strong>Payment Reference:</strong> {purchase["payment_reference"]}<br>
                        <strong>Payment Date:</strong> {formatted_date}
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
                    © 2026 Ideotronix - Ideation Axis<br>
                    Empowering Innovation Through Electronics
                </p>
                <p style="margin: 15px 0 5px 0; color: #666; font-size: 12px;">
                    <a href="https://ideotronix.com" style="color: #0a2463; text-decoration: none;">Visit Our Website</a> | 
                    <a href="mailto:ideotronix@ideationaxis.com" style="color: #0a2463; text-decoration: none;">Contact Us</a>
                </p>
            </div>
        </body>
        </html>
        """
        
        # ✅ FIXED: Use correct method signature matching distributor emails
        result = await graph_client.send_email(
            to_emails=[customer["email"]],  # Changed from to_email to to_emails (list)
            subject=f"Order Confirmed - {purchase['product_name']} #{purchase['payment_reference']}",
            body_html=html_content,  # Changed from body to body_html
            department="products"
        )
        
        print(f"✅ Purchase confirmation email sent to {customer['email']}")
        return {"status": "sent", "email": customer["email"], "type": "purchase_confirmation"}
        
    except Exception as e:
        print(f"❌ Error sending purchase confirmation email: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {"status": "failed", "error": str(e)}


async def notify_admin_new_product_purchase(
    purchase_data: Dict,
    graph_client,
    admin_emails: List[str]
) -> Dict:
    """
    Send new purchase notification to admin team
    """
    try:
        customer = purchase_data["customer"]
        purchase = purchase_data["purchase"]
        
        # Format payment date
        payment_date = purchase["payment_date"]
        if isinstance(payment_date, datetime):
            formatted_date = payment_date.strftime("%B %d, %Y at %I:%M %p")
        else:
            formatted_date = payment_date
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: #0a2463; padding: 20px; text-align: center; border-radius: 8px 8px 0 0;">
                <h2 style="color: white; margin: 0;">🛒 New Product Order</h2>
            </div>
            
            <div style="background: white; padding: 25px; border: 1px solid #e0e0e0;">
                <div style="background: #28a745; color: white; padding: 15px; border-radius: 5px; margin-bottom: 20px; text-align: center;">
                    <h3 style="margin: 0;">Payment Confirmed</h3>
                    <p style="margin: 5px 0 0 0; font-size: 14px;">Order ready for processing</p>
                </div>
                
                <h3 style="color: #0a2463; border-bottom: 2px solid #0a2463; padding-bottom: 10px;">Order Details</h3>
                <table style="width: 100%; margin: 15px 0;">
                    <tr>
                        <td style="padding: 8px 0;"><strong>Product:</strong></td>
                        <td style="padding: 8px 0;">{purchase["product_name"]}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;"><strong>Quantity:</strong></td>
                        <td style="padding: 8px 0;">{purchase["quantity"]} unit(s)</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;"><strong>Unit Price:</strong></td>
                        <td style="padding: 8px 0;">GHS {purchase["unit_price"]:.2f}</td>
                    </tr>
                    <tr style="background: #f8f9fa;">
                        <td style="padding: 12px 8px; font-size: 16px;"><strong>Total Amount:</strong></td>
                        <td style="padding: 12px 8px; font-size: 16px; color: #28a745;"><strong>GHS {purchase["total_amount"]:.2f}</strong></td>
                    </tr>
                </table>
                
                <h3 style="color: #0a2463; border-bottom: 2px solid #0a2463; padding-bottom: 10px; margin-top: 30px;">Customer Information</h3>
                <table style="width: 100%; margin: 15px 0;">
                    <tr>
                        <td style="padding: 8px 0;"><strong>Name:</strong></td>
                        <td style="padding: 8px 0;">{customer["name"]}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;"><strong>Email:</strong></td>
                        <td style="padding: 8px 0;"><a href="mailto:{customer['email']}" style="color: #0a2463;">{customer["email"]}</a></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;"><strong>Phone:</strong></td>
                        <td style="padding: 8px 0;"><a href="tel:{customer['phone']}" style="color: #0a2463;">{customer["phone"]}</a></td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;"><strong>Institution:</strong></td>
                        <td style="padding: 8px 0;">{customer["institution"]}</td>
                    </tr>
                </table>
                
                <h3 style="color: #0a2463; border-bottom: 2px solid #0a2463; padding-bottom: 10px; margin-top: 30px;">Payment Information</h3>
                <table style="width: 100%; margin: 15px 0;">
                    <tr>
                        <td style="padding: 8px 0;"><strong>Reference:</strong></td>
                        <td style="padding: 8px 0; font-family: monospace;">{purchase["payment_reference"]}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;"><strong>Payment Date:</strong></td>
                        <td style="padding: 8px 0;">{formatted_date}</td>
                    </tr>
                    <tr>
                        <td style="padding: 8px 0;"><strong>Status:</strong></td>
                        <td style="padding: 8px 0;"><span style="background: #28a745; color: white; padding: 3px 10px; border-radius: 3px; font-size: 12px;">PAID</span></td>
                    </tr>
                </table>
                
                {f'''
                <div style="background: #d4edda; padding: 15px; border-radius: 5px; margin: 20px 0; border-left: 4px solid #28a745;">
                    <p style="margin: 0 0 5px 0; color: #155724;">
                        <strong>✓ Distributor Code Applied (10% discount):</strong> {purchase["distributor_code"]}
                    </p>
                    {f'<p style="margin: 5px 0 0 0; color: #155724; font-size: 14px;">Referred by: {purchase["distributor_name"]}</p>' if purchase.get("distributor_name") else ''}
                    {f'<p style="margin: 5px 0 0 0; color: #155724; font-size: 14px;">Commission: GHS {purchase["distributor_commission"]:.2f}</p>' if purchase.get("distributor_commission") else ''}
                </div>
                ''' if purchase.get("distributor_code") else ""}
                
                {f'''
                <div style="background: #e7f3ff; padding: 15px; border-radius: 5px; margin: 20px 0;">
                    <p style="margin: 0; color: #004085;">
                        <strong>Customer Notes:</strong><br>
                        {purchase["notes"]}
                    </p>
                </div>
                ''' if purchase.get("notes") else ""}
                
                <div style="background: #fff9e6; padding: 20px; border-radius: 5px; margin: 25px 0; border-left: 4px solid #ffc107;">
                    <h4 style="margin-top: 0; color: #856404;">⚠️ Action Required</h4>
                    <ul style="margin: 10px 0; padding-left: 20px; color: #856404;">
                        <li>Verify payment in Paystack dashboard</li>
                        <li>Prepare order for shipment</li>
                        <li>Update inventory records</li>
                        <li>Contact customer for delivery coordination</li>
                        <li>Process distributor commission if applicable</li>
                    </ul>
                </div>
                
                <div style="text-align: center; margin-top: 30px;">
                    <a href="mailto:{customer['email']}" style="display: inline-block; background: #0a2463; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 5px;">Contact Customer</a>
                    <a href="https://dashboard.paystack.com" target="_blank" style="display: inline-block; background: #28a745; color: white; padding: 12px 25px; text-decoration: none; border-radius: 5px; margin: 5px;">View in Paystack</a>
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
        
        # ✅ FIXED: Use correct method signature
        result = await graph_client.send_admin_notification(
            admin_emails=admin_emails,
            subject=f"🛒 New Order: {purchase['product_name']} - GHS {purchase['total_amount']:.2f}",
            template_html=html_content,
            template_vars={},  # Already formatted in template
            reply_to_applicant=customer["email"]
        )
        
        print(f"✅ Admin notification sent for purchase {purchase['payment_reference']}")
        return {"status": "sent", "results": result}
        
    except Exception as e:
        print(f"❌ Error sending admin notification: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {"status": "failed", "error": str(e)}
    
async def notify_distributor_commission_earned(
    purchase_data: Dict,
    graph_client
) -> Dict:
    """
    Send commission notification to distributor
    """
    try:
        customer = purchase_data["customer"]
        purchase = purchase_data["purchase"]
        
        # Only send if distributor info exists
        if not purchase.get("distributor_email"):
            return {"status": "skipped", "reason": "No distributor email"}
        
        # Format payment date
        payment_date = purchase["payment_date"]
        if isinstance(payment_date, datetime):
            formatted_date = payment_date.strftime("%B %d, %Y at %I:%M %p")
        else:
            formatted_date = payment_date
        
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
        </head>
        <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #28a745 0%, #20c997 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">💰 Commission Earned!</h1>
                <p style="color: #e0e0e0; margin: 10px 0 0 0;">Your distributor code was used</p>
            </div>
            
            <div style="background: white; padding: 30px; border: 1px solid #e0e0e0; border-top: none;">
                <p style="font-size: 16px; margin-top: 0;">Dear {purchase["distributor_name"]},</p>
                
                <p>Great news! Your distributor code <strong>{purchase["distributor_code"]}</strong> was used for a purchase, and you've earned a commission.</p>
                
                <div style="background: #d4edda; padding: 25px; border-radius: 8px; margin: 25px 0; text-align: center; border: 2px solid #28a745;">
                    <h2 style="color: #155724; margin: 0 0 10px 0; font-size: 32px;">GHS {purchase["distributor_commission"]:.2f}</h2>
                    <p style="color: #155724; margin: 0; font-size: 18px;">Commission Earned</p>
                </div>
                
                <h3 style="color: #28a745; border-bottom: 2px solid #28a745; padding-bottom: 10px;">Sale Details</h3>
                <table style="width: 100%; margin: 15px 0; border-collapse: collapse;">
                    <tr style="background: #f8f9fa;">
                        <td style="padding: 12px 8px; border-bottom: 1px solid #dee2e6;"><strong>Product:</strong></td>
                        <td style="padding: 12px 8px; border-bottom: 1px solid #dee2e6; text-align: right;">{purchase["product_name"]}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 8px; border-bottom: 1px solid #dee2e6;"><strong>Quantity:</strong></td>
                        <td style="padding: 12px 8px; border-bottom: 1px solid #dee2e6; text-align: right;">{purchase["quantity"]} unit(s)</td>
                    </tr>
                    <tr style="background: #f8f9fa;">
                        <td style="padding: 12px 8px; border-bottom: 1px solid #dee2e6;"><strong>Unit Price:</strong></td>
                        <td style="padding: 12px 8px; border-bottom: 1px solid #dee2e6; text-align: right;">GHS {purchase["unit_price"]:.2f}</td>
                    </tr>
                    <tr>
                        <td style="padding: 12px 8px; border-bottom: 1px solid #dee2e6;"><strong>Sale Total:</strong></td>
                        <td style="padding: 12px 8px; border-bottom: 1px solid #dee2e6; text-align: right;">GHS {purchase["total_amount"]:.2f}</td>
                    </tr>
                    <tr style="background: #d4edda;">
                        <td style="padding: 15px 8px; font-size: 16px;"><strong>Your Commission:</strong></td>
                        <td style="padding: 15px 8px; text-align: right; font-size: 16px; color: #28a745;"><strong>GHS {purchase["distributor_commission"]:.2f}</strong></td>
                    </tr>
                </table>
                
                <h3 style="color: #28a745; border-bottom: 2px solid #28a745; padding-bottom: 10px; margin-top: 30px;">Customer Information</h3>
                <table style="width: 100%; margin: 15px 0;">
                    <tr style="background: #f8f9fa;">
                        <td style="padding: 10px 8px;"><strong>Name:</strong></td>
                        <td style="padding: 10px 8px; text-align: right;">{customer["name"]}</td>
                    </tr>
                    <tr>
                        <td style="padding: 10px 8px;"><strong>Institution:</strong></td>
                        <td style="padding: 10px 8px; text-align: right;">{customer["institution"]}</td>
                    </tr>
                    <tr style="background: #f8f9fa;">
                        <td style="padding: 10px 8px;"><strong>Contact:</strong></td>
                        <td style="padding: 10px 8px; text-align: right;">{customer["phone"]}</td>
                    </tr>
                </table>
                
                <div style="background: #e7f3ff; padding: 15px; border-radius: 8px; margin: 20px 0; border-left: 4px solid #0a2463;">
                    <p style="margin: 0; color: #004085;">
                        <strong>Transaction Reference:</strong> {purchase["payment_reference"]}<br>
                        <strong>Sale Date:</strong> {formatted_date}
                    </p>
                </div>
                
                <div style="background: #fff9e6; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #ffc107;">
                    <h3 style="color: #856404; margin-top: 0;">📊 Commission Summary</h3>
                    <p style="margin: 10px 0; color: #856404;">
                        This commission has been automatically added to your distributor account. You can view your complete earnings history and request payouts through your distributor dashboard.
                    </p>
                </div>
                
                <div style="background: #d1ecf1; padding: 20px; border-radius: 8px; margin: 25px 0; border-left: 4px solid #17a2b8;">
                    <h3 style="color: #0c5460; margin-top: 0;">💡 Keep Growing Your Sales</h3>
                    <ul style="margin: 10px 0; padding-left: 20px; color: #0c5460;">
                        <li style="margin: 8px 0;">Share your distributor code with more potential customers</li>
                        <li style="margin: 8px 0;">Promote Ideotronix products in your network</li>
                        <li style="margin: 8px 0;">Earn 10% commission on every sale using your code</li>
                        <li style="margin: 8px 0;">Track your performance in the distributor dashboard</li>
                    </ul>
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
                    © 2026 Ideotronix - Distributor Program<br>
                    Questions? Contact us at <a href="mailto:distributors@ideationaxis.com" style="color: #0a2463;">distributors@ideationaxis.com</a>
                </p>
            </div>
        </body>
        </html>
        """
        
        result = await graph_client.send_email(
            to_emails=[purchase["distributor_email"]],
            subject=f"💰 Commission Earned: GHS {purchase['distributor_commission']:.2f} - {purchase['product_name']}",
            body_html=html_content,
            department="distributors"
        )
        
        print(f"✅ Distributor commission notification sent to {purchase['distributor_email']}")
        return {"status": "sent", "email": purchase["distributor_email"], "type": "distributor_commission"}
        
    except Exception as e:
        print(f"❌ Error sending distributor commission email: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return {"status": "failed", "error": str(e)}


