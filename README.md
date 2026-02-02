# Contoso Electronics Agent - Comprehensive Evaluation System

A production-ready evaluation framework for Azure AI Agents with support for 12 built-in evaluators, dataset generation, multi-run comparison, and cluster insights analysis.

## 📋 Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Evaluators](#evaluators)
- [Workflows](#workflows)
- [File Structure](#file-structure)
- [Advanced Usage](#advanced-usage)
- [Best Practices](#best-practices)

## 🎯 Overview

This evaluation system provides comprehensive testing and analysis for AI agents built with Azure AI Projects SDK v2. It supports:

- **12 Built-in Evaluators**: Tool-focused, task-focused, and quality-focused metrics
- **Dataset Generation**: Automated generation of test data from live agent interactions
- **Multi-Run Comparison**: Compare model performance across different configurations
- **Cluster Insights**: AI-powered analysis to identify failure patterns and improvement opportunities
- **Modular Architecture**: Separate concerns for maintainability and reusability

### Key Features

✅ **Comprehensive Agent Support**: Function Tools, File Search, Azure AI Search  
✅ **Message Array Format**: Proper response format for tool input/output evaluation  
✅ **Iterative Tool Calling**: Captures multi-turn tool interactions  
✅ **Built-in Tools Handling**: Correctly separates built-in from custom function tools  
✅ **Production Ready**: Based on official Azure SDK samples and patterns

## 🏗️ Architecture

### Modular Design

```
evaluation/
├── business_functions.py      # 10 e-commerce business functions
├── tool_schemas.py            # Tool definitions for all functions
├── agent_helpers.py           # Response processing and query execution
├── agent_config.py            # Agent instructions and test queries
├── schema_mappings.py         # Official evaluator schema mappings
├── generate_agent_test_dataset.py   # Dataset generation
├── run_evaluation_with_dataset.py   # Evaluation execution
├── generate_cluster_insights.py     # Cluster analysis
└── documents/
    ├── Contoso_Return_Policy.md
    └── Contoso_Warranty_Information.md
```

### Component Responsibilities

| Component | Purpose |
|-----------|---------|
| **business_functions.py** | Implements realistic business operations (orders, refunds, emails, CRM) |
| **tool_schemas.py** | Defines OpenAI function schemas with strict validation |
| **agent_helpers.py** | Converts agent responses to evaluator-compatible format |
| **agent_config.py** | Centralized configuration for agent behavior and test scenarios |
| **schema_mappings.py** | Official Azure SDK schema patterns for all evaluators |

## 📦 Prerequisites

### Required Environment Variables

```bash
# Azure AI Project Configuration
AZURE_AI_PROJECT_ENDPOINT=https://your-account.services.ai.azure.com/api/projects/your-project
AZURE_AI_MODEL_DEPLOYMENT_NAME=gpt-4.1  # Model for evaluation
AGENT_MODEL_DEPLOYMENT_NAME=gpt-4.1-mini  # Model for agent

# Azure AI Search (optional, for Azure AI Search tool)
AI_SEARCH_PROJECT_CONNECTION_ID=your-connection-id
AI_SEARCH_INDEX_NAME=policy-index

# Evaluation Comparison (optional)
EVAL_ID=  # Set to compare runs under same evaluation
```

### Python Dependencies

```bash
pip install "azure-ai-projects>=2.0.0b1" python-dotenv azure-identity openai
```

## 🚀 Quick Start

### 1. Generate Test Dataset

Generate a dataset with 10 realistic test scenarios:

```bash
python evaluation/generate_agent_test_dataset.py
```

**Output**: `evaluation/generated_test_dataset.jsonl`

**Dataset includes:**
- User queries covering order tracking, returns, emails, CRM updates
- Agent responses with tool calls and results (message array format)
- Context from File Search and Azure AI Search
- Tool definitions for all function tools
- Ground truth fields (optional, for reference)

### 2. Run Evaluation

Execute all 12 evaluators on the generated dataset:

```bash
python evaluation/run_evaluation_with_dataset.py
```

**Results:**
- Creates evaluation and run in Azure AI Projects
- Polls for completion (typically 2-5 minutes for 10 items)
- Outputs aggregated scores and report URL
- View detailed results in Azure AI Studio

### 3. Generate Cluster Insights

Analyze evaluation results to identify patterns:

```bash
# Update eval_id and run_ids in generate_cluster_insights.py first
python evaluation/generate_cluster_insights.py
```

**Provides:**
- Cluster analysis of failure patterns
- Actionable suggestions for improvement
- Sub-cluster breakdown for detailed analysis
- Visualization coordinates for Azure AI Studio

## 📊 Evaluators

### Tool Evaluators (5)

| Evaluator | Measures | Pass Threshold |
|-----------|----------|----------------|
| **tool_call_accuracy** | Correct tool selection and parameter accuracy | ≥3/5 |
| **tool_selection** | Appropriate tools chosen without excess | ≥3/5 |
| **tool_input_accuracy** | Tool parameters match requirements | ≥3/5 |
| **tool_output_utilization** | Effective use of tool results in response | ≥3/5 |
| **tool_call_success** | Technical success of tool execution | Pass/Fail |

### Task Evaluators (2)

| Evaluator | Measures | Pass Threshold |
|-----------|----------|----------------|
| **task_completion** | User's objective fully achieved | Pass/Fail |
| **task_adherence** | Response follows instructions correctly | ≥3/5 |

### Quality Evaluators (5)

| Evaluator | Measures | Pass Threshold |
|-----------|----------|----------------|
| **coherence** | Logical flow and consistency | ≥3/5 |
| **fluency** | Natural language quality | ≥3/5 |
| **relevance** | Response addresses the query | ≥3/5 |
| **groundedness** | Response grounded in provided context | ≥3/5 |
| **intent_resolution** | User's intent successfully resolved | ≥3/5 |

## 📝 Workflows

### Workflow 1: Model Performance Comparison

Compare different models (e.g., gpt-4.1 vs gpt-4.1-mini) before migration:

```bash
# Step 1: Generate baseline dataset with gpt-4o-mini
# Update .env: AGENT_MODEL_DEPLOYMENT_NAME=gpt-4o-mini
python evaluation/generate_agent_test_dataset.py
python evaluation/run_evaluation_with_dataset.py
# Note the Evaluation ID from output

# Step 2: Generate comparison dataset with gpt-4.1-mini
# Update .env: AGENT_MODEL_DEPLOYMENT_NAME=gpt-4.1-mini
# Update .env: EVAL_ID=<evaluation-id-from-step-1>
python evaluation/generate_agent_test_dataset.py
python evaluation/run_evaluation_with_dataset.py

# Step 3: Compare runs in Azure AI Studio
# Both runs appear under same evaluation for side-by-side comparison
```

### Workflow 2: Iterative Agent Improvement

Improve agent performance based on evaluation insights:

```bash
# Step 1: Baseline evaluation
python evaluation/generate_agent_test_dataset.py
python evaluation/run_evaluation_with_dataset.py

# Step 2: Analyze failures
python evaluation/generate_cluster_insights.py
# Review clusters and suggestions

# Step 3: Update agent configuration
# Modify agent_config.py AGENT_INSTRUCTIONS based on insights

# Step 4: Re-evaluate
# Set EVAL_ID to compare with baseline
python evaluation/generate_agent_test_dataset.py
python evaluation/run_evaluation_with_dataset.py

# Step 5: Compare improvements
# View both runs in Azure AI Studio
```

### Workflow 3: Custom Dataset Evaluation

Evaluate with your own dataset:

```bash
# Step 1: Create custom dataset in JSONL format
# Each line must include: query, response, context, tool_definitions, tool_calls, ground_truth
# See generated_test_dataset.jsonl for format reference

# Step 2: Set environment variable
export DATASET_FILE=/path/to/your/dataset.jsonl

# Step 3: Run evaluation
python evaluation/run_evaluation_with_dataset.py
```

## 📁 File Structure

### Core Components

#### `business_functions.py`

Implements 10 realistic business functions for e-commerce operations:

```python
# Available functions:
- check_order_status(order_number)
- process_refund(order_number, reason)
- cancel_order(order_number)
- send_email(to, subject, body, cc)
- update_customer_profile_salesforce(customer_id, phone, email, address)
- get_customer_profile_crm(customer_id, email)
- create_support_ticket_erp(issue_type, description, priority)
- check_product_availability(product_name, store_location)
- schedule_installation(order_number, preferred_date, time_slot)
- process_warranty_claim(product_id, issue_description)
```

#### `agent_helpers.py`

Key functions:
- `extract_context_from_response()`: Extracts citations from File Search/Azure AI Search
- `execute_agent_query()`: Executes queries with iterative tool calling
- `schema_to_tool_definition()`: Converts schemas to evaluator format
- `build_message_object()`: Creates properly formatted message objects

**Critical Format**: Returns response as **message array** with:
- Tool call messages: `{"type": "tool_call", "tool_call_id": "...", "name": "...", "arguments": {...}}`
- Tool result messages: `{"type": "tool_result", "tool_result": {...}}`
- Text messages: `{"type": "text", "text": "..."}`

#### `schema_mappings.py`

Official Azure SDK schema mappings for evaluators. Defines:
- `EVALUATOR_DATA_SOURCE_CONFIGS`: Schema requirements per evaluator
- `EVALUATOR_DATA_MAPPINGS`: Data mapping templates

### Dataset Schema

Required fields in JSONL dataset:

```json
{
  "query": "User's question (string or array)",
  "response": [
    {
      "createdAt": "ISO timestamp",
      "run_id": "unique run identifier",
      "role": "assistant|tool",
      "content": [{"type": "tool_call|tool_result|text", ...}],
      "tool_call_id": "optional, for tool messages"
    }
  ],
  "context": "Supporting information from searches",
  "tool_definitions": [
    {
      "type": "function",
      "name": "function_name",
      "description": "what it does",
      "parameters": {...}
    }
  ],
  "tool_calls": [
    {
      "type": "function_call|file_search|azure_ai_search",
      "tool_call_id": "unique id",
      "name": "tool name",
      "arguments": {...}
    }
  ],
  "ground_truth": "Optional expected response"
}
```

## 🎓 Advanced Usage

### Custom Evaluators

Add custom evaluators by extending `build_testing_criteria()` in `run_evaluation_with_dataset.py`:

```python
testing_criteria.append({
    "type": "azure_ai_evaluator",
    "name": "custom_evaluator_name",
    "evaluator_name": "builtin.custom_evaluator_name",
    "data_mapping": {
        "query": "{{item.query}}",
        "response": "{{item.response}}",
        # Add required fields
    },
    "initialization_parameters": {"deployment_name": model_deployment_name},
})
```

### Filtering Evaluators

Run specific evaluators only:

```python
# In run_evaluation_with_dataset.py, modify evaluator_names list:
evaluator_names = [
    "tool_call_accuracy",
    "task_completion",
    "coherence",
    # Only these will run
]
```

### Multiple Dataset Versions

Track dataset evolution:

```bash
export DATASET_NAME=contoso-agent-eval-v2
export DATASET_VERSION=2
python evaluation/run_evaluation_with_dataset.py
```

## ✅ Best Practices

### 1. Response Format

**Always** use message array format for `response` field:
- ✅ **Correct**: `[{role, content, ...}, ...]` 
- ❌ **Wrong**: `"text string"`

Tool evaluators (`tool_input_accuracy`, `tool_output_utilization`) require parsing tool calls from message array.

### 2. Built-in vs Custom Tools

**Separate** built-in agent tools from custom function tools:
- ✅ **Include in response messages**: Function tools with definitions in `tool_definitions`
- ❌ **Exclude from response messages**: File Search, Azure AI Search (built-in, no definitions)
- ✅ **Track in tool_calls field**: All tool types for reference

### 3. Tool Definitions

**Include** all available function tools in `tool_definitions`:
- Use `schema_to_tool_definition()` to convert from tool schemas
- Tool evaluators validate calls against these definitions
- Missing definitions cause "unexpected parameter" errors

### 4. Dataset Quality

**Generate** realistic test data:
- Cover success and failure scenarios
- Include multi-turn conversations
- Test edge cases (missing info, errors)
- Validate data format before evaluation

### 5. Iterative Tool Calling

**Capture** all iterations (up to 5):
- Track tool calls across multiple rounds
- Include all tool results in message array
- Build complete conversation history

### 6. Evaluation Comparison

**Use same evaluation ID** for comparing runs:
- Set `EVAL_ID` environment variable
- Keeps runs under same evaluation
- Enables side-by-side comparison in Azure AI Studio

## 🐛 Troubleshooting

### Issue: "No tool_call found in response"

**Cause**: Response is string instead of message array  
**Fix**: Ensure `agent_helpers.py` returns response as message array with tool_call objects

### Issue: "Unexpected parameter 'queries' for file_search"

**Cause**: Built-in tools included in response messages without definitions  
**Fix**: Exclude `file_search` and `azure_ai_search` from response message content (only track in `tool_calls`)

### Issue: "Missing input for tool_definitions"

**Cause**: Dataset missing `tool_definitions` field  
**Fix**: Regenerate dataset with updated `agent_helpers.py` that includes `schema_to_tool_definition()`

### Issue: Evaluation stuck in "in_progress"

**Cause**: Large dataset or API throttling  
**Fix**: 
- Wait longer (10+ items can take 5-10 minutes)
- Check Azure AI Studio for detailed status
- Verify model deployment is active

## 📚 Additional Resources

- [Azure AI Projects SDK Documentation](https://learn.microsoft.com/azure/ai-services/agents/)
- [Azure AI Evaluators Guide](https://learn.microsoft.com/azure/ai-services/agents/how-to/evaluation)
- [Official SDK Samples](https://github.com/Azure/azure-sdk-for-python/tree/main/sdk/ai/azure-ai-projects/samples/evaluations)

## 🤝 Contributing

When adding new features:
1. Follow the modular architecture pattern
2. Use official Azure SDK patterns from `schema_mappings.py`
3. Validate against sample files for correct format
4. Test with both success and failure scenarios
5. Document new evaluators or workflows in this README

## 📄 License

This evaluation framework follows the same license as the parent project.

---

**Last Updated**: February 2026  
**Azure AI Projects SDK Version**: >=2.0.0b1  
**Supported Agent Types**: PromptAgentDefinition with Function Tools, File Search, Azure AI Search
