"""
Generate cluster insights from evaluation runs.
Analyzes evaluation results to identify patterns and clusters in agent performance.
"""

import os
import sys
import time
from pprint import pprint
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.ai.projects import AIProjectClient
from azure.ai.projects.models import (
    Insight,
    EvaluationRunClusterInsightsRequest,
    InsightModelConfiguration,
    OperationState,
)

# Add current directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv()


def generate_cluster_insights(
    project_client,
    eval_id: str,
    run_ids: list[str],
    model_deployment_name: str,
    display_name: str = "Contoso Agent Evaluation Cluster Analysis"
):
    """
    Generate cluster insights from evaluation runs.
    
    Args:
        project_client: AIProjectClient instance
        eval_id: The evaluation ID
        run_ids: List of evaluation run IDs to analyze
        model_deployment_name: The model deployment to use for analysis
        display_name: Display name for the insight generation
    
    Returns:
        Generated cluster insight object
    """
    print("\n" + "=" * 80)
    print("Generating Cluster Insights")
    print("=" * 80)
    print(f"Evaluation ID: {eval_id}")
    print(f"Run IDs: {', '.join(run_ids)}")
    print(f"Model: {model_deployment_name}")
    print()
    
    # Start cluster insight generation
    cluster_insight = project_client.insights.generate(
        Insight(
            display_name=display_name,
            request=EvaluationRunClusterInsightsRequest(
                eval_id=eval_id,
                run_ids=run_ids,
                model_configuration=InsightModelConfiguration(
                    model_deployment_name=model_deployment_name
                ),
            ),
        )
    )
    
    print(f"✓ Started insight generation (ID: {cluster_insight.id})")
    print()
    
    # Poll for completion
    print("Waiting for cluster insights to be generated...")
    while cluster_insight.state not in [OperationState.SUCCEEDED, OperationState.FAILED]:
        time.sleep(5)
        cluster_insight = project_client.insights.get(id=cluster_insight.id)
        print(f"  Status: {cluster_insight.state}")
    
    print()
    
    if cluster_insight.state == OperationState.SUCCEEDED:
        print("=" * 80)
        print("✓ Cluster Insights Generated Successfully!")
        print("=" * 80)
        print()
        print("Cluster Insight Details:")
        print("-" * 80)
        pprint(cluster_insight)
        print()
        return cluster_insight
    else:
        print("=" * 80)
        print("✗ Cluster Insight Generation Failed")
        print("=" * 80)
        if hasattr(cluster_insight, 'error'):
            print(f"Error: {cluster_insight.error}")
        return None


def main():
    """
    Main function to demonstrate cluster insight generation.
    
    Usage:
    1. Set AZURE_AI_PROJECT_ENDPOINT in .env
    2. Set AZURE_AI_MODEL_DEPLOYMENT_NAME in .env
    3. Run an evaluation first using run_evaluation_with_dataset.py
    4. Copy the Evaluation ID and Run ID from the output
    5. Update eval_id and run_ids in this script
    6. Run: python evaluation/generate_cluster_insights.py
    """
    # Get configuration from environment
    endpoint = os.environ.get("AZURE_AI_PROJECT_ENDPOINT")
    model_deployment_name = os.environ.get("AZURE_AI_MODEL_DEPLOYMENT_NAME")
    
    if not endpoint:
        raise ValueError("AZURE_AI_PROJECT_ENDPOINT environment variable not set")
    if not model_deployment_name:
        raise ValueError("AZURE_AI_MODEL_DEPLOYMENT_NAME environment variable not set")
    
    # CONFIGURE THESE: Replace with your actual eval_id and run_ids from a completed evaluation
    # You can find these in the output of run_evaluation_with_dataset.py
    eval_id = "eval_342b6eec62d145af8f69dde3e3558516"  # Replace with your evaluation ID
    run_ids = ["evalrun_08c6f016297e4e06a79e1a16fc83f2f4"]  # Replace with your run ID(s)
    
    print("\n" + "=" * 80)
    print("Contoso Agent Evaluation - Cluster Insights Generation")
    print("=" * 80)
    print(f"Project Endpoint: {endpoint}")
    print(f"Model: {model_deployment_name}")
    print()
    
    with DefaultAzureCredential() as credential:
        with AIProjectClient(endpoint=endpoint, credential=credential) as project_client:
            # Generate cluster insights
            cluster_insight = generate_cluster_insights(
                project_client=project_client,
                eval_id=eval_id,
                run_ids=run_ids,
                model_deployment_name=model_deployment_name,
                display_name="Contoso Agent Performance Cluster Analysis"
            )
            
            if cluster_insight:
                print("=" * 80)
                print("INSIGHTS SUMMARY")
                print("=" * 80)
                
                # Extract and display key information
                if hasattr(cluster_insight, 'result'):
                    print("\nInsight Result:")
                    print(cluster_insight.result)
                
                if hasattr(cluster_insight, 'display_name'):
                    print(f"\nInsight Name: {cluster_insight.display_name}")
                
                if hasattr(cluster_insight, 'id'):
                    print(f"Insight ID: {cluster_insight.id}")
                
                print()
                print("=" * 80)
                print("You can view detailed insights in Microsoft Foundry portal.")
                print("=" * 80)


if __name__ == "__main__":
    main()
