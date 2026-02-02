"""
Business function implementations for Contoso Electronics customer service.
These functions simulate various business operations like order tracking,
refunds, CRM updates, etc.
"""

import json
from datetime import datetime


def check_order_status(order_number: str) -> dict:
    """Check the status of an order."""
    # Simulated order data
    orders = {
        "ORD-2024-5678": {
            "status": "In Transit",
            "items": [{"name": "Samsung 55-inch 4K Smart TV", "quantity": 1}],
            "tracking": "TRK-987654321",
            "estimated_delivery": "February 5, 2026",
            "location": "Distribution center, Seattle, WA",
            "order_date": "January 28, 2026",
            "total": "$708.48"
        },
        "ORD-2024-1234": {
            "status": "Delivered",
            "items": [{"name": "Sony WH-1000XM5 Headphones", "quantity": 1}],
            "tracking": "TRK-123456789",
            "estimated_delivery": "January 30, 2026",
            "location": "Delivered",
            "order_date": "January 25, 2026",
            "total": "$399.99"
        }
    }
    
    if order_number in orders:
        return orders[order_number]
    else:
        return {"error": "Order not found", "order_number": order_number}


def process_refund(order_number: str, reason: str = "") -> dict:
    """Process a refund for an order."""
    # Simulated refund processing
    order_data = check_order_status(order_number)
    
    if "error" in order_data:
        return {
            "success": False,
            "message": f"Order {order_number} not found in system",
            "refund_id": None
        }
    
    refund_id = f"RFD-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return {
        "success": True,
        "message": f"Refund processed successfully for order {order_number}",
        "refund_id": refund_id,
        "amount": order_data.get("total", "$0.00"),
        "processing_time": "5-7 business days",
        "reason": reason or "Customer request"
    }


def cancel_order(order_number: str) -> dict:
    """Cancel an order if it hasn't shipped yet."""
    order_data = check_order_status(order_number)
    
    if "error" in order_data:
        return {
            "success": False,
            "message": f"Order {order_number} not found"
        }
    
    if order_data["status"] in ["Shipped", "In Transit", "Delivered"]:
        return {
            "success": False,
            "message": f"Order {order_number} has already shipped. Please initiate a return instead.",
            "status": order_data["status"]
        }
    
    return {
        "success": True,
        "message": f"Order {order_number} has been canceled successfully",
        "refund_processing": "3-5 business days"
    }


def send_email(to: str, subject: str, body: str, cc: str = "") -> dict:
    """Send an email."""
    return {
        "success": True,
        "message": f"Email sent successfully to {to}",
        "message_id": f"MSG-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "to": to,
        "subject": subject,
        "sent_at": datetime.now().isoformat(),
        "cc": cc if cc else None
    }


def update_customer_profile_salesforce(customer_id: str = None, **updates) -> dict:
    """Update customer profile in Salesforce CRM."""
    updated_fields = []
    for field, value in updates.items():
        updated_fields.append(f"{field}: {value}")
    
    return {
        "success": True,
        "message": "Customer profile updated successfully in Salesforce",
        "customer_id": customer_id or f"SF-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "updated_fields": updated_fields,
        "synced_systems": ["Salesforce CRM", "Contoso Order Management", "Email Notification Service"],
        "timestamp": datetime.now().isoformat()
    }


def get_customer_profile_crm(customer_id: str = None, email: str = None) -> dict:
    """Retrieve customer profile from CRM system."""
    return {
        "customer_id": customer_id or "CRM-12345",
        "email": email or "customer@example.com",
        "name": "John Smith",
        "phone": "(555) 123-4567",
        "address": "123 Main Street, Seattle, WA 98101",
        "loyalty_tier": "Gold",
        "lifetime_value": "$2,450.00",
        "orders_count": 8,
        "last_order_date": "January 28, 2026"
    }


def create_support_ticket_erp(issue_type: str, description: str, priority: str = "medium") -> dict:
    """Create a support ticket in ERP system."""
    ticket_id = f"TKT-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return {
        "success": True,
        "ticket_id": ticket_id,
        "issue_type": issue_type,
        "description": description,
        "priority": priority,
        "status": "Open",
        "assigned_to": "Support Team",
        "created_at": datetime.now().isoformat(),
        "sla_response_time": "4 hours" if priority == "high" else "24 hours"
    }


def check_product_availability(product_name: str, store_location: str = "Online") -> dict:
    """Check product availability in inventory."""
    # Simulated inventory
    inventory = {
        "Samsung 55-inch 4K Smart TV": {"online": 45, "seattle": 12, "new_york": 8},
        "Sony WH-1000XM5 Headphones": {"online": 120, "seattle": 25, "new_york": 30},
        "Dell XPS 15 Laptop": {"online": 35, "seattle": 8, "new_york": 15},
    }
    
    for product, stock in inventory.items():
        if product_name.lower() in product.lower():
            return {
                "product": product,
                "available": True,
                "stock_levels": stock,
                "estimated_delivery": "2-3 business days" if store_location.lower() == "online" else "Same day pickup"
            }
    
    return {
        "product": product_name,
        "available": False,
        "message": "Product not found or out of stock"
    }


def schedule_installation(order_number: str, preferred_date: str, time_slot: str = "morning") -> dict:
    """Schedule product installation service."""
    return {
        "success": True,
        "confirmation_number": f"INST-{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "order_number": order_number,
        "scheduled_date": preferred_date,
        "time_slot": f"{time_slot.capitalize()} (8AM-12PM)" if time_slot == "morning" else f"{time_slot.capitalize()} (1PM-5PM)",
        "technician": "Contoso Certified Installer",
        "contact": "1-800-CONTOSO",
        "message": "Installation scheduled successfully. You will receive a confirmation email and SMS reminder 24 hours before."
    }


def process_warranty_claim(product_id: str, issue_description: str) -> dict:
    """Process a warranty claim."""
    claim_id = f"WRN-{datetime.now().strftime('%Y%m%d%H%M%S')}"
    return {
        "success": True,
        "claim_id": claim_id,
        "product_id": product_id,
        "issue": issue_description,
        "status": "Under Review",
        "next_steps": "Our warranty team will contact you within 24-48 hours to assess the claim",
        "estimated_resolution": "5-7 business days",
        "coverage_verified": True
    }


# Map function names to implementations
AVAILABLE_FUNCTIONS = {
    "check_order_status": check_order_status,
    "process_refund": process_refund,
    "cancel_order": cancel_order,
    "send_email": send_email,
    "update_customer_profile_salesforce": update_customer_profile_salesforce,
    "get_customer_profile_crm": get_customer_profile_crm,
    "create_support_ticket_erp": create_support_ticket_erp,
    "check_product_availability": check_product_availability,
    "schedule_installation": schedule_installation,
    "process_warranty_claim": process_warranty_claim,
}
