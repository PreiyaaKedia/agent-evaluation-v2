# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

"""
DESCRIPTION:
    Main script to generate comprehensive agent test dataset.
    Creates an AI agent with Azure AI Search, File Search, and Function Tools.

USAGE:
    python evaluation/generate_agent_test_dataset.py

    Set environment variables:
    1) AZURE_AI_PROJECT_ENDPOINT
    2) AZURE_AI_MODEL_DEPLOYMENT_NAME
    3) AI_SEARCH_INDEX_NAME (optional)
    4) AI_SEARCH_PROJECT_CONNECTION_ID (optional)
"""

import os
import sys
import json
import time
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    PromptAgentDefinition,
    FileSearchTool,
    AzureAISearchAgentTool,
    AzureAISearchToolResource,
    AISearchIndexResource,
    AzureAISearchQueryType,
)

from tool_schemas import create_function_tools
from agent_config import AGENT_INSTRUCTIONS, TEST_QUERIES, DOCUMENT_PATHS
from agent_helpers import execute_agent_query

load_dotenv()


def create_vector_store_with_documents(openai_client):
    """Create vector store and upload documents for File Search."""
    print("\nCreating vector store for File Search...")
    vector_store = openai_client.vector_stores.create(name="ContosoElectronicsDocuments")
    print(f"✓ Vector store created: {vector_store.id}")
    
    # Upload documents
    uploaded_files = []
    for doc_path in DOCUMENT_PATHS:
        if os.path.exists(doc_path):
            try:
                file = openai_client.vector_stores.files.upload_and_poll(
                    vector_store_id=vector_store.id,
                    file=open(doc_path, "rb")
                )
                uploaded_files.append(file.id)
                print(f"  ✓ Uploaded: {os.path.basename(doc_path)} (ID: {file.id})")
            except Exception as e:
                print(f"  ✗ Failed to upload {doc_path}: {e}")
        else:
            print(f"  ⚠ Document not found: {doc_path}")
    
    return vector_store, uploaded_files


def create_agent_tools(openai_client, search_index_name=None, search_connection_id=None):
    """Create all agent tools: Function Tools, File Search, and Azure AI Search."""
    # Function tools
    function_tools = create_function_tools()
    print(f"✓ Created {len(function_tools)} function tools")
    
    # File Search tool
    vector_store, uploaded_files = create_vector_store_with_documents(openai_client)
    file_search_tool = FileSearchTool(vector_store_ids=[vector_store.id])
    print(f"✓ FileSearchTool created with {len(uploaded_files)} documents")
    
    # Combine all tools
    all_tools = function_tools + [file_search_tool]
    
    # Azure AI Search tool (optional)
    if search_index_name and search_connection_id:
        azure_search_tool = AzureAISearchAgentTool(
            azure_ai_search=AzureAISearchToolResource(
                indexes=[
                    AISearchIndexResource(
                        project_connection_id=search_connection_id,
                        index_name=search_index_name,
                        query_type=AzureAISearchQueryType.SIMPLE,
                    ),
                ]
            )
        )
        all_tools.append(azure_search_tool)
        print(f"✓ AzureAISearchAgentTool created (index: {search_index_name})")
    else:
        print("⚠ Azure AI Search not configured (set AI_SEARCH_INDEX_NAME and AI_SEARCH_PROJECT_CONNECTION_ID)")
    
    return all_tools, vector_store.id, uploaded_files


def generate_test_dataset(client, agent_name, queries):
    """Generate test dataset by executing queries."""
    print("\n" + "="*80)
    print("Generating Test Dataset")
    print("="*80)
    
    test_data = []
    for query in queries:
        try:
            result = execute_agent_query(client, agent_name, query)
            test_data.append(result)
            time.sleep(1)  # Rate limiting
        except Exception as e:
            print(f"Error processing query: {e}")
            continue
    
    return test_data


def save_dataset(test_data, output_file="evaluation/generated_test_dataset.jsonl"):
    """Save test data to JSONL file."""
    with open(output_file, 'w') as f:
        for item in test_data:
            f.write(json.dumps(item) + '\n')
    
    print(f"\n✓ Generated {len(test_data)} test cases")
    print(f"✓ Saved to: {output_file}")
    return output_file


def cleanup_resources(project_client, openai_client, agent, vector_store_id):
    """Clean up agent and vector store."""
    print("\nCleaning up...")
    try:
        project_client.agents.delete_version(agent_name=agent.name, agent_version=agent.version)
        print("✓ Agent deleted")
        
        openai_client.vector_stores.delete(vector_store_id=vector_store_id)
        print("✓ Vector store deleted")
    except Exception as e:
        print(f"⚠ Cleanup warning: {e}")


def main():
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT", os.environ.get("AZURE_EXISTING_AIPROJECT_ENDPOINT"))
    model_deployment_name = os.environ.get("AGENT_MODEL_DEPLOYMENT_NAME", "gpt-4.1")
    search_index_name = os.environ.get("AI_SEARCH_INDEX_NAME")
    search_connection_id = os.environ.get("AI_SEARCH_PROJECT_CONNECTION_ID")
    
    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=endpoint, credential=credential) as project_client,
        project_client.get_openai_client() as client,
    ):
        print("\n" + "="*80)
        print("Creating Comprehensive Contoso Electronics Agent")
        print("="*80)
        
        # Create all tools
        all_tools, vector_store_id, uploaded_files = create_agent_tools(
            client,
            search_index_name,
            search_connection_id
        )
        
        # Create agent
        agent = project_client.agents.create_version(
            agent_name="ContosoElectronicsAgent",
            definition=PromptAgentDefinition(
                model=model_deployment_name,
                instructions=AGENT_INSTRUCTIONS,
                tools=all_tools,
            ),
        )
        print(f"✓ Agent created: {agent.name} (version: {agent.version})")
        
        # Generate test dataset
        test_data = generate_test_dataset(client, agent.name, TEST_QUERIES)
        
        # Save dataset
        output_file = save_dataset(test_data)
        
        # Cleanup
        cleanup_resources(project_client, client, agent, vector_store_id)
        
        print("\n" + "="*80)
        print("COMPLETE")
        print("="*80)
        print(f"Generated dataset: {output_file}")
        print("This dataset can be used with comprehensive_agent_evaluation.py")


if __name__ == "__main__":
    main()
