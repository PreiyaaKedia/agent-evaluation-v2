# pylint: disable=line-too-long,useless-suppression
# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

"""
DESCRIPTION:
    Comprehensive end-to-end agent evaluation script using Azure AI Projects SDK v2.
    This script:
    1. Executes agents with function tools end-to-end
    2. Captures real agent responses and tool calls
    3. Creates a dataset from the captured data
    4. Runs multiple agentic evaluators using the dataset ID
    
    Evaluators run:
    - Tool-related: tool_call_accuracy, tool_selection, tool_input_accuracy, 
                    tool_output_utilization, tool_call_success
    - Task-related: task_completion, task_adherence
    - Quality-related: coherence, fluency, relevance, groundedness, intent_resolution

USAGE:
    python comprehensive_agent_evaluation.py

    Before running:
    pip install "azure-ai-projects>=2.0.0b1" python-dotenv

    Set these environment variables:
    1) AZURE_AI_PROJECT_ENDPOINT - Required
    2) AZURE_AI_MODEL_DEPLOYMENT_NAME - Required (for evaluation)
    3) DATASET_NAME - Optional (default: auto-generated)
    4) DATASET_VERSION - Optional (default: "1")
"""

import os
import json
import time
from pprint import pprint
from datetime import datetime
from dotenv import load_dotenv

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool, DatasetVersion
from openai.types.evals.create_eval_jsonl_run_data_source_param import (
    CreateEvalJSONLRunDataSourceParam,
    SourceFileID,
)
from openai.types.eval_create_params import DataSourceConfigCustom
from openai.types.responses.response_input_param import FunctionCallOutput

load_dotenv()


# ========================================
# Function Implementations
# ========================================

def get_weather(location: str) -> dict:
    """Get weather information for a location."""
    weather_data = {
        "New York": {"temperature": "72°F", "condition": "Sunny", "humidity": "45%"},
        "Seattle": {"temperature": "58°F", "condition": "Rainy", "humidity": "80%"},
        "San Francisco": {"temperature": "65°F", "condition": "Foggy", "humidity": "70%"},
        "Chicago": {"temperature": "55°F", "condition": "Cloudy", "humidity": "60%"},
    }
    return weather_data.get(location, {"temperature": "70°F", "condition": "Clear", "humidity": "50%"})


def search_database(query: str, table: str) -> dict:
    """Search database for information."""
    return {
        "results": [
            {"id": 1, "data": f"Result 1 for '{query}' in {table}"},
            {"id": 2, "data": f"Result 2 for '{query}' in {table}"},
        ],
        "count": 2,
    }


def send_email(to: str, subject: str, body: str) -> dict:
    """Send an email."""
    return {
        "status": "sent",
        "message": f"Email successfully sent to {to}",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


AVAILABLE_FUNCTIONS = {
    "get_weather": get_weather,
    "search_database": search_database,
    "send_email": send_email,
}


# ========================================
# Tool Schemas
# ========================================

TOOL_SCHEMAS = {
    "weather": {
        "name": "get_weather",
        "description": "Get weather information for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {"type": "string", "description": "The city name"}
            },
            "required": ["location"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    "database": {
        "name": "search_database",
        "description": "Search database for information",
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "table": {"type": "string", "description": "Table name to search"}
            },
            "required": ["query", "table"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    "email": {
        "name": "send_email",
        "description": "Send an email",
        "parameters": {
            "type": "object",
            "properties": {
                "to": {"type": "string", "description": "Email recipient"},
                "subject": {"type": "string", "description": "Email subject"},
                "body": {"type": "string", "description": "Email body"}
            },
            "required": ["to", "subject", "body"],
            "additionalProperties": False,
        },
        "strict": True,
    },
}


def create_function_tool(schema: dict) -> FunctionTool:
    """Create a FunctionTool from a schema definition."""
    return FunctionTool(
        name=schema["name"],
        parameters=schema["parameters"],
        description=schema["description"],
        strict=schema.get("strict", True),
    )


def schema_to_eval_format(schema: dict) -> dict:
    """Convert tool schema to evaluation format."""
    return {
        "type": "function",
        "name": schema["name"],
        "description": schema["description"],
        "parameters": schema["parameters"],
    }


def extract_tool_calls_from_response(response) -> list:
    """Extract tool calls from SDK v2 Response object."""
    tool_calls = []
    for item in response.output:
        if hasattr(item, 'type') and item.type == "function_call":
            tool_calls.append({
                "type": "tool_call",
                "tool_call_id": item.call_id,
                "name": item.name,
                "arguments": json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments,
            })
    return tool_calls


def convert_response_to_conversation_format(response) -> list:
    """Convert SDK v2 Response object to conversation format for evaluation."""
    conversation = []
    for item in response.output:
        if hasattr(item, 'type'):
            if item.type == "function_call":
                conversation.append({
                    "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(response.created_at)),
                    "run_id": response.id,
                    "role": "assistant",
                    "content": [{
                        "type": "tool_call",
                        "tool_call_id": item.call_id,
                        "name": item.name,
                        "arguments": json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments,
                    }],
                })
            elif item.type == "azure_ai_search_call":
                # Azure AI Search tool call
                conversation.append({
                    "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(response.created_at)),
                    "run_id": response.id,
                    "role": "assistant",
                    "content": [{
                        "type": "azure_ai_search_call",
                        "call_id": item.call_id if hasattr(item, 'call_id') else item.id,
                        "arguments": item.arguments if hasattr(item, 'arguments') else "",
                    }],
                })
            elif item.type == "file_search_call":
                # File Search tool call
                conversation.append({
                    "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(response.created_at)),
                    "run_id": response.id,
                    "role": "assistant",
                    "content": [{
                        "type": "file_search_call",
                        "queries": item.queries if hasattr(item, 'queries') else [],
                    }],
                })
            elif item.type == "message":
                message_content = []
                if hasattr(item, 'content'):
                    for content_item in item.content:
                        if hasattr(content_item, 'type') and content_item.type == "output_text":
                            message_content.append({
                                "type": "text",
                                "text": content_item.text,
                            })
                if message_content:
                    conversation.append({
                        "createdAt": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(response.created_at)),
                        "run_id": response.id,
                        "role": "assistant",
                        "content": message_content,
                    })
    return conversation


def extract_context_from_response(response) -> str:
    """
    Extract context from response, including:
    - File Search citations (AnnotationFileCitation)
    - Azure AI Search citations (AnnotationURLCitation)
    - File search queries
    - Azure AI Search queries
    This is crucial for groundedness evaluation.
    """
    context_parts = []
    search_queries = []
    
    for item in response.output:
        # Extract queries from File Search
        if hasattr(item, 'type') and item.type == "file_search_call":
            if hasattr(item, 'queries') and item.queries:
                search_queries.extend(item.queries)
                context_parts.append(f"File search queries: {', '.join(item.queries)}")
        
        # Extract queries from Azure AI Search
        if hasattr(item, 'type') and item.type == "azure_ai_search_call":
            if hasattr(item, 'arguments'):
                try:
                    args = json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments
                    if 'query' in args:
                        search_queries.append(args['query'])
                        context_parts.append(f"Azure AI Search query: {args['query']}")
                except:
                    pass
        
        # Extract context from message content with annotations
        if hasattr(item, 'type') and item.type == "message":
            if hasattr(item, 'content'):
                for content_item in item.content:
                    if hasattr(content_item, 'type') and content_item.type == "output_text":
                        # Extract annotations (citations)
                        if hasattr(content_item, 'annotations') and content_item.annotations:
                            for annotation in content_item.annotations:
                                if hasattr(annotation, 'type'):
                                    # File citation annotation (from File Search)
                                    if annotation.type == "file_citation":
                                        citation_text = f"[File: {annotation.file_id}"
                                        if hasattr(annotation, 'filename'):
                                            citation_text += f" ({annotation.filename})"
                                        if hasattr(annotation, 'text'):
                                            citation_text += f" - {annotation.text}"
                                        citation_text += "]"
                                        context_parts.append(citation_text)
                                    
                                    # URL citation annotation (from Azure AI Search)
                                    elif annotation.type == "url_citation":
                                        citation_text = f"[Source: {annotation.title if hasattr(annotation, 'title') else 'Unknown'}"
                                        if hasattr(annotation, 'url'):
                                            citation_text += f" - {annotation.url}"
                                        citation_text += "]"
                                        context_parts.append(citation_text)
                                    
                                    # File path annotation
                                    elif annotation.type == "file_path":
                                        if hasattr(annotation, 'file_path'):
                                            context_parts.append(f"[Referenced file: {annotation.file_path.file_id}]")
                        
                        # Also capture the text itself as context
                        if hasattr(content_item, 'text') and content_item.text:
                            context_parts.append(content_item.text)
    
    return " ".join(context_parts) if context_parts else ""


def execute_agent_with_tools(client, agent_name, query, available_functions=None, conversation_id=None):
    """
    Execute an agent query and handle function calls end-to-end.
    Also handles file search tools and extracts context for groundedness evaluation.
    """
    if available_functions is None:
        available_functions = AVAILABLE_FUNCTIONS
    
    print(f"\n{'='*60}")
    print(f"Executing: {query}")
    print(f"{'='*60}")
    
    # Create request with optional conversation for file search
    request_params = {
        "input": query,
        "extra_body": {"agent": {"name": agent_name, "type": "agent_reference"}},
    }
    if conversation_id:
        request_params["conversation"] = conversation_id
    
    initial_response = client.responses.create(**request_params)
    
    print(f"Status: {initial_response.status}")
    
    input_list = []
    tool_calls_made = []
    function_results = {}
    context_extracted = ""
    
    # Extract context from file search (for groundedness evaluation)
    context_extracted = extract_context_from_response(initial_response)
    if context_extracted:
        print(f"  → Context extracted from file search/annotations")
    
    for item in initial_response.output:
        if hasattr(item, 'type') and item.type == "function_call":
            print(f"  → Function call: {item.name}({item.arguments})")
            
            tool_calls_made.append({
                "type": "tool_call",
                "tool_call_id": item.call_id,
                "name": item.name,
                "arguments": json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments,
            })
            
            if item.name in available_functions:
                function_to_call = available_functions[item.name]
                args = json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments
                
                try:
                    result = function_to_call(**args)
                    print(f"    Result: {result}")
                    function_results[item.call_id] = result
                    input_list.append(
                        FunctionCallOutput(
                            type="function_call_output",
                            call_id=item.call_id,
                            output=json.dumps(result),
                        )
                    )
                except Exception as e:
                    print(f"    Error: {e}")
                    input_list.append(
                        FunctionCallOutput(
                            type="function_call_output",
                            call_id=item.call_id,
                            output=json.dumps({"error": str(e)}),
                        )
                    )
    
    final_response = None
    if input_list:
        request_params["input"] = input_list
        request_params["previous_response_id"] = initial_response.id
        final_response = client.responses.create(**request_params)
        print(f"Final response: {final_response.output_text}")
        
        # Extract additional context from final response
        final_context = extract_context_from_response(final_response)
        if final_context:
            context_extracted = f"{context_extracted} {final_context}".strip()
    else:
        print(f"Direct response: {initial_response.output_text}")
    
    return initial_response, final_response, tool_calls_made, function_results, context_extracted


# ========================================
# Evaluator Configurations
# ========================================

# Schema mappings for each evaluator
EVALUATOR_SCHEMAS = {
    "tool_call_accuracy": {
        "properties": {
            "query": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
            "tool_definitions": {"anyOf": [{"type": "object"}, {"type": "array", "items": {"type": "object"}}]},
            "tool_calls": {"anyOf": [{"type": "object"}, {"type": "array", "items": {"type": "object"}}]},
            "response": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
        },
        "required": ["query", "tool_definitions"],
    },
    "tool_selection": {
        "properties": {
            "query": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
            "response": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
            "tool_calls": {"anyOf": [{"type": "object"}, {"type": "array", "items": {"type": "object"}}]},
            "tool_definitions": {"anyOf": [{"type": "object"}, {"type": "array", "items": {"type": "object"}}]},
        },
        "required": ["query", "response", "tool_definitions"],
    },
    "tool_input_accuracy": {
        "properties": {
            "query": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
            "response": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
            "tool_definitions": {"anyOf": [{"type": "object"}, {"type": "array", "items": {"type": "object"}}]},
        },
        "required": ["query", "response", "tool_definitions"],
    },
    "tool_output_utilization": {
        "properties": {
            "query": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
            "response": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
            "tool_definitions": {"anyOf": [{"type": "object"}, {"type": "array", "items": {"type": "object"}}]},
        },
        "required": ["query", "response"],
    },
    "tool_call_success": {
        "properties": {
            "tool_definitions": {"anyOf": [{"type": "object"}, {"type": "array", "items": {"type": "object"}}]},
            "response": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
        },
        "required": ["response"],
    },
    "task_completion": {
        "properties": {
            "query": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
            "response": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
            "tool_definitions": {"anyOf": [{"type": "object"}, {"type": "array", "items": {"type": "object"}}]},
        },
        "required": ["query", "response"],
    },
    "task_adherence": {
        "properties": {
            "query": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
            "response": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
            "tool_definitions": {"anyOf": [{"type": "object"}, {"type": "array", "items": {"type": "object"}}]},
        },
        "required": ["query", "response"],
    },
    "coherence": {
        "properties": {
            "query": {"type": "string"},
            "response": {"type": "string"}
        },
        "required": ["query", "response"],
    },
    "fluency": {
        "properties": {
            "query": {"type": "string"},
            "response": {"type": "string"}
        },
        "required": ["response"],
    },
    "relevance": {
        "properties": {
            "query": {"type": "string"},
            "response": {"type": "string"}
        },
        "required": ["query", "response"],
    },
    "groundedness": {
        "properties": {
            "context": {"type": "string"},
            "query": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
            "response": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
            "tool_definitions": {"anyOf": [{"type": "string"}, {"type": "object"}, {"type": "array", "items": {"type": "object"}}]},
        },
        "required": ["response"],
    },
    "intent_resolution": {
        "properties": {
            "query": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
            "response": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
            "tool_definitions": {"anyOf": [{"type": "object"}, {"type": "array", "items": {"type": "object"}}]},
        },
        "required": ["query", "response"],
    },
}

# Data mappings for each evaluator
EVALUATOR_DATA_MAPPINGS = {
    "tool_call_accuracy": {
        "query": "{{item.query}}",
        "tool_definitions": "{{item.tool_definitions}}",
        "tool_calls": "{{item.tool_calls}}",
        "response": "{{item.response}}",
    },
    "tool_selection": {
        "query": "{{item.query}}",
        "response": "{{item.response}}",
        "tool_calls": "{{item.tool_calls}}",
        "tool_definitions": "{{item.tool_definitions}}",
    },
    "tool_input_accuracy": {
        "query": "{{item.query}}",
        "response": "{{item.response}}",
        "tool_definitions": "{{item.tool_definitions}}",
    },
    "tool_output_utilization": {
        "query": "{{item.query}}",
        "response": "{{item.response}}",
        "tool_definitions": "{{item.tool_definitions}}",
    },
    "tool_call_success": {
        "tool_definitions": "{{item.tool_definitions}}",
        "response": "{{item.response}}",
    },
    "task_completion": {
        "query": "{{item.query}}",
        "response": "{{item.response}}",
        "tool_definitions": "{{item.tool_definitions}}",
    },
    "task_adherence": {
        "query": "{{item.query}}",
        "response": "{{item.response}}",
        "tool_definitions": "{{item.tool_definitions}}",
    },
    "coherence": {
        "query": "{{item.query}}",
        "response": "{{item.response}}",
    },
    "fluency": {
        "query": "{{item.query}}",
        "response": "{{item.response}}",
    },
    "relevance": {
        "query": "{{item.query}}",
        "response": "{{item.response}}",
    },
    "groundedness": {
        "context": "{{item.context}}",
        "query": "{{item.query}}",
        "response": "{{item.response}}",
        "tool_definitions": "{{item.tool_definitions}}",
    },
    "intent_resolution": {
        "query": "{{item.query}}",
        "response": "{{item.response}}",
        "tool_definitions": "{{item.tool_definitions}}",
    },
    "tool_output_utilization": {
        "query": "{{item.query}}",
        "response": "{{item.response}}",
        "tool_definitions": "{{item.tool_definitions}}",
    },
}


def get_unified_data_source_config() -> DataSourceConfigCustom:
    """Get a unified data source config that supports all evaluators."""
    # Combine all unique properties from all evaluators
    all_properties = {
        "query": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
        "response": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
        "context": {"type": "string"},
        "tool_definitions": {"anyOf": [{"type": "string"}, {"type": "object"}, {"type": "array", "items": {"type": "object"}}]},
        "tool_calls": {"anyOf": [{"type": "object"}, {"type": "array", "items": {"type": "object"}}]},
        "ground_truth": {"type": "string"},
    }
    
    return DataSourceConfigCustom({
        "type": "custom",
        "item_schema": {
            "type": "object",
            "properties": all_properties,
            "required": [],
        },
        "include_sample_schema": True,
    })


def build_testing_criteria(evaluator_names: list[str], model_deployment_name: str) -> list[dict]:
    """Build testing criteria for multiple evaluators."""
    testing_criteria = []
    
    for evaluator_name in evaluator_names:
        if evaluator_name not in EVALUATOR_DATA_MAPPINGS:
            print(f"Warning: Unknown evaluator '{evaluator_name}', skipping...")
            continue
        
        testing_criteria.append({
            "type": "azure_ai_evaluator",
            "name": evaluator_name,
            "evaluator_name": f"builtin.{evaluator_name}",
            "initialization_parameters": {"deployment_name": model_deployment_name},
            "data_mapping": EVALUATOR_DATA_MAPPINGS[evaluator_name],
        })
    
    return testing_criteria


def get_evaluator_configs(model_deployment_name: str) -> dict:
    """
    DEPRECATED: Use build_testing_criteria() instead.
    Kept for backward compatibility.
    """
    # This function is no longer needed with the new pattern
    # but keeping it for reference
    pass


def main():
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", os.environ.get("AZURE_EXISTING_AIPROJECT_ENDPOINT"))
    model_deployment_name = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4.1")
    dataset_name = os.environ.get("DATASET_NAME", f"agent-eval-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}")
    dataset_version = os.environ.get("DATASET_VERSION", "1")
    
    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=endpoint, credential=credential) as project_client,
        project_client.get_openai_client() as client,
    ):
        print("\n" + "="*80)
        print("STEP 1: Execute Agents and Capture Data")
        print("="*80)
        
        # Create agents
        weather_tool = create_function_tool(TOOL_SCHEMAS["weather"])
        database_tool = create_function_tool(TOOL_SCHEMAS["database"])
        email_tool = create_function_tool(TOOL_SCHEMAS["email"])
        
        weather_agent = project_client.agents.create_version(
            agent_name="WeatherAgent",
            definition=PromptAgentDefinition(
                model=model_deployment_name,
                instructions="You are a helpful assistant that can check weather information.",
                tools=[weather_tool],
            ),
        )
        
        multi_tool_agent = project_client.agents.create_version(
            agent_name="MultiToolAgent",
            definition=PromptAgentDefinition(
                model=model_deployment_name,
                instructions="You are a helpful assistant that can search databases and send emails.",
                tools=[database_tool, email_tool],
            ),
        )
        
        # Execute test cases
        test_cases = []
        
        # Test Case 1: Simple weather query
        query1 = "What's the weather like in New York?"
        initial_resp1, final_resp1, tool_calls1, _, context1 = execute_agent_with_tools(client, weather_agent.name, query1)
        tool_definitions1 = [schema_to_eval_format(TOOL_SCHEMAS["weather"])]
        response1_conv = convert_response_to_conversation_format(initial_resp1)
        if final_resp1:
            response1_conv.extend(convert_response_to_conversation_format(final_resp1))
        
        test_cases.append({
            "query": query1,
            "response": response1_conv,
            "tool_definitions": tool_definitions1,
            "tool_calls": tool_calls1 if tool_calls1 else None,
            "context": context1 or "Weather information for major cities",
        })
        
        # Test Case 2: Multiple tool calls
        query2 = "Search for customer orders in the orders table and send an email to customer@example.com with subject 'Order Update' and body 'Your order has been processed'"
        initial_resp2, final_resp2, tool_calls2, _, context2 = execute_agent_with_tools(client, multi_tool_agent.name, query2)
        tool_definitions2 = [schema_to_eval_format(TOOL_SCHEMAS["database"]), schema_to_eval_format(TOOL_SCHEMAS["email"])]
        response2_conv = convert_response_to_conversation_format(initial_resp2)
        if final_resp2:
            response2_conv.extend(convert_response_to_conversation_format(final_resp2))
        
        test_cases.append({
            "query": query2,
            "response": response2_conv,
            "tool_definitions": tool_definitions2,
            "tool_calls": tool_calls2 if tool_calls2 else None,
            "context": context2 or "Customer order management system",
        })
        
        # Test Case 3: Seattle weather
        query3 = "What's the weather in Seattle?"
        initial_resp3, final_resp3, tool_calls3, _, context3 = execute_agent_with_tools(client, weather_agent.name, query3)
        response3_conv = convert_response_to_conversation_format(initial_resp3)
        if final_resp3:
            response3_conv.extend(convert_response_to_conversation_format(final_resp3))
        
        test_cases.append({
            "query": query3,
            "response": response3_conv,
            "tool_definitions": tool_definitions1,
            "tool_calls": tool_calls3 if tool_calls3 else None,
            "context": context3 or "Weather information for Seattle",
        })
        
        # Test Case 4: No tool call
        query4 = "Hello! Can you tell me what tools you have available?"
        initial_resp4, final_resp4, tool_calls4, _, context4 = execute_agent_with_tools(client, weather_agent.name, query4)
        
        test_cases.append({
            "query": query4,
            "response": initial_resp4.output_text or "",
            "tool_definitions": tool_definitions1,
            "tool_calls": tool_calls4 if tool_calls4 else None,
            "context": context4 or "General conversation about available tools",
        })
        
        # Clean up agents
        project_client.agents.delete_version(agent_name=weather_agent.name, agent_version=weather_agent.version)
        project_client.agents.delete_version(agent_name=multi_tool_agent.name, agent_version=multi_tool_agent.version)
        print("\nAgents cleaned up")
        
        print("\n" + "="*80)
        print("STEP 2: Create Dataset from Captured Data")
        print("="*80)
        
        # Create JSONL file
        import tempfile
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for test_case in test_cases:
                f.write(json.dumps(test_case) + '\n')
            temp_file_path = f.name
        
        # Upload dataset
        dataset: DatasetVersion = project_client.datasets.upload_file(
            name=dataset_name,
            version=dataset_version,
            file_path=temp_file_path,
        )
        print(f"Dataset created: {dataset.name} (version: {dataset.version}, id: {dataset.id})")
        
        # Clean up temp file
        os.unlink(temp_file_path)
        
        print("\n" + "="*80)
        print("STEP 3: Create and Run Combined Evaluation")
        print("="*80)
        
        # Select evaluators to run (matching the screenshot)
        evaluators_to_run = [
            "tool_call_accuracy",
            "tool_selection",
            "tool_input_accuracy",
            "tool_call_success",
            "task_completion",
            "task_adherence",
            "coherence",
            "fluency",
            "relevance",
            "groundedness",
            "intent_resolution",
            "tool_output_utilization",
        ]
        
        # Build testing criteria with all evaluators
        print(f"Building testing criteria for {len(evaluators_to_run)} evaluators...")
        testing_criteria = build_testing_criteria(evaluators_to_run, model_deployment_name)
        
        for criterion in testing_criteria:
            print(f"  ✓ {criterion['name']}")
        
        # Get unified data source config
        unified_data_source_config = get_unified_data_source_config()
        
        # Create single evaluation with all testing criteria
        print(f"\nCreating evaluation with {len(testing_criteria)} evaluators...")
        eval_object = client.evals.create(
            name=f"Comprehensive Agent Evaluation - {dataset_name}",
            data_source_config=unified_data_source_config,
            testing_criteria=testing_criteria,  # type: ignore
        )
        print(f"✓ Evaluation created (id: {eval_object.id})")
        
        # Create single evaluation run with dataset ID
        print(f"\nCreating evaluation run with dataset ID: {dataset.id}...")
        eval_run = client.evals.runs.create(
            eval_id=eval_object.id,
            name=f"comprehensive_run_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            metadata={
                "dataset": dataset_name,
                "evaluators": ", ".join(evaluators_to_run),
                "test_cases": len(test_cases),
            },
            data_source=CreateEvalJSONLRunDataSourceParam(
                type="jsonl",
                source=SourceFileID(type="file_id", id=dataset.id if dataset.id else "")
            ),
        )
        print(f"✓ Evaluation run created (id: {eval_run.id})")
        
        # Wait for completion
        print(f"\nWaiting for evaluation to complete...")
        while True:
            run = client.evals.runs.retrieve(run_id=eval_run.id, eval_id=eval_object.id)
            if run.status in ["completed", "failed"]:
                print(f"\n✓ Evaluation {run.status}")
                break
            print(".", end="", flush=True)
            time.sleep(5)
        
        # Get results
        evaluation_results = {
            "eval_id": eval_object.id,
            "run_id": eval_run.id,
            "status": run.status,
            "report_url": run.report_url,
            "result_counts": run.result_counts if hasattr(run, 'result_counts') else None,
        }
        
        print("\n\n" + "="*80)
        print("EVALUATION SUMMARY")
        print("="*80)
        print(f"Dataset: {dataset_name} (id: {dataset.id})")
        print(f"Test Cases: {len(test_cases)}")
        print(f"Evaluators Run: {len(evaluators_to_run)}")
        print(f"\nEvaluation Details:")
        print(f"  ID: {evaluation_results['eval_id']}")
        print(f"  Run ID: {evaluation_results['run_id']}")
        print(f"  Status: {evaluation_results['status']}")
        if evaluation_results['result_counts']:
            print(f"  Result Counts: {evaluation_results['result_counts']}")
        if evaluation_results['report_url']:
            print(f"\n  📊 Report URL: {evaluation_results['report_url']}")
        
        print(f"\nEvaluators included:")
        for evaluator in evaluators_to_run:
            print(f"  ✓ {evaluator}")
        
        # Get detailed output items
        print(f"\n{'='*80}")
        print("DETAILED RESULTS")
        print("="*80)
        output_items = list(client.evals.runs.output_items.list(
            run_id=evaluation_results['run_id'], 
            eval_id=evaluation_results['eval_id']
        ))
        print(f"Total output items: {len(output_items)}")
        
        if output_items:
            print(f"\nSample output (first item):")
            pprint(output_items[0])
        
        print("\n" + "="*80)
        print("COMPLETE")
        print("="*80)
        print(f"\n💡 View full results at: {evaluation_results['report_url']}")
        print(f"💡 Evaluation ID: {evaluation_results['eval_id']}")
        print(f"💡 Run ID: {evaluation_results['run_id']}")


if __name__ == "__main__":
    main()
