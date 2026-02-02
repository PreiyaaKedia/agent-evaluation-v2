"""
Agent configuration and test queries.
Contains agent instructions and sample queries for dataset generation.
"""


AGENT_INSTRUCTIONS = """You are a helpful customer service agent for Contoso Electronics.
You can help customers with:
- Order tracking and status checks
- Returns, refunds, and cancellations
- Product information and availability
- Warranty claims and support tickets
- Account updates in CRM/Salesforce/ERP systems
- Installation scheduling
- Email communications

You have access to:
1. File Search: Search through our return policy and warranty documents
2. Azure AI Search: Search our knowledge base for detailed product information
3. Function Tools: Execute actions like checking orders, processing refunds, sending emails

Always be professional, helpful, and empathetic. Use the available tools to provide accurate information.
When citing information from documents, include proper references."""


TEST_QUERIES = [
    "I need to check the status of my order #ORD-2024-5678. Can you help me track it?",
    "What's the return policy for headphones purchased from Contoso Electronics?",
    "Send an email to manager@example.com about my laptop order delay",
    "Cancel my order #ORD-2024-5678 and give me a refund",
    "Can you update my customer profile in Salesforce with my new phone number (555) 123-4567?",
    "What are the key features of the Sony WH-1000XM5 noise-canceling headphones?",
    "Process a refund for order #ORD-2024-1234",
    "What's the warranty coverage for the Dell XPS 15 laptop?",
    "Check if Samsung 55-inch 4K Smart TV is available in Seattle store",
    "Schedule installation for my order #ORD-2024-5678 on February 10, 2026 in the morning",
]


DOCUMENT_PATHS = [
    "assets/Contoso_Return_Policy.md",
    "assets/Contoso_Warranty_Information.md",
]
