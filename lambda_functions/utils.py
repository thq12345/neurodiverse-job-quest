import os
import json
import uuid
import boto3
from datetime import datetime
from dotenv import load_dotenv
from typing import Dict, List, Any, Optional

# Load environment variables
load_dotenv()

# Initialize AWS clients
def get_dynamodb_client():
    """Create and return a DynamoDB resource client"""
    return boto3.resource(
        'dynamodb',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )

def get_s3_client():
    """Create and return an S3 client"""
    return boto3.client(
        's3',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )

def get_bedrock_client():
    """Create and return a Bedrock client"""
    return boto3.client(
        'bedrock-agent-runtime',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name="us-east-1"
    )

# DynamoDB table configuration
ASSESSMENT_TABLE_NAME = "Assessments"
ANALYSIS_TEMPLATES_TABLE_NAME = "AnalysisTemplates"
JOB_BANK_TABLE_NAME = "JobBank"
KNOWLEDGE_BASE_ID = "ILPMNFRVOC"

# DynamoDB helpers
def create_dynamodb_table(table_name: str):
    """Create DynamoDB table if it doesn't exist"""
    dynamodb = get_dynamodb_client()
    
    # Check if table exists
    existing_tables = [table.name for table in dynamodb.tables.all()]
    if table_name in existing_tables:
        return
    
    # Create table with on-demand capacity
    if table_name == ASSESSMENT_TABLE_NAME:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand mode
        )
    elif table_name == ANALYSIS_TEMPLATES_TABLE_NAME:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'template_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'template_id',
                    'AttributeType': 'S'
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand mode
        )
    elif table_name == JOB_BANK_TABLE_NAME:
        table = dynamodb.create_table(
            TableName=table_name,
            KeySchema=[
                {
                    'AttributeName': 'job_id',
                    'KeyType': 'HASH'  # Partition key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'job_id',
                    'AttributeType': 'N'
                }
            ],
            BillingMode='PAY_PER_REQUEST'  # On-demand mode
        )
    
    # Wait until the table exists
    table.meta.client.get_waiter('table_exists').wait(TableName=table_name)
    return table

def save_assessment(assessment_data: Dict[str, Any]) -> str:
    """Save assessment data to DynamoDB"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table(ASSESSMENT_TABLE_NAME)
    
    # Generate ID if not provided
    if 'id' not in assessment_data:
        assessment_data['id'] = str(uuid.uuid4())
    
    # Add timestamp if not provided
    if 'created_at' not in assessment_data:
        assessment_data['created_at'] = datetime.utcnow().isoformat()
    
    # Convert any non-serializable objects to strings
    for key, value in assessment_data.items():
        if isinstance(value, (dict, list)):
            assessment_data[key] = json.dumps(value)
    
    table.put_item(Item=assessment_data)
    return assessment_data['id']

def get_assessment(assessment_id: str) -> Optional[Dict[str, Any]]:
    """Retrieve assessment data from DynamoDB"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table(ASSESSMENT_TABLE_NAME)
    
    response = table.get_item(Key={'id': assessment_id})
    return response.get('Item')

def update_assessment(assessment_id: str, update_data: Dict[str, Any]) -> bool:
    """Update an existing assessment in DynamoDB"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table(ASSESSMENT_TABLE_NAME)
    
    # Create update expression
    update_expression = "SET "
    expression_attribute_values = {}
    
    for key, value in update_data.items():
        update_expression += f"#{key} = :{key}, "
        expression_attribute_values[f":{key}"] = value
    
    # Remove trailing comma and space
    update_expression = update_expression[:-2]
    
    # Create expression attribute names
    expression_attribute_names = {f"#{key}": key for key in update_data.keys()}
    
    try:
        table.update_item(
            Key={'id': assessment_id},
            UpdateExpression=update_expression,
            ExpressionAttributeValues=expression_attribute_values,
            ExpressionAttributeNames=expression_attribute_names
        )
        return True
    except Exception as e:
        print(f"Error updating assessment: {e}")
        return False

def list_assessments(limit: int = 50) -> List[Dict[str, Any]]:
    """List assessments from DynamoDB, sorted by creation date"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table(ASSESSMENT_TABLE_NAME)
    
    response = table.scan(Limit=limit)
    items = response.get('Items', [])
    
    # Sort by created_at date (newest first)
    items.sort(key=lambda x: x.get('created_at', ''), reverse=True)
    
    return items

def get_template_by_id(template_id: str) -> Optional[Dict[str, Any]]:
    """Get analysis template by ID"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table(ANALYSIS_TEMPLATES_TABLE_NAME)
    
    response = table.get_item(Key={'template_id': template_id})
    return response.get('Item')

def get_job_by_id(job_id: int) -> Optional[Dict[str, Any]]:
    """Get job from JobBank by ID"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table(JOB_BANK_TABLE_NAME)
    
    response = table.get_item(Key={'job_id': job_id})
    return response.get('Item')

def get_jobs_by_ids(job_ids: List[int]) -> List[Dict[str, Any]]:
    """Get multiple jobs by IDs"""
    dynamodb = get_dynamodb_client()
    table = dynamodb.Table(JOB_BANK_TABLE_NAME)
    
    jobs = []
    for job_id in job_ids:
        try:
            response = table.get_item(Key={'job_id': job_id})
            if 'Item' in response:
                jobs.append(response['Item'])
        except Exception as e:
            print(f"Error getting job {job_id}: {e}")
    
    return jobs

# Helper for API responses
def create_response(status_code: int, body: Any) -> Dict[str, Any]:
    """Create a standardized API response"""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*',
            'Access-Control-Allow-Credentials': True
        },
        'body': json.dumps(body) if isinstance(body, (dict, list)) else body
    }

# Questions data
QUESTIONS = [
    {
        "id": 1,
        "text": "How do you prefer to structure your workday?",
        "options": [
            ("A", "I thrive with a structured schedule"),
            ("B", "I prefer flexibility in my work hours")
        ]
    },
    {
        "id": 2,
        "text": "What type of workspace do you find most comfortable?",
        "options": [
            ("A", "Quiet and private spaces"),
            ("B", "Collaborative and open spaces")
        ]
    },
    {
        "id": 3,
        "text": "How comfortable are you with frequent interactions with colleagues?",
        "options": [
            ("A", "Prefer minimal interactions"),
            ("B", "Comfortable with regular teamwork"),
            ("C", "Enjoy leading or coordinating teams")
        ]
    },
    {
        "id": 4,
        "text": "Do you prefer tasks that are:",
        "options": [
            ("A", "Highly detailed and focused"),
            ("B", "Creative and innovative"),
            ("C", "A balance of both")
        ]
    },
    {
        "id": 5,
        "text": "Is there anything else we should know about you? (Optional)",
        "type": "free_response",
        "optional": True
    }
] 