"""
Helper functions for agent execution and response processing.
Includes context extraction and query execution utilities.
"""

import json
from datetime import datetime
from openai.types.responses.response_input_param import FunctionCallOutput
from business_functions import AVAILABLE_FUNCTIONS
from tool_schemas import FUNCTION_TOOL_SCHEMAS


def schema_to_tool_definition(schema: dict) -> dict:
    """Convert tool schema to evaluation tool_definition format."""
    return {
        "type": "function",
        "name": schema["name"],
        "description": schema["description"],
        "parameters": schema["parameters"],
    }


def build_message_object(role, content, run_id, tool_call_id=None):
    """Build a message object in the format expected by evaluators."""
    msg = {
        "createdAt": datetime.utcnow().isoformat() + "Z",
        "run_id": run_id,
        "role": role,
        "content": content,
    }
    if tool_call_id:
        msg["tool_call_id"] = tool_call_id
    return msg


def extract_context_from_response(response) -> str:
    """Extract context from response including search citations."""
    context_parts = []
    
    for item in response.output:
        # File Search queries
        if hasattr(item, 'type') and item.type == "file_search_call":
            if hasattr(item, 'queries') and item.queries:
                context_parts.append(f"File search queries: {', '.join(item.queries)}")
        
        # Azure AI Search queries
        if hasattr(item, 'type') and item.type == "azure_ai_search_call":
            if hasattr(item, 'arguments'):
                try:
                    args = json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments
                    if 'query' in args:
                        context_parts.append(f"Azure AI Search query: {args['query']}")
                except:
                    pass
        
        # Extract message content with annotations
        if hasattr(item, 'type') and item.type == "message":
            if hasattr(item, 'content'):
                for content_item in item.content:
                    if hasattr(content_item, 'type') and content_item.type == "output_text":
                        # Extract annotations
                        if hasattr(content_item, 'annotations') and content_item.annotations:
                            for annotation in content_item.annotations:
                                if hasattr(annotation, 'type'):
                                    if annotation.type == "file_citation":
                                        citation_text = f"[File: {annotation.file_id}"
                                        if hasattr(annotation, 'filename'):
                                            citation_text += f" ({annotation.filename})"
                                        citation_text += "]"
                                        context_parts.append(citation_text)
                                    elif annotation.type == "url_citation":
                                        citation_text = f"[Source: {annotation.title if hasattr(annotation, 'title') else 'Unknown'}]"
                                        context_parts.append(citation_text)
                        
                        # Add text content
                        if hasattr(content_item, 'text') and content_item.text:
                            context_parts.append(content_item.text)
    
    return " ".join(context_parts) if context_parts else ""


def execute_agent_query(client, agent_name, query, conversation_id=None):
    """Execute agent query with full tool support."""
    from datetime import datetime
    import time
    
    print(f"\n{'='*60}")
    print(f"Query: {query}")
    print(f"{'='*60}")
    
    # Track conversation messages in format required by evaluators
    response_messages = []
    run_id = f"run_{int(time.time())}"
    
    request_params = {
        "input": query,
        "extra_body": {"agent": {"name": agent_name, "type": "agent_reference"}},
    }
    if conversation_id:
        request_params["conversation"] = conversation_id
    
    initial_response = client.responses.create(**request_params)
    
    # Extract context
    context = extract_context_from_response(initial_response)
    
    # Handle function calls and capture tool call information
    input_list = []
    tool_calls_made = []
    function_results = {}
    
    # Build assistant message with tool calls from initial response
    assistant_content = []
    for item in initial_response.output:
        # Capture File Search tool calls (tracking only, not added to response messages)
        if hasattr(item, 'type') and item.type == "file_search_call":
            print(f"  → File Search: {item.queries if hasattr(item, 'queries') else 'N/A'}")
            tool_calls_made.append({
                "type": "file_search",
                "tool_call_id": item.call_id if hasattr(item, 'call_id') else None,
                "queries": item.queries if hasattr(item, 'queries') else [],
            })
            # Note: file_search is not added to response messages as it's a built-in tool without definition
        
        # Capture Azure AI Search tool calls (tracking only, not added to response messages)
        elif hasattr(item, 'type') and item.type == "azure_ai_search_call":
            args = json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments if hasattr(item, 'arguments') else {}
            print(f"  → Azure AI Search: {args.get('query', 'N/A')}")
            tool_calls_made.append({
                "type": "azure_ai_search",
                "tool_call_id": item.call_id if hasattr(item, 'call_id') else None,
                "query": args.get('query', ''),
                "arguments": args,
            })
            # Note: azure_ai_search is not added to response messages as it's a built-in tool without definition
        
        # Capture function tool calls
        elif hasattr(item, 'type') and item.type == "function_call":
            print(f"  → Function: {item.name}({item.arguments})")
            
            parsed_args = json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments
            
            # Capture tool call information
            tool_calls_made.append({
                "type": "function_call",
                "tool_call_id": item.call_id,
                "name": item.name,
                "arguments": parsed_args,
            })
            
            # Add to message content
            assistant_content.append({
                "type": "tool_call",
                "tool_call_id": item.call_id,
                "name": item.name,
                "arguments": parsed_args,
            })
            
            if item.name in AVAILABLE_FUNCTIONS:
                function_to_call = AVAILABLE_FUNCTIONS[item.name]
                
                try:
                    result = function_to_call(**parsed_args)
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
                    function_results[item.call_id] = {"error": str(e)}
                    input_list.append(
                        FunctionCallOutput(
                            type="function_call_output",
                            call_id=item.call_id,
                            output=json.dumps({"error": str(e)}),
                        )
                    )
    
    # Add assistant message with tool calls if any
    if assistant_content:
        response_messages.append(build_message_object("assistant", assistant_content, run_id))
        
        # Add tool result messages
        for tool_call in assistant_content:
            tool_call_id = tool_call.get("tool_call_id")
            if tool_call_id in function_results:
                response_messages.append(build_message_object(
                    "tool",
                    [{"type": "tool_result", "tool_result": function_results[tool_call_id]}],
                    run_id,
                    tool_call_id=tool_call_id
                ))
    
    # Get final response if there were function calls (handle iterative tool calling)
    current_response = initial_response
    max_iterations = 5  # Prevent infinite loops
    iteration = 0
    
    while input_list and iteration < max_iterations:
        iteration += 1
        request_params["input"] = input_list
        request_params["previous_response_id"] = current_response.id
        current_response = client.responses.create(**request_params)
        
        # Extract context from this response
        iteration_context = extract_context_from_response(current_response)
        if iteration_context:
            context = f"{context} {iteration_context}".strip()
        
        # Check if there are MORE function calls to handle
        input_list = []
        iteration_assistant_content = []
        
        for item in current_response.output:
            # Capture any additional File Search calls (tracking only)
            if hasattr(item, 'type') and item.type == "file_search_call":
                print(f"  → File Search (iteration {iteration}): {item.queries if hasattr(item, 'queries') else 'N/A'}")
                tool_calls_made.append({
                    "type": "file_search",
                    "tool_call_id": item.call_id if hasattr(item, 'call_id') else None,
                    "queries": item.queries if hasattr(item, 'queries') else [],
                })
                # Note: file_search not added to iteration messages as it's a built-in tool
            
            # Capture any additional Azure AI Search calls (tracking only)
            elif hasattr(item, 'type') and item.type == "azure_ai_search_call":
                args = json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments if hasattr(item, 'arguments') else {}
                print(f"  → Azure AI Search (iteration {iteration}): {args.get('query', 'N/A')}")
                tool_calls_made.append({
                    "type": "azure_ai_search",
                    "tool_call_id": item.call_id if hasattr(item, 'call_id') else None,
                    "query": args.get('query', ''),
                    "arguments": args,
                })
                # Note: azure_ai_search not added to iteration messages as it's a built-in tool
            
            # Handle additional function calls
            elif hasattr(item, 'type') and item.type == "function_call":
                print(f"  → Function (iteration {iteration}): {item.name}({item.arguments})")
                
                parsed_args = json.loads(item.arguments) if isinstance(item.arguments, str) else item.arguments
                
                tool_calls_made.append({
                    "type": "function_call",
                    "tool_call_id": item.call_id,
                    "name": item.name,
                    "arguments": parsed_args,
                })
                
                iteration_assistant_content.append({
                    "type": "tool_call",
                    "tool_call_id": item.call_id,
                    "name": item.name,
                    "arguments": parsed_args,
                })
                
                if item.name in AVAILABLE_FUNCTIONS:
                    function_to_call = AVAILABLE_FUNCTIONS[item.name]
                    
                    try:
                        result = function_to_call(**parsed_args)
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
                        function_results[item.call_id] = {"error": str(e)}
                        input_list.append(
                            FunctionCallOutput(
                                type="function_call_output",
                                call_id=item.call_id,
                                output=json.dumps({"error": str(e)}),
                            )
                        )
        
        # Add iteration messages if there were tool calls
        if iteration_assistant_content:
            response_messages.append(build_message_object("assistant", iteration_assistant_content, run_id))
            
            # Add tool result messages
            for tool_call in iteration_assistant_content:
                tool_call_id = tool_call.get("tool_call_id")
                if tool_call_id in function_results:
                    response_messages.append(build_message_object(
                        "tool",
                        [{"type": "tool_result", "tool_result": function_results[tool_call_id]}],
                        run_id,
                        tool_call_id=tool_call_id
                    ))
        
        # If no more function calls, we're done
        if not input_list:
            break
    
    response_text = current_response.output_text or ""
    if not response_text:
        print(f"  ⚠ Warning: No response text generated after {iteration} iterations")
    else:
        print(f"Response: {response_text[:200]}...")
    
    # Add final assistant message with text response
    if response_text:
        response_messages.append(build_message_object(
            "assistant",
            [{"type": "text", "text": response_text}],
            run_id
        ))
    
    # Build tool_definitions from all function tools that were available
    tool_definitions = []
    for schema in FUNCTION_TOOL_SCHEMAS.values():
        tool_definitions.append(schema_to_tool_definition(schema))
    
    return {
        "query": query,
        "response": response_messages,  # Now an array of message objects
        "context": context,
        "tool_definitions": tool_definitions,
        "tool_calls": tool_calls_made if tool_calls_made else None,
        "ground_truth": ""  # To be filled manually or via another evaluation
    }
