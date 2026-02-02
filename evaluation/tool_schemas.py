"""
Tool schema definitions and tool creation utilities.
Defines the OpenAI function schemas for all business functions.
"""

from azure.ai.projects.models import FunctionTool


FUNCTION_TOOL_SCHEMAS = {
    "check_order_status": {
        "name": "check_order_status",
        "description": "Check the status of a customer order by order number",
        "parameters": {
            "type": "object",
            "properties": {
                "order_number": {
                    "type": "string",
                    "description": "The order number (e.g., ORD-2024-5678)"
                }
            },
            "required": ["order_number"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    "process_refund": {
        "name": "process_refund",
        "description": "Process a refund for an order",
        "parameters": {
            "type": "object",
            "properties": {
                "order_number": {
                    "type": "string",
                    "description": "The order number to refund"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for the refund"
                }
            },
            "required": ["order_number", "reason"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    "cancel_order": {
        "name": "cancel_order",
        "description": "Cancel an order if it hasn't shipped yet",
        "parameters": {
            "type": "object",
            "properties": {
                "order_number": {
                    "type": "string",
                    "description": "The order number to cancel"
                }
            },
            "required": ["order_number"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    "send_email": {
        "name": "send_email",
        "description": "Send an email to a recipient",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {
                    "type": "string",
                    "description": "Email recipient address"
                },
                "subject": {
                    "type": "string",
                    "description": "Email subject"
                },
                "body": {
                    "type": "string",
                    "description": "Email body content"
                },
                "cc": {
                    "type": "string",
                    "description": "CC email address (optional)"
                }
            },
            "required": ["to", "subject", "body", "cc"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    "update_customer_profile_salesforce": {
        "name": "update_customer_profile_salesforce",
        "description": "Update customer profile in Salesforce CRM",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID (optional)"
                },
                "phone": {
                    "type": "string",
                    "description": "Phone number to update"
                },
                "email": {
                    "type": "string",
                    "description": "Email address to update"
                },
                "address": {
                    "type": "string",
                    "description": "Address to update"
                }
            },
            "required": ["customer_id", "phone", "email", "address"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    "get_customer_profile_crm": {
        "name": "get_customer_profile_crm",
        "description": "Retrieve customer profile from CRM system",
        "parameters": {
            "type": "object",
            "properties": {
                "customer_id": {
                    "type": "string",
                    "description": "Customer ID"
                },
                "email": {
                    "type": "string",
                    "description": "Customer email"
                }
            },
            "required": ["customer_id", "email"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    "create_support_ticket_erp": {
        "name": "create_support_ticket_erp",
        "description": "Create a support ticket in ERP system",
        "parameters": {
            "type": "object",
            "properties": {
                "issue_type": {
                    "type": "string",
                    "description": "Type of issue (e.g., technical, billing, shipping)"
                },
                "description": {
                    "type": "string",
                    "description": "Detailed description of the issue"
                },
                "priority": {
                    "type": "string",
                    "description": "Priority level: low, medium, or high"
                }
            },
            "required": ["issue_type", "description", "priority"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    "check_product_availability": {
        "name": "check_product_availability",
        "description": "Check if a product is in stock",
        "parameters": {
            "type": "object",
            "properties": {
                "product_name": {
                    "type": "string",
                    "description": "Name of the product"
                },
                "store_location": {
                    "type": "string",
                    "description": "Store location (Online, Seattle, New York)"
                }
            },
            "required": ["product_name", "store_location"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    "schedule_installation": {
        "name": "schedule_installation",
        "description": "Schedule product installation service",
        "parameters": {
            "type": "object",
            "properties": {
                "order_number": {
                    "type": "string",
                    "description": "Order number for installation"
                },
                "preferred_date": {
                    "type": "string",
                    "description": "Preferred installation date (YYYY-MM-DD format)"
                },
                "time_slot": {
                    "type": "string",
                    "description": "Preferred time slot: morning or afternoon"
                }
            },
            "required": ["order_number", "preferred_date", "time_slot"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    "process_warranty_claim": {
        "name": "process_warranty_claim",
        "description": "Process a warranty claim for a product",
        "parameters": {
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "description": "Product ID or serial number"
                },
                "issue_description": {
                    "type": "string",
                    "description": "Description of the issue with the product"
                }
            },
            "required": ["product_id", "issue_description"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}


def create_function_tools() -> list[FunctionTool]:
    """Create function tools from schemas."""
    tools = []
    for schema in FUNCTION_TOOL_SCHEMAS.values():
        tools.append(FunctionTool(
            name=schema["name"],
            parameters=schema["parameters"],
            description=schema["description"],
            strict=schema.get("strict", True),
        ))
    return tools
