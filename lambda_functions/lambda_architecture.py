"""
Lambda Architecture Overview

This file provides documentation about the Lambda functions architecture,
API Gateway integration, and how the different components interact.
"""

import logging
from typing import Dict, Any

# Configure logging
logger = logging.getLogger("lambda-architecture")
logger.setLevel(logging.INFO)

def describe_architecture() -> Dict[str, Any]:
    """
    Returns a description of the Lambda architecture and file interactions.
    """
    architecture = {
        "lambda_functions": {
            "questionnaire_api": {
                "handler": "questionnaire_api.handler",
                "purpose": "Handles questionnaire-related API endpoints",
                "api_routes": [
                    {
                        "path": "/questionnaire",
                        "method": "GET",
                        "description": "Returns the list of questionnaire questions and options"
                    },
                    {
                        "path": "/submit_questionnaire",
                        "method": "POST",
                        "description": "Accepts questionnaire answers and stores them in DynamoDB"
                    }
                ],
                "dependencies": ["utils.py", "models.py"]
            },
            "results_api": {
                "handler": "results_api.handler",
                "purpose": "Handles analysis results and job recommendations",
                "api_routes": [
                    {
                        "path": "/results/{assessment_id}",
                        "method": "GET",
                        "description": "Retrieves or generates analysis results for a given assessment ID"
                    }
                ],
                "dependencies": [
                    "utils.py", 
                    "models.py", 
                    "job_analyzer.py", 
                    "response_evaluator.py", 
                    "analysis_templates.py"
                ]
            },
            "app_init": {
                "handler": "app_init.handler",
                "purpose": "Initializes application resources at deployment time",
                "api_routes": [],  # No API routes, called during deployment
                "dependencies": ["utils.py"]
            }
        },
        "api_gateway_integration": {
            "description": "The API Gateway routes HTTP requests to the appropriate Lambda functions",
            "routes": [
                {
                    "path": "/questionnaire",
                    "method": "GET",
                    "lambda": "questionnaire_api.handler"
                },
                {
                    "path": "/submit_questionnaire",
                    "method": "POST",
                    "lambda": "questionnaire_api.handler"
                },
                {
                    "path": "/results/{assessment_id}",
                    "method": "GET",
                    "lambda": "results_api.handler"
                }
            ]
        },
        "file_interactions": {
            "utils.py": {
                "description": "Contains utility functions and AWS client initialization",
                "provides": [
                    "DynamoDB client functions (get_dynamodb_client)",
                    "S3 client functions (get_s3_client)",
                    "Bedrock client functions (get_bedrock_client)",
                    "Database helper functions (save_assessment, get_assessment, update_assessment)",
                    "Table creation function (create_dynamodb_table)",
                    "Constants (QUESTIONS, ASSESSMENT_TABLE_NAME)"
                ],
                "used_by": ["questionnaire_api.py", "results_api.py", "app_init.py"]
            },
            "models.py": {
                "description": "Contains Pydantic models for data validation",
                "provides": [
                    "Assessment model (for storing questionnaire responses)",
                    "AnalysisResult model (for analysis output)",
                    "JobRecommendation model (for job recommendations)"
                ],
                "used_by": ["questionnaire_api.py", "results_api.py"]
            },
            "questionnaire_api.py": {
                "description": "FastAPI application for questionnaire endpoints",
                "provides": [
                    "GET /questionnaire endpoint",
                    "POST /submit_questionnaire endpoint",
                    "Lambda handler function"
                ],
                "uses": ["utils.py", "models.py"]
            },
            "results_api.py": {
                "description": "FastAPI application for analysis and results endpoints",
                "provides": [
                    "GET /results/{assessment_id} endpoint",
                    "Lambda handler function",
                    "Analysis and recommendation functions"
                ],
                "uses": [
                    "utils.py", 
                    "models.py", 
                    "job_analyzer.py", 
                    "response_evaluator.py", 
                    "analysis_templates.py"
                ]
            },
            "app_init.py": {
                "description": "Lambda function to initialize application resources",
                "provides": [
                    "DynamoDB table creation",
                    "Initialization checks"
                ],
                "uses": ["utils.py"]
            },
            "job_analyzer.py": {
                "description": "Contains logic for analyzing job fit and providing recommendations",
                "provides": ["Job analysis functions", "Recommendation generation"],
                "used_by": ["results_api.py"]
            },
            "response_evaluator.py": {
                "description": "Evaluates free-text responses to enhance analysis",
                "provides": ["Free-text response evaluation"],
                "used_by": ["results_api.py"]
            },
            "analysis_templates.py": {
                "description": "Contains template analyses based on questionnaire answer combinations",
                "provides": ["Template analyses based on answer combinations"],
                "used_by": ["results_api.py"]
            }
        },
        "deployment": {
            "description": "The application is deployed using AWS SAM/CloudFormation",
            "template": "template.yaml",
            "resources": [
                "DynamoDB Table (Assessments)",
                "API Gateway (NeurodiverseJobQuestApi)",
                "Lambda Functions (InitFunction, QuestionnaireFunction, ResultsFunction)"
            ]
        }
    }
    
    return architecture

def get_api_gateway_mapping():
    """
    Returns the mapping between API Gateway routes and Lambda functions.
    This can be used to verify the proper configuration.
    """
    return {
        "/questionnaire": {
            "GET": "questionnaire_api.handler"
        },
        "/submit_questionnaire": {
            "POST": "questionnaire_api.handler"
        },
        "/results/{assessment_id}": {
            "GET": "results_api.handler"
        }
    }

if __name__ == "__main__":
    import json
    # Pretty print the architecture when run directly
    print(json.dumps(describe_architecture(), indent=2)) 