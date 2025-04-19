import os
import logging
import boto3
from utils import create_dynamodb_table, ASSESSMENT_TABLE_NAME, ANALYSIS_TEMPLATES_TABLE_NAME, JOB_BANK_TABLE_NAME

# Configure logging
logger = logging.getLogger("app-init")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

def handler(event, context):
    """
    Lambda function to initialize resources when the application is first deployed.
    This function can be called manually or as part of the deployment process.
    """
    logger.info("Initializing application resources")
    
    # Create DynamoDB tables if they don't exist
    tables_to_create = [ASSESSMENT_TABLE_NAME, ANALYSIS_TEMPLATES_TABLE_NAME, JOB_BANK_TABLE_NAME]
    created_tables = []
    
    try:
        for table_name in tables_to_create:
            table = create_dynamodb_table(table_name)
            if table:
                created_tables.append(table_name)
                logger.info(f"DynamoDB table '{table_name}' created")
            else:
                logger.info(f"DynamoDB table '{table_name}' already exists")
        
        logger.info("All DynamoDB tables are ready")
    except Exception as e:
        logger.error(f"Error creating DynamoDB tables: {e}")
        raise
    
    return {
        'statusCode': 200,
        'body': f"Application resources initialized successfully. Tables ready: {', '.join(created_tables or tables_to_create)}"
    }

if __name__ == "__main__":
    # For local testing
    handler(None, None) 