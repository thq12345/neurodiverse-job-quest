"""
Template management for work environment analyses.
This file contains functions to load and insert analysis templates into DynamoDB.
"""
import boto3
from boto3.dynamodb.conditions import Key
import json
import os
import decimal

# Helper class for JSON serialization of Decimal types
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            return str(o)
        return super(DecimalEncoder, self).default(o)

# Initialize DynamoDB
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
table = dynamodb.Table('AnalysisTemplates')

# Helper function to get analysis for a specific template ID
def get_analysis_by_id(template_id):
    """Get the template for a specific ID."""
    try:
        response = table.get_item(
            Key={
                'template_id': template_id
            }
        )
        item = response.get('Item')
        if item and 'recommended_jobs' in item:
            # Convert job IDs to plain integers/strings
            item['recommended_jobs'] = json.loads(item['recommended_jobs'])
        return item
    except Exception as e:
        print(f"Error retrieving analysis: {str(e)}")
        return None

# Helper function to get analysis for a specific combination of answers
def get_analysis_for_combination(q1, q2, q3, q4):
    """Get the pre-computed analysis for a specific answer combination."""
    template_id = f"{q1}{q2}{q3}{q4}"
    try:
        response = table.get_item(
            Key={
                'template_id': template_id
            }
        )
        item = response.get('Item')
        if item and 'recommended_jobs' in item:
            # Convert job IDs to plain integers/strings
            item['recommended_jobs'] = json.loads(item['recommended_jobs'])
        return item
    except Exception as e:
        print(f"Error retrieving analysis for combination {template_id}: {str(e)}")
        return None

# Step 1: Clear all existing items
def clear_table():
    """Clear all existing items from the DynamoDB table."""
    print("Clearing existing items...")
    response = table.scan()
    data = response.get('Items', [])

    with table.batch_writer() as batch:
        for item in data:
            batch.delete_item(Key={'template_id': item['template_id']})
    print(f"Deleted {len(data)} item(s).")

# Step 2: Insert new cleaned data from analysis-bank.json
def insert_templates(templates_dict):
    """Insert templates into DynamoDB table."""
    print(f"Inserting {len(templates_dict)} templates into DynamoDB...")
    inserted = 0
    
    for template_id, template_data in templates_dict.items():
        try:
            # Store recommended_jobs as a JSON string to avoid DynamoDB type issues
            recommended_jobs_json = json.dumps(template_data['recommended_jobs'])
            
            # Create the item with all fields
            item = {
                'template_id': template_id,
                'work_style_description': template_data['work_style']['description'],
                'work_style_explanation': template_data['work_style']['explanation'],
                'environment_description': template_data['environment']['description'],
                'environment_explanation': template_data['environment']['explanation'],
                'interaction_level_description': template_data['interaction_level']['description'],
                'interaction_level_explanation': template_data['interaction_level']['explanation'],
                'task_preference_description': template_data['task_preference']['description'],
                'task_preference_explanation': template_data['task_preference']['explanation'],
                'recommended_jobs': recommended_jobs_json  # Store as JSON string
            }
            
            # Put the item in the table
            table.put_item(Item=item)
            inserted += 1
            
            if inserted % 25 == 0:
                print(f"Inserted {inserted} templates...")
                
        except Exception as e:
            print(f"Error inserting template {template_id}: {str(e)}")
    
    print(f"Successfully inserted {inserted} templates into DynamoDB.")
    return inserted

def load_templates(file_path='contents/analysis-bank.json'):
    """Load analysis templates from JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as file:
            templates_dict = json.load(file)
            print(f"Loaded templates from {file_path} with {len(templates_dict)} entries")
            return templates_dict
    except Exception as e:
        print(f"Error loading templates from {file_path}: {str(e)}")
        return {}

# Run when this script is executed directly
if __name__ == "__main__":
    # Load templates from JSON file
    templates_dict = load_templates()
    clear_table()
    # Insert templates into DynamoDB
    inserted = insert_templates(templates_dict)
    print(f"Inserted {inserted} templates into DynamoDB.")
