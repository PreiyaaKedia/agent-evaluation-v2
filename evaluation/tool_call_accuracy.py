# pylint: disable=line-too-long,useless-suppression
# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

"""
DESCRIPTION:
    Given an AIProjectClient, this sample demonstrates how to use the synchronous
    `openai.evals.*` methods to create, get and list evaluation and eval runs
    for Tool Call Accuracy evaluator using inline dataset content.
    
    This version is updated for Azure AI Projects SDK v2 with the new Response API.
    
    KEY CHANGES FOR SDK v2:
    - Uses PromptAgentDefinition and create_version() for agent creation
    - Response objects have an 'output' list containing ResponseFunctionToolCall and ResponseOutputMessage objects
    - Function calls are accessed via response.output with item.type == "function_call"
    - Tool call properties: item.name, item.arguments, item.call_id
    - Helper functions extract_tool_calls_from_response() and convert_response_to_conversation_format() 
      handle the new response structure
    - Demonstrates live agent responses before running evaluations

USAGE:
    python tool_call_accuracy.py

    Before running the sample:

    pip install "azure-ai-projects>=2.0.0b1" python-dotenv

    Set these environment variables with your own values:
    1) AZURE_AI_PROJECT_ENDPOINT - Required. The Azure AI Project endpoint, as found in the overview page of your
       Microsoft Foundry project. It has the form: https://<account_name>.services.ai.azure.com/api/projects/<project_name>.
    2) AZURE_AI_MODEL_DEPLOYMENT_NAME - Required. The name of the model deployment to use for evaluation.
"""

from dotenv import load_dotenv
import os
import json
import time
from pprint import pprint

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import PromptAgentDefinition, FunctionTool
from openai.types.evals.create_eval_jsonl_run_data_source_param import (
    CreateEvalJSONLRunDataSourceParam,
    SourceFileContent,
    SourceFileContentContent,
)
from openai.types.eval_create_params import DataSourceConfigCustom
from openai.types.responses.response_input_param import FunctionCallOutput

load_dotenv()


# ========================================
# Actual Function Implementations
# ========================================

def get_weather(location: str) -> dict:
    """Get weather information for a location."""
    # Simulated weather data
    weather_data = {
        "New York": {"temperature": "72°F", "condition": "Sunny", "humidity": "45%"},
        "Seattle": {"temperature": "58°F", "condition": "Rainy", "humidity": "80%"},
        "San Francisco": {"temperature": "65°F", "condition": "Foggy", "humidity": "70%"},
        "Chicago": {"temperature": "55°F", "condition": "Cloudy", "humidity": "60%"},
    }
    return weather_data.get(location, {"temperature": "70°F", "condition": "Clear", "humidity": "50%"})


def search_database(query: str, table: str) -> dict:
    """Search database for information."""
    # Simulated database results
    return {
        "results": [
            {"id": 1, "data": f"Result 1 for '{query}' in {table}"},
            {"id": 2, "data": f"Result 2 for '{query}' in {table}"},
        ],
        "count": 2,
    }


def send_email(to: str, subject: str, body: str = "") -> dict:
    """Send an email."""
    # Simulated email sending
    return {
        "status": "sent",
        "message": f"Email successfully sent to {to}",
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
    }


# Map function names to actual function references
AVAILABLE_FUNCTIONS = {
    "get_weather": get_weather,
    "search_database": search_database,
    "send_email": send_email,
}

# ========================================
# Tool Schema Definitions (Single Source of Truth)
# ========================================

TOOL_SCHEMAS = {
    "weather": {
        "name": "get_weather",
        "description": "Get weather information for a location",
        "parameters": {
            "type": "object",
            "properties": {
                "location": {
                    "type": "string",
                    "description": "The city name"
                }
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
    """
    Extract tool calls from SDK v2 Response object.
    
    Args:
        response: The Response object from openai_client.responses.create()
        
    Returns:
        List of tool call dictionaries in the format expected by the evaluator
    """
    tool_calls = []
    
    for item in response.output:
        # Check if it's a function call (SDK v2 uses ResponseFunctionToolCall)
        if hasattr(item, 'type') and item.type == "function_call":
            tool_calls.append({
                "type": "tool_call",
                "tool_call_id": item.call_id,
                "name": item.name,
                "arguments": json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments,
            })
    
    return tool_calls


def convert_response_to_conversation_format(response) -> list:
    """
    Convert SDK v2 Response object to conversation format for evaluation.
    
    Args:
        response: The Response object from openai_client.responses.create()
        
    Returns:
        List of conversation turns in the format expected by the evaluator
    """
    conversation = []
    
    for item in response.output:
        if hasattr(item, 'type'):
            if item.type == "function_call":
                # Add assistant's tool call
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
            elif item.type == "message":
                # Add assistant message
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


def execute_agent_with_tools(client, agent_name, query, available_functions=None):
    """
    Execute an agent query and handle function calls end-to-end.
    
    Args:
        client: OpenAI client from project_client.get_openai_client()
        agent_name: Name of the agent to use
        query: User query string
        available_functions: Dictionary mapping function names to callable functions
        
    Returns:
        Tuple of (initial_response, final_response, tool_calls_made, function_results)
    """
    if available_functions is None:
        available_functions = AVAILABLE_FUNCTIONS
    
    print(f"\n{'='*60}")
    print(f"Executing: {query}")
    print(f"{'='*60}")
    
    # Step 1: Get initial response from agent
    initial_response = client.responses.create(
        input=query,
        extra_body={"agent": {"name": agent_name, "type": "agent_reference"}},
    )
    
    print(f"Initial response status: {initial_response.status}")
    print(f"Initial response output types: {[item.type for item in initial_response.output]}")
    
    # Step 2: Check for function calls and execute them
    input_list = []
    tool_calls_made = []
    function_results = {}
    
    for item in initial_response.output:
        if hasattr(item, 'type') and item.type == "function_call":
            print(f"\n  → Function call detected: {item.name}")
            print(f"    Arguments: {item.arguments}")
            
            # Record the tool call
            tool_calls_made.append({
                "type": "tool_call",
                "tool_call_id": item.call_id,
                "name": item.name,
                "arguments": json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments,
            })
            
            # Execute the function if available
            if item.name in available_functions:
                function_to_call = available_functions[item.name]
                args = json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments
                
                try:
                    result = function_to_call(**args)
                    print(f"    Result: {result}")
                    
                    function_results[item.call_id] = result
                    
                    # Prepare function output for the agent
                    input_list.append(
                        FunctionCallOutput(
                            type="function_call_output",
                            call_id=item.call_id,
                            output=json.dumps(result),
                        )
                    )
                except Exception as e:
                    print(f"    Error executing function: {e}")
                    input_list.append(
                        FunctionCallOutput(
                            type="function_call_output",
                            call_id=item.call_id,
                            output=json.dumps({"error": str(e)}),
                        )
                    )
            else:
                print(f"    Warning: Function '{item.name}' not available")
    
    # Step 3: If there were function calls, send results back to agent
    final_response = None
    if input_list:
        print(f"\n  → Sending {len(input_list)} function result(s) back to agent...")
        final_response = client.responses.create(
            input=input_list,
            previous_response_id=initial_response.id,
            extra_body={"agent": {"name": agent_name, "type": "agent_reference"}},
        )
        print(f"Final response status: {final_response.status}")
        print(f"Final response: {final_response.output_text}")
    else:
        print(f"\n  → No function calls detected")
        print(f"Direct response: {initial_response.output_text}")
    
    return initial_response, final_response, tool_calls_made, function_results


def main() -> None:
    endpoint = os.environ.get(
        "AZURE_AI_PROJECT_ENDPOINT",
        os.environ.get("AZURE_EXISTING_AIPROJECT_ENDPOINT")
    )  # Sample : https://<account_name>.services.ai.azure.com/api/projects/<project_name>
    model_deployment_name = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME", "gpt-4.1")  # Sample : gpt-4o-mini

    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=endpoint, credential=credential) as project_client,
        project_client.get_openai_client() as client,
    ):
        print("Creating an OpenAI client from the AI Project client")

        data_source_config = DataSourceConfigCustom(
            {
                "type": "custom",
                "item_schema": {
                    "type": "object",
                    "properties": {
                        "query": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
                        "tool_definitions": {
                            "anyOf": [{"type": "object"}, {"type": "array", "items": {"type": "object"}}]
                        },
                        "tool_calls": {"anyOf": [{"type": "object"}, {"type": "array", "items": {"type": "object"}}]},
                        "response": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
                    },
                    "required": ["query", "tool_definitions"],
                },
                "include_sample_schema": True,
            }
        )

        testing_criteria = [
            {
                "type": "azure_ai_evaluator",
                "name": "tool_call_accuracy",
                "evaluator_name": "builtin.tool_call_accuracy",
                "initialization_parameters": {"deployment_name": f"{model_deployment_name}"},
                "data_mapping": {
                    "query": "{{item.query}}",
                    "tool_definitions": "{{item.tool_definitions}}",
                    "tool_calls": "{{item.tool_calls}}",
                    "response": "{{item.response}}",
                },
            }
        ]

        print("Creating Evaluation")
        eval_object = client.evals.create(
            name="Test Tool Call Accuracy Evaluator with inline data",
            data_source_config=data_source_config,
            testing_criteria=testing_criteria,  # type: ignore
        )
        print(f"Evaluation created")

        print("Get Evaluation by Id")
        eval_object_response = client.evals.retrieve(eval_object.id)
        print("Eval Run Response:")
        pprint(eval_object_response)

        # ========================================
        # SDK v2 Agent Examples with Real Responses
        # ========================================
        
        print("\n" + "="*60)
        print("SDK v2: End-to-End Agent Execution with Function Calls")
        print("="*60 + "\n")
        
        # Test Case 1: Weather Query
        print("\n" + "="*60)
        print("TEST CASE 1: Simple Weather Query")
        print("="*60)
        
        weather_tool = create_function_tool(TOOL_SCHEMAS["weather"])
        
        weather_agent = project_client.agents.create_version(
            agent_name="WeatherAgent",
            definition=PromptAgentDefinition(
                model=model_deployment_name,
                instructions="You are a helpful assistant that can check weather information. Always use the get_weather tool to get accurate weather data.",
                tools=[weather_tool],
            ),
        )
        
        query1 = "What's the weather like in New York?"
        initial_resp1, final_resp1, tool_calls1, func_results1 = execute_agent_with_tools(
            client, weather_agent.name, query1
        )
        
        tool_definitions1 = [schema_to_eval_format(TOOL_SCHEMAS["weather"])]
        
        # Test Case 2: Multiple Tool Calls
        print("\n" + "="*60)
        print("TEST CASE 2: Multiple Tool Calls (Database + Email)")
        print("="*60)
        
        database_tool = create_function_tool(TOOL_SCHEMAS["database"])
        email_tool = create_function_tool(TOOL_SCHEMAS["email"])
        
        multi_tool_agent = project_client.agents.create_version(
            agent_name="MultiToolAgent",
            definition=PromptAgentDefinition(
                model=model_deployment_name,
                instructions="You are a helpful assistant that can search databases and send emails. Use the tools to help users with their requests.",
                tools=[database_tool, email_tool],
            ),
        )
        
        query2 = "Search for customer orders in the orders table and send an email to customer@example.com with subject 'Order Update'"
        initial_resp2, final_resp2, tool_calls2, func_results2 = execute_agent_with_tools(
            client, multi_tool_agent.name, query2
        )
        
        tool_definitions2 = [
            schema_to_eval_format(TOOL_SCHEMAS["database"]),
            schema_to_eval_format(TOOL_SCHEMAS["email"]),
        ]
        
        # Test Case 3: Seattle Weather with Conversation Format
        print("\n" + "="*60)
        print("TEST CASE 3: Seattle Weather (Conversation Format)")
        print("="*60)
        
        query3 = "What's the weather in Seattle?"
        initial_resp3, final_resp3, tool_calls3, func_results3 = execute_agent_with_tools(
            client, weather_agent.name, query3
        )
        
        # Convert to conversation format for evaluation
        response3_conversation = convert_response_to_conversation_format(initial_resp3)
        if final_resp3:
            response3_conversation.extend(convert_response_to_conversation_format(final_resp3))
        
        tool_definitions3 = tool_definitions1  # Same as weather tool
        
        # Test Case 4: No Tool Call Needed
        print("\n" + "="*60)
        print("TEST CASE 4: No Tool Call Needed (General Conversation)")
        print("="*60)
        
        query4 = "Hello! Can you tell me what tools you have available?"
        initial_resp4, final_resp4, tool_calls4, func_results4 = execute_agent_with_tools(
            client, weather_agent.name, query4
        )
        
        tool_definitions4 = tool_definitions1  # Same as weather tool
        
        print("\n" + "="*60)
        print("Summary of Captured Data:")
        print("="*60)
        print(f"Test 1 - Tool Calls: {len(tool_calls1)}")
        print(f"Test 2 - Tool Calls: {len(tool_calls2)}")
        print(f"Test 3 - Tool Calls: {len(tool_calls3)}")
        print(f"Test 3 - Conversation Turns: {len(response3_conversation)}")
        print(f"Test 4 - Tool Calls: {len(tool_calls4)} (should be 0)")
        
        # Clean up agents
        print("\nCleaning up agents...")
        project_client.agents.delete_version(agent_name=weather_agent.name, agent_version=weather_agent.version)
        project_client.agents.delete_version(agent_name=multi_tool_agent.name, agent_version=multi_tool_agent.version)
        print("Agents deleted")
        
        print("\n" + "="*60)
        print("Creating Evaluation with Real Agent Data")
        print("="*60 + "\n")

        print("Creating Eval Run with Real Data from Agents")
        eval_run_object = client.evals.runs.create(
            eval_id=eval_object.id,
            name="sdk_v2_real_data_run",
            metadata={"team": "eval-exp", "scenario": "sdk-v2-real-agents"},
            data_source=CreateEvalJSONLRunDataSourceParam(
                type="jsonl",
                source=SourceFileContent(
                    type="file_content",
                    content=[
                        # Test Case 1: Simple weather query with real data
                        SourceFileContentContent(
                            item={
                                "query": query1,
                                "tool_definitions": tool_definitions1,
                                "tool_calls": tool_calls1,
                                "response": None,
                            }
                        ),
                        # Test Case 2: Multiple tool calls with real data
                        SourceFileContentContent(
                            item={
                                "query": query2,
                                "tool_definitions": tool_definitions2,
                                "tool_calls": tool_calls2,
                                "response": None,
                            }
                        ),
                        # Test Case 3: Conversation format with real data
                        SourceFileContentContent(
                            item={
                                "query": query3,
                                "tool_definitions": tool_definitions3,
                                "response": response3_conversation,
                                "tool_calls": None,
                            }
                        ),
                        # Test Case 4: No tool call needed
                        SourceFileContentContent(
                            item={
                                "query": query4,
                                "tool_definitions": tool_definitions4,
                                "tool_calls": tool_calls4 if tool_calls4 else None,
                                "response": initial_resp4.output_text,
                            }
                        ),
                    ],
                ),
            ),
        )

        print(f"Eval Run created")
        pprint(eval_run_object)

        print("Get Eval Run by Id")
        eval_run_response = client.evals.runs.retrieve(run_id=eval_run_object.id, eval_id=eval_object.id)
        print("Eval Run Response:")
        pprint(eval_run_response)

        print("\n\n----Eval Run Output Items----\n\n")

        while True:
            run = client.evals.runs.retrieve(run_id=eval_run_response.id, eval_id=eval_object.id)
            if run.status == "completed" or run.status == "failed":
                output_items = list(client.evals.runs.output_items.list(run_id=run.id, eval_id=eval_object.id))
                pprint(output_items)
                print(f"Eval Run Status: {run.status}")
                print(f"Eval Run Report URL: {run.report_url}")
                break
            time.sleep(5)
            print("Waiting for eval run to complete...")


if __name__ == "__main__":
    main()