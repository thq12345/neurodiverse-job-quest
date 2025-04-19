import os
import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_user_assessments_table():
    """Create the UserAssessments DynamoDB table if it doesn't exist"""
    
    print("Initializing DynamoDB table creation...")
    
    # Initialize AWS session
    aws_session = boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )
    
    # Create DynamoDB resource
    dynamodb = aws_session.resource('dynamodb')
    
    # Table name
    assessments_table_name = 'UserAssessments'
    
    # Check if table already exists
    existing_tables = [table.name for table in dynamodb.tables.all()]
    if assessments_table_name in existing_tables:
        print(f"Table '{assessments_table_name}' already exists.")
        return
    
    # Create the table
    print(f"Creating table '{assessments_table_name}'...")
    assessments_table = dynamodb.create_table(
        TableName=assessments_table_name,
        KeySchema=[
            {
                'AttributeName': 'assessment_id',
                'KeyType': 'HASH'  # Partition key
            }
        ],
        AttributeDefinitions=[
            {
                'AttributeName': 'assessment_id',
                'AttributeType': 'S'
            }
        ],
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    
    # Wait for the table to be created
    print(f"Waiting for table '{assessments_table_name}' to be created...")
    assessments_table.wait_until_exists()
    print(f"Table '{assessments_table_name}' created successfully!")

def create_analysis_templates_table():
    """Create the AnalysisTemplates DynamoDB table if it doesn't exist"""
    
    print("Checking AnalysisTemplates table...")
    
    # Initialize AWS session
    aws_session = boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )
    
    # Create DynamoDB resource
    dynamodb = aws_session.resource('dynamodb')
    
    # Table name
    analysis_templates_table_name = 'AnalysisTemplates'
    
    # Check if table already exists
    existing_tables = [table.name for table in dynamodb.tables.all()]
    if analysis_templates_table_name in existing_tables:
        print(f"Table '{analysis_templates_table_name}' already exists.")
        return
    
    # Create the table
    print(f"Creating table '{analysis_templates_table_name}'...")
    analysis_templates_table = dynamodb.create_table(
        TableName=analysis_templates_table_name,
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
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    
    # Wait for the table to be created
    print(f"Waiting for table '{analysis_templates_table_name}' to be created...")
    analysis_templates_table.wait_until_exists()
    print(f"Table '{analysis_templates_table_name}' created successfully!")

def create_job_bank_table():
    """Create the JobBank DynamoDB table if it doesn't exist"""
    
    print("Checking JobBank table...")
    
    # Initialize AWS session
    aws_session = boto3.Session(
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1"),
    )
    
    # Create DynamoDB resource
    dynamodb = aws_session.resource('dynamodb')
    
    # Table name
    job_bank_table_name = 'JobBank'
    
    # Check if table already exists
    existing_tables = [table.name for table in dynamodb.tables.all()]
    if job_bank_table_name in existing_tables:
        print(f"Table '{job_bank_table_name}' already exists.")
        return
    
    # Create the table
    print(f"Creating table '{job_bank_table_name}'...")
    job_bank_table = dynamodb.create_table(
        TableName=job_bank_table_name,
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
        ProvisionedThroughput={
            'ReadCapacityUnits': 5,
            'WriteCapacityUnits': 5
        }
    )
    
    # Wait for the table to be created
    print(f"Waiting for table '{job_bank_table_name}' to be created...")
    job_bank_table.wait_until_exists()
    print(f"Table '{job_bank_table_name}' created successfully!")

if __name__ == "__main__":
    print("Starting DynamoDB table creation script...")
    create_user_assessments_table()
    print("All tables created/verified successfully!") 