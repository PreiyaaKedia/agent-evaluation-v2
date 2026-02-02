# Agent Evaluation with Azure AI Projects SDK v2

## Overview

This document describes how to perform comprehensive end-to-end agent evaluations using the Azure AI Projects SDK v2. The evaluation pipeline captures real agent responses, creates datasets, and runs multiple built-in evaluators.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. AGENT EXECUTION                                              │
│    • Create agents with function tools                          │
│    • Execute queries with real tool calls                       │
│    • Capture responses, tool calls, and results                 │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. DATASET CREATION                                             │
│    • Convert captured data to JSONL format                      │
│    • Upload to Azure AI Projects as Dataset                     │
│    • Get Dataset ID for evaluation runs                         │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. EVALUATION EXECUTION                                         │
│    • Create evaluations with proper schemas                     │
│    • Run evaluations using Dataset ID                           │
│    • Monitor status and collect results                         │
└─────────────────────────────────────────────────────────────────┘
```

## Key Components

### 1. Agent Execution Pipeline

**Purpose:** Execute agents with real function tools and capture all data needed for evaluation.

**Key Functions:**
- `execute_agent_with_tools()` - Executes agent with end-to-end function calling
- `extract_tool_calls_from_response()` - Extracts tool calls from SDK v2 Response
- `convert_response_to_conversation_format()` - Converts to conversation format

**SDK v2 Response Structure:**
```python
Response(
    id='resp_xxx',
    status='completed',
    output=[
        ResponseFunctionToolCall(
            type='function_call',
            name='function_name',
            arguments='{"param": "value"}',
            call_id='call_xxx'
        ),
        ResponseOutputMessage(
            type='message',
            content=[
                ResponseOutputText(text='Final response')
            ]
        )
    ]
)
```

### 2. Tool Schema Management

**Single Source of Truth Pattern:**
```python
TOOL_SCHEMAS = {
    "tool_name": {
        "name": "function_name",
        "description": "Tool description",
        "parameters": {...},
        "strict": True,
    }
}
```

**Helper Functions:**
- `create_function_tool(schema)` → FunctionTool (for agents)
- `schema_to_eval_format(schema)` → dict (for evaluation)

**Benefits:**
- No duplication
- Consistent definitions
- Easy maintenance
- Type safety with `strict=True`

### 3. Dataset Creation

**From Inline Data to Dataset ID:**

```python
# 1. Prepare data in JSONL format
test_cases = [
    {
        "query": "user query",
        "response": conversation_format_or_string,
        "tool_definitions": [...],
        "tool_calls": [...],
        "context": "additional context"
    }
]

# 2. Create JSONL file
with open('data.jsonl', 'w') as f:
    for case in test_cases:
        f.write(json.dumps(case) + '\n')

# 3. Upload as dataset
dataset = project_client.datasets.upload_file(
    name="dataset_name",
    version="1",
    file_path="data.jsonl"
)

# 4. Use dataset.id for evaluations
```

### 4. Evaluator Configurations

Each evaluator requires specific schema configuration and data mapping.

#### Tool-Related Evaluators

**tool_call_accuracy**
- **Purpose:** Measures whether the agent calls the right tools
- **Required Fields:** `query`, `tool_definitions`
- **Optional Fields:** `tool_calls`, `response`

**tool_selection**
- **Purpose:** Evaluates whether an AI agent selected appropriate tools
- **Required Fields:** `query`, `response`, `tool_definitions`
- **Optional Fields:** `tool_calls`

**tool_input_accuracy**
- **Purpose:** Checks if inputs to tools are accurate
- **Required Fields:** `query`, `response`, `tool_definitions`

**tool_output_utilization**
- **Purpose:** Checks if agent correctly uses tool outputs
- **Required Fields:** `query`, `response`
- **Optional Fields:** `tool_definitions`

**tool_call_success**
- **Purpose:** Evaluates if tool calls succeed
- **Required Fields:** `response`
- **Optional Fields:** `tool_definitions`

#### Task-Related Evaluators

**task_completion**
- **Purpose:** Evaluates if agent completes the task
- **Required Fields:** `query`, `response`
- **Optional Fields:** `tool_definitions`

**task_adherence**
- **Purpose:** Checks if agent adheres to task requirements
- **Required Fields:** `query`, `response`
- **Optional Fields:** `tool_definitions`

#### Quality Evaluators

**coherence**
- **Purpose:** Evaluates logical consistency
- **Required Fields:** `query`, `response`

**fluency**
- **Purpose:** Evaluates how natural and fluent responses are
- **Required Fields:** `response`
- **Optional Fields:** `query`

**relevance**
- **Purpose:** Assesses how relevant response is to query
- **Required Fields:** `query`, `response`

**groundedness**
- **Purpose:** Checks if response is grounded in context
- **Required Fields:** `response`
- **Optional Fields:** `context`, `query`, `tool_definitions`

**intent_resolution**
- **Purpose:** Checks if model correctly resolves user intent
- **Required Fields:** `query`, `response`
- **Optional Fields:** `tool_definitions`

## Usage

### Prerequisites

```bash
pip install "azure-ai-projects>=2.0.0b1" python-dotenv
```

### Environment Variables

```bash
export AZURE_AI_PROJECT_ENDPOINT="https://<account>.services.ai.azure.com/api/projects/<project>"
export AZURE_AI_MODEL_DEPLOYMENT_NAME="gpt-4.1"
export DATASET_NAME="my-evaluation-dataset"  # Optional
export DATASET_VERSION="1"                   # Optional
```

### Running Evaluations

```bash
# Run comprehensive evaluation
python evaluation/comprehensive_agent_evaluation.py
```

### Expected Output

```
================================================================================
STEP 1: Execute Agents and Capture Data
================================================================================
Executing: What's the weather like in New York?
Status: completed
  → Function call: get_weather({"location": "New York"})
    Result: {'temperature': '72°F', 'condition': 'Sunny', 'humidity': '45%'}
Final response: The weather in New York is...

Agents cleaned up

================================================================================
STEP 2: Create Dataset from Captured Data
================================================================================
Dataset created: agent-eval-20260202_123456 (version: 1, id: dataset_abc123)

================================================================================
STEP 3: Create and Run Evaluations
================================================================================
Running: tool_call_accuracy
Evaluation created (id: eval_123)
Evaluation run created (id: run_456)
Status: completed
Report: https://...

================================================================================
EVALUATION SUMMARY
================================================================================
Dataset: agent-eval-20260202_123456 (id: dataset_abc123)
Test Cases: 4

Evaluations Run:
  ✓ tool_call_accuracy: completed
    Report: https://...
  ✓ tool_selection: completed
    Report: https://...
  ...
```

## Data Format Requirements

### Conversation Format (for complex scenarios)

```python
response = [
    {
        "createdAt": "2026-02-02T12:00:00Z",
        "run_id": "run_xxx",
        "role": "assistant",
        "content": [{
            "type": "tool_call",
            "tool_call_id": "call_xxx",
            "name": "function_name",
            "arguments": {"param": "value"}
        }]
    },
    {
        "createdAt": "2026-02-02T12:00:01Z",
        "run_id": "run_xxx",
        "role": "assistant",
        "content": [{
            "type": "text",
            "text": "Final response text"
        }]
    }
]
```

### String Format (for simple scenarios)

```python
response = "Direct response text without tool calls"
```

### Tool Calls Format

```python
tool_calls = [
    {
        "type": "tool_call",
        "tool_call_id": "call_xxx",
        "name": "function_name",
        "arguments": {"param": "value"}
    }
]
```

### Tool Definitions Format

```python
tool_definitions = [
    {
        "type": "function",
        "name": "function_name",
        "description": "Function description",
        "parameters": {
            "type": "object",
            "properties": {
                "param": {"type": "string", "description": "Parameter description"}
            },
            "required": ["param"]
        }
    }
]
```

## Best Practices

### 1. Tool Schema Design

✅ **DO:**
- Use `strict=True` for structured outputs
- Include all properties in `required` array when using strict mode
- Provide clear descriptions for all parameters
- Use single source of truth for schemas

❌ **DON'T:**
- Mix strict and non-strict schemas
- Have optional parameters with `strict=True`
- Duplicate tool definitions
- Forget to validate schemas

### 2. Agent Execution

✅ **DO:**
- Execute functions and send results back to agent
- Capture both initial and final responses
- Handle exceptions in function execution
- Log all tool calls for debugging

❌ **DON'T:**
- Skip function execution
- Ignore final agent responses
- Forget error handling
- Lose track of conversation flow

### 3. Dataset Creation

✅ **DO:**
- Include diverse test cases
- Capture real agent behavior
- Add context where relevant
- Version your datasets

❌ **DON'T:**
- Use only synthetic data
- Skip edge cases
- Forget to clean up agents
- Hardcode responses

### 4. Evaluation Selection

✅ **DO:**
- Run evaluators relevant to your use case
- Monitor evaluation status
- Check report URLs for details
- Track evaluation IDs for reference

❌ **DON'T:**
- Run all evaluators blindly
- Ignore evaluation failures
- Skip result validation
- Forget to document findings

## Troubleshooting

### Common Issues

**1. `strict=True` validation errors**
```
Error: 'required' must include every key in properties
Solution: Add all properties to 'required' array or set strict=False
```

**2. Dataset upload failures**
```
Error: Invalid JSONL format
Solution: Ensure each line is valid JSON and ends with newline
```

**3. Evaluation schema mismatches**
```
Error: Missing required field 'query'
Solution: Check evaluator requirements and ensure all fields present
```

**4. Agent response parsing errors**
```
Error: AttributeError: 'dict' object has no attribute 'type'
Solution: Access response.output for SDK v2, not raw dictionaries
```

## Advanced Topics

### Custom Evaluators

You can create custom evaluators by defining your own schema and logic:

```python
custom_config = {
    "data_source_config": DataSourceConfigCustom({
        "type": "custom",
        "item_schema": {
            "type": "object",
            "properties": {
                "custom_field": {"type": "string"}
            },
            "required": ["custom_field"],
        },
        "include_sample_schema": True,
    }),
    "data_mapping": {
        "custom_field": "{{item.custom_field}}",
    },
}
```

### Batch Evaluations

For large-scale evaluations, consider:
- Processing agents in batches
- Using async operations where possible
- Implementing retry logic
- Caching intermediate results

### Evaluation Metrics

Access detailed metrics via the report URLs:
- Accuracy scores
- Latency measurements
- Error rates
- Confidence levels

## References

- [Azure AI Projects SDK Documentation](https://learn.microsoft.com/azure/ai-studio/)
- [Agent SDK v2 Migration Guide](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/ai/azure-ai-projects)
- [Built-in Evaluators Reference](https://learn.microsoft.com/azure/ai-studio/how-to/evaluate-results)
- [Sample Evaluations](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/ai/azure-ai-projects/samples/evaluations)

## Version History

- **v1.0 (2026-02-02)**: Initial version with SDK v2 support
  - End-to-end agent execution with function tools
  - Dataset-based evaluation approach
  - 12 built-in evaluators configured
  - Comprehensive documentation

---

**Last Updated:** February 2, 2026  
**Maintainer:** Azure AI Projects Team
