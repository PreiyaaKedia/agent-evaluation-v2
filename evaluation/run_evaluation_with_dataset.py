# pylint: disable=line-too-long,useless-suppression
# ------------------------------------
# Copyright (c) Microsoft Corporation.
# Licensed under the MIT License.
# ------------------------------------

"""
DESCRIPTION:
    Run comprehensive agent evaluation using a generated dataset.
    This script uploads the generated_test_dataset.jsonl file as a Dataset
    and runs all agentic evaluators against it.
    
    Evaluators run:
    - Tool-related: tool_call_accuracy, tool_selection, tool_input_accuracy, 
                    tool_output_utilization, tool_call_success
    - Task-related: task_completion, task_adherence
    - Quality-related: coherence, fluency, relevance, groundedness, intent_resolution

USAGE:
    python evaluation/run_evaluation_with_dataset.py

    Before running:
    pip install "azure-ai-projects>=2.0.0b1" python-dotenv

    Set these environment variables:
    1) AZURE_AI_PROJECT_ENDPOINT - Required
    2) AZURE_AI_MODEL_DEPLOYMENT_NAME - Required (for evaluation)
    3) DATASET_FILE - Optional (default: evaluation/generated_test_dataset.jsonl)
    4) DATASET_NAME - Optional (default: auto-generated with timestamp)
    5) DATASET_VERSION - Optional (default: "1")
"""

import os
import sys
import time
from pprint import pprint
from datetime import datetime
from dotenv import load_dotenv

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import DatasetVersion
from openai.types.evals.create_eval_jsonl_run_data_source_param import (
    CreateEvalJSONLRunDataSourceParam,
    SourceFileID,
)
from openai.types.eval_create_params import DataSourceConfigCustom
from schema_mappings import EVALUATOR_DATA_SOURCE_CONFIGS, EVALUATOR_DATA_MAPPINGS

load_dotenv()


def build_testing_criteria(model_deployment_name, evaluator_names=None):
    """Build testing criteria for specified evaluators using schema mappings."""
    # Default to all evaluators if none specified
    if evaluator_names is None:
        evaluator_names = [
            "tool_call_accuracy",
            "tool_selection",
            "tool_input_accuracy",
            "tool_output_utilization",
            "tool_call_success",
            "task_completion",
            "task_adherence",
            "coherence",
            "fluency",
            "relevance",
            "groundedness",
            "intent_resolution",
        ]
    
    testing_criteria = []
    for evaluator_name in evaluator_names:
        if evaluator_name not in EVALUATOR_DATA_MAPPINGS:
            print(f"⚠ Warning: Unknown evaluator '{evaluator_name}', skipping")
            continue
        
        testing_criteria.append({
            "type": "azure_ai_evaluator",
            "name": evaluator_name,
            "evaluator_name": f"builtin.{evaluator_name}",
            "data_mapping": EVALUATOR_DATA_MAPPINGS[evaluator_name],
            "initialization_parameters": {"deployment_name": model_deployment_name},
        })
    
    return testing_criteria


def main():
    endpoint = os.environ["AZURE_AI_PROJECT_ENDPOINT"]
    model_deployment_name = os.environ["AZURE_AI_MODEL_DEPLOYMENT_NAME"]
    
    # Optional: Use existing evaluation ID for comparing runs
    existing_eval_id = os.environ.get("EVAL_ID")  # Set this to compare runs under same evaluation
    
    # Get dataset file path
    script_dir = os.path.dirname(os.path.abspath(__file__))
    dataset_file = os.environ.get(
        "DATASET_FILE",
        os.path.join(script_dir, "generated_test_dataset.jsonl")
    )
    
    # Generate dataset name with timestamp if not provided
    dataset_name = os.environ.get(
        "DATASET_NAME",
        f"contoso-agent-eval-{datetime.utcnow().strftime('%Y-%m-%d_%H%M%S_UTC')}"
    )
    dataset_version = os.environ.get("DATASET_VERSION", "1")
    
    if not os.path.exists(dataset_file):
        print(f"❌ Error: Dataset file not found: {dataset_file}")
        print("Please run generate_agent_test_dataset.py first to create the dataset.")
        return
    
    with (
        DefaultAzureCredential() as credential,
        AIProjectClient(endpoint=endpoint, credential=credential) as project_client,
        project_client.get_openai_client() as client,
    ):
        print("\n" + "="*80)
        print("Uploading Dataset for Evaluation")
        print("="*80)
        
        # Upload dataset file
        print(f"Uploading file: {dataset_file}")
        dataset: DatasetVersion = project_client.datasets.upload_file(
            name=dataset_name,
            version=dataset_version,
            file_path=dataset_file,
        )
        print(f"✓ Dataset uploaded:")
        print(f"  - Name: {dataset.name}")
        print(f"  - Version: {dataset.version}")
        print(f"  - ID: {dataset.id}")
        
        # Use a unified schema that supports all evaluators
        # This is a superset of all evaluator schemas from schema_mappings.py
        unified_schema = {
            "type": "object",
            "properties": {
                "query": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
                "response": {"anyOf": [{"type": "string"}, {"type": "array", "items": {"type": "object"}}]},
                "context": {"type": "string"},
                "ground_truth": {"type": "string"},
                "tool_definitions": {"anyOf": [{"type": "object"}, {"type": "array", "items": {"type": "object"}}]},
                "tool_calls": {"anyOf": [{"type": "object"}, {"type": "array", "items": {"type": "object"}}]},
            },
            "required": ["query", "tool_definitions"],
        }
        
        # Configure data source
        data_source_config = DataSourceConfigCustom({
            "type": "custom",
            "item_schema": unified_schema,
            "include_sample_schema": True,
        })
        
        # Build testing criteria
        testing_criteria = build_testing_criteria(model_deployment_name)
        
        print("\n" + "="*80)
        if existing_eval_id:
            print("Using Existing Evaluation for Run Comparison")
            print("="*80)
            print(f"Evaluation ID: {existing_eval_id}")
            
            # Retrieve existing evaluation
            eval_object = client.evals.retrieve(existing_eval_id)
            print(f"✓ Retrieved evaluation:")
            print(f"  - Name: {eval_object.name}")
        else:
            print("Creating Evaluation")
            print("="*80)
            print(f"Evaluators: {len(testing_criteria)}")
            for criteria in testing_criteria:
                print(f"  - {criteria['name']}")
            
            # Create evaluation
            eval_object = client.evals.create(
                name=f"Contoso Agent Evaluation - {dataset_name}",
                data_source_config=data_source_config,
                testing_criteria=testing_criteria,  # type: ignore
            )
            print(f"\n✓ Evaluation created:")
            print(f"  - ID: {eval_object.id}")
            print(f"  - Name: {eval_object.name}")
        
        print("\n" + "="*80)
        print("Creating Evaluation Run")
        print("="*80)
        
        # Create evaluation run with dataset ID
        eval_run_object = client.evals.runs.create(
            eval_id=eval_object.id,
            name=f"run-{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}",
            metadata={
                "team": "contoso-electronics",
                "scenario": "comprehensive-agent-evaluation",
                "dataset_file": os.path.basename(dataset_file),
            },
            data_source=CreateEvalJSONLRunDataSourceParam(
                type="jsonl",
                source=SourceFileID(type="file_id", id=dataset.id if dataset.id else "")
            ),
        )
        print(f"✓ Evaluation run created:")
        print(f"  - Run ID: {eval_run_object.id}")
        print(f"  - Status: {eval_run_object.status}")
        
        print("\n" + "="*80)
        print("Waiting for Evaluation Run to Complete")
        print("="*80)
        
        # Poll for completion
        while True:
            run = client.evals.runs.retrieve(
                run_id=eval_run_object.id,
                eval_id=eval_object.id
            )
            
            if run.status == "completed":
                print("\n✓ Evaluation completed successfully!")
                
                # Get output items
                output_items = list(client.evals.runs.output_items.list(
                    run_id=run.id,
                    eval_id=eval_object.id
                ))
                
                print(f"\n📊 Evaluation Results ({len(output_items)} items):")
                print("="*80)
                
                # Aggregate scores by evaluator
                evaluator_scores = {}
                for item in output_items:
                    if hasattr(item, 'scores') and item.scores:
                        for score in item.scores:
                            if score.name not in evaluator_scores:
                                evaluator_scores[score.name] = []
                            if score.score is not None:
                                evaluator_scores[score.name].append(score.score)
                
                # Print average scores
                for evaluator_name, scores in sorted(evaluator_scores.items()):
                    if scores:
                        avg_score = sum(scores) / len(scores)
                        print(f"  {evaluator_name:30s}: {avg_score:.2f} (avg of {len(scores)} items)")
                    else:
                        print(f"  {evaluator_name:30s}: N/A")
                
                print(f"\n🔗 Report URL: {run.report_url}")
                break
                
            elif run.status == "failed":
                print(f"\n❌ Evaluation run failed!")
                print(f"Error: {run.error if hasattr(run, 'error') else 'Unknown error'}")
                break
            
            else:
                print(f"  Status: {run.status} ... waiting")
                time.sleep(10)
        
        print("\n" + "="*80)
        print("COMPLETE")
        print("="*80)
        print(f"Dataset: {dataset.name} (v{dataset.version})")
        print(f"Evaluation ID: {eval_object.id}")
        print(f"Run ID: {eval_run_object.id}")
        print(f"Report: {run.report_url if 'run' in locals() else 'N/A'}")


if __name__ == "__main__":
    main()
