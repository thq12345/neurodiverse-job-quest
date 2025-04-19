import os
from dotenv import load_dotenv
load_dotenv() 

langtrace_api_key = os.environ.get("LANGTRACE_API_KEY")
from langtrace_python_sdk import langtrace
langtrace.init(api_key=langtrace_api_key)

from openai import OpenAI
import logging
import json
import sys
import boto3
import re
from response_evaluator import ResponseEvaluator
from job_analyzer import JobAnalyzer
import uuid
import time
import requests

# Initialize AWS session
aws_session = boto3.Session(
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION"),
)

# Create clients using the session
bedrock = aws_session.client('bedrock-agent-runtime', region_name='us-east-1')
knowledge_base_id = "ILPMNFRVOC"
s3 = aws_session.client('s3')

# Get DynamoDB table for storing assessments
dynamodb = aws_session.resource('dynamodb')
analysis_templates = dynamodb.Table('AnalysisTemplates')
assessments_table = dynamodb.Table('UserAssessments')

# ===== Logging Configuration =====
# Configure logging to show application messages but suppress framework noise
logging.basicConfig(level=logging.INFO)
logging.getLogger('werkzeug').setLevel(logging.ERROR)  # Suppress Flask/Werkzeug logs
logging.getLogger('sqlalchemy.engine').setLevel(logging.ERROR)  # Suppress SQL logs

# Create custom app logger with distinctive formatting
console_handler = logging.StreamHandler(sys.stdout)
formatter = logging.Formatter('\n>>> APP LOG: %(levelname)s - %(message)s')
console_handler.setFormatter(formatter)
app_logger = logging.getLogger('app')
app_logger.setLevel(logging.DEBUG)
app_logger.addHandler(console_handler)
app_logger.propagate = False  # Prevent duplicate logs

# Helper function for debug logging
def debug(message, value=None):
    """Log a debug message with optional value inspection"""
    if value is not None:
        app_logger.debug(f"{message}: {value}")
    else:
        app_logger.debug(message)
    sys.stdout.flush()  # Force immediate output
# ===== End Logging Configuration =====

# Check for API key in environment or use a placeholder for development
openai_api_key = os.environ.get("OPENAI_API_KEY")
if not openai_api_key:
    app_logger.warning("OpenAI API key not found - using mock responses for development")
    # Set to None to handle mock responses later
    openai_api_key = None

client = OpenAI(api_key=openai_api_key)


questions = [
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


# Main function to process questionnaire answers and return analysis and recommendations
def process_questionnaire_answers(answers):
    """Process questionnaire answers and return analysis and recommendations"""
    debug("Processing questionnaire answers")
    
    # Verify required questions are answered (now excluding q5 which is optional)
    required_questions = [f"q{i+1}" for i in range(len(questions)) 
                          if not (i+1 == 5 and 'optional' in questions[i] and questions[i]['optional'])]
    
    for req in required_questions:
        if req not in answers:
            return {
                "statusCode": 400,
                "body": json.dumps({
                    "error": f"Missing required question answer: {req}"
                })
            }
    
    # Prepare answers for AI analysis
    formatted_answers = {}
    parsed_answers = []
    
    for i, q in enumerate(questions):
        question_key = f"q{i+1}"
        
        # Skip optional questions that weren't answered
        if question_key not in answers and i+1 == 5 and 'optional' in q and q['optional']:
            continue
            
        answer_key = answers.get(question_key, "")
        
        # Store the answer key in formatted_answers dict for later use
        formatted_answers[question_key] = answer_key
        
        # Format for analysis text
        if 'type' in q and q['type'] == 'free_response':
            answer_text = answer_key  # Use the free response text directly
        else:
            answer_text = next((opt[1] for opt in q["options"] if opt[0] == answer_key), "Unknown")
        
        parsed_answers.append(f"Q: {q['text']}\nA: {answer_text}")
        
        # Log the answer
        if 'type' in q and q['type'] == 'free_response':
            app_logger.info(f"Q{i+1}: {q['text']} - Answer: {answer_key}")
        else:
            option_text = next((opt[1] for opt in q["options"] if opt[0] == answer_key), "Unknown")
            app_logger.info(f"Q{i+1}: {q['text']} - Option: {answer_key} - {option_text}")

    # Generate assessment ID
    assessment_id = str(uuid.uuid4())
    
    # Agents, RAGs, and LLMs - get analysis
    analysis_result = analyze_responses(formatted_answers)
    
    # Convert any HTML result to structured JSON if needed
    if isinstance(analysis_result, str) and analysis_result.strip().startswith('<div'):
        profile = extract_user_profile_from_analysis(analysis_result)
    else:
        # If it's already structured data, use it directly
        profile = analysis_result
        
    # Get job recommendations using both the profile and answers
    recommendations = get_job_recommendations(profile, formatted_answers)
    
    # Store results in DynamoDB
    try:
        debug(f"Storing assessment data for ID: {assessment_id}")
        assessments_table.put_item(
            Item={
                'assessment_id': assessment_id,
                'answers': json.dumps(formatted_answers),
                'profile': json.dumps(profile),
                'recommendations': json.dumps(recommendations),
                'created_at': int(time.time())
            }
        )
        debug("Successfully stored assessment data")
    except Exception as e:
        app_logger.error(f"Error storing assessment data: {str(e)}")
        # Continue even if storage fails - we can still return results
    
    # Return combined results (JSON only, no HTML)
    return {
        "statusCode": 200,
        "body": json.dumps({
            "assessment_id": assessment_id,
            "profile": profile,
            "recommendations": recommendations
        })
    }

# Lambda handler function
def lambda_handler(event, context):
    """AWS Lambda handler function"""
    
    # Log the incoming event
    debug("Lambda invoked with event", event)
    
    # Get HTTP method and path
    http_method = event.get('httpMethod', '')
    path = event.get('path', '')
    
    # Create path patterns for routing
    if http_method == 'GET' and path == '/questionnaire':
        # Return questionnaire data
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "questions": questions
            })
        }
    
    elif http_method == 'GET' and path == '/health':
        # Health check endpoint
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "status": "healthy"
            })
        }
    
    elif http_method == 'POST' and path == '/submit_questionnaire':
        # Process submitted questionnaire
        try:
            # Parse request body
            body = json.loads(event.get('body', '{}'))
            
            # Process answers and get results
            result = process_questionnaire_answers(body)
            
            # Add CORS headers to the response
            result["headers"] = {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            }
            
            return result
            
        except Exception as e:
            app_logger.error(f"Error processing questionnaire: {str(e)}")
            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "error": "Internal server error",
                    "detail": str(e)
                })
            }
    
    elif http_method == 'GET' and path.startswith('/results/'):
        # Get assessment results by ID
        try:
            assessment_id = path.split('/')[-1]
            
            # Retrieve the stored assessment from DynamoDB
            debug(f"Retrieving assessment with ID: {assessment_id}")
            response = assessments_table.get_item(
                Key={
                    'assessment_id': assessment_id
                }
            )
            
            # Check if assessment was found
            if 'Item' not in response:
                debug(f"Assessment ID {assessment_id} not found in database")
                return {
                    "statusCode": 404,
                    "headers": {
                        "Content-Type": "application/json",
                        "Access-Control-Allow-Origin": "*"
                    },
                    "body": json.dumps({
                        "error": "Assessment not found"
                    })
                }
            
            # Get the stored data
            item = response['Item']
            
            # Parse stored JSON strings
            if 'profile' in item and isinstance(item['profile'], str):
                item['profile'] = json.loads(item['profile'])
            
            if 'recommendations' in item and isinstance(item['recommendations'], str):
                item['recommendations'] = json.loads(item['recommendations'])
            
            # Return just the profile and recommendations data (not the HTML)
            result_data = {
                "assessment_id": assessment_id,
                "profile": item.get('profile', {}),
                "recommendations": item.get('recommendations', [])
            }
            
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps(result_data)
            }
            
        except Exception as e:
            app_logger.error(f"Error fetching results: {str(e)}")
            return {
                "statusCode": 500,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*"
                },
                "body": json.dumps({
                    "error": "Internal server error",
                    "detail": str(e)
                })
            }
    
    # Handle OPTIONS request for CORS
    elif http_method == 'OPTIONS':
        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Content-Type,X-Amz-Date,Authorization,X-Api-Key",
                "Access-Control-Allow-Methods": "GET,POST,OPTIONS"
            },
            "body": "{}"
        }
    
    # Return 404 for undefined routes
    else:
        return {
            "statusCode": 404,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*"
            },
            "body": json.dumps({
                "error": "Not found"
            })
        }

def analyze_responses(answers):
    debug("Starting response analysis")
    # Helper function to get analysis for a specific combination of answers
    def get_analysis_for_combination(q1, q2, q3, q4):
        """Get the pre-computed analysis for a specific answer combination."""
        template_id = f"{q1}{q2}{q3}{q4}"
        try:
            response = analysis_templates.get_item(
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
    # Import time module explicitly to avoid scope issues
    import time
    
    # Generate a trace ID for this analysis session
    trace_id = str(uuid.uuid4())
    
    # Extract the first 4 multiple-choice answers from the answers parameter
    mc_answers = []
    for i in range(4):  # First 4 questions are multiple choice
        answer_key = f"q{i+1}"
        if answer_key in answers:
            mc_answers.append(answers[answer_key])
        else:
            mc_answers.append(None)
    
    debug("Using pre-computed analysis for multiple choice answers")
    q1, q2, q3, q4 = mc_answers
    pre_computed_analysis = get_analysis_for_combination(q1, q2, q3, q4)
    
    if pre_computed_analysis:
        debug(f"Found pre-computed analysis for combination {q1}{q2}{q3}{q4}")
        
        # Normalize data structure to handle both nested and flattened formats
        normalized_analysis = normalize_analysis_data(pre_computed_analysis)
        
        # Get the free response answer (if provided)
        free_response = answers.get("q5", "")
        
        # Check if free response is empty or just whitespace
        if not free_response or not free_response.strip():
            debug("Free response is empty, skipping ResponseEvaluator")
            
            # Add default additional insights without calling ResponseEvaluator
            normalized_analysis["additional_insights"] = {
                "description": "No additional information provided",
                "explanation": "You did not provide any additional context about your work preferences."
            }
            
            # Record skipped metrics
            send_langtrace_metric(
                "Agent response_evaluator",
                "skipped_evaluation",
                "1",
                trace_id=str(uuid.uuid4()),
                metadata={
                    "reason": "empty_input"
                }
            )
            
            # Return the normalized analysis data directly (no HTML conversion)
            return normalized_analysis
        
        # Start time for metrics - only if we have non-empty free response
        start_time = time.time()
        
        # Initialize the CrewAI-based response evaluator
        evaluator = ResponseEvaluator(
            openai_client=client if openai_api_key else None,
            debug_func=debug
        )
        
        # Process the free response using the evaluator
        try:
            # Store original normalized_analysis for comparison
            original_additional_insights = normalized_analysis.get('additional_insights', {}).get('description', 'No additional insights') if normalized_analysis else {}
            
            # Call the evaluator
            normalized_analysis = evaluator.get_additional_insights(free_response, normalized_analysis)
            
            # Tool Call Accuracy metric (1 = success)
            tool_call_accuracy = 1
            
            # Agent Goal Accuracy metric - check if insights were added or modified
            goal_achieved = 0
            current_insights = normalized_analysis.get('additional_insights', {}).get('description', 'No additional insights')
            if current_insights != 'No additional insights' and current_insights != 'Additional information provided, but couldn\'t be processed':
                goal_achieved = 1
                
            # Calculate time taken
            time_taken = time.time() - start_time
            
            # Log metrics collection
            app_logger.info(f"Collecting metrics for ResponseEvaluator - tool_call_accuracy: {tool_call_accuracy}, agent_goal_accuracy: {goal_achieved}")
                
        except Exception as e:
            app_logger.error(f"Error in ResponseEvaluator: {str(e)}")
            tool_call_accuracy = 0
            goal_achieved = 0
            time_taken = time.time() - start_time
        
        # Send metrics to Langtrace
        # 1. Tool Call Accuracy
        send_langtrace_metric(
            "Agent response_evaluator",
            "tool_call_accuracy",
            tool_call_accuracy,
            trace_id=trace_id,
            metadata={
                "agent_name": "response_evaluator",
                "response_length": len(free_response),
                "time_taken": str(time_taken)
            }
        )
        
        # 2. Agent Goal Accuracy
        send_langtrace_metric(
            "Agent response_evaluator",
            "agent_goal_accuracy",
            goal_achieved,
            trace_id=trace_id,
            metadata={
                "agent_name": "response_evaluator",
                "response_length": len(free_response),
                "has_openai_client": str(openai_api_key is not None)
            }
        )
        
        # Return the normalized analysis data directly (no HTML conversion)
        return normalized_analysis
    
    # If no pre-computed analysis is found, return a default structure
    debug("No pre-computed analysis found, returning default structure")
    return {
        'work_style': {'description': 'Adaptable working style', 'explanation': 'You appear to have a flexible approach to work scheduling.'},
        'environment': {'description': 'Versatile environment preference', 'explanation': 'You can work in various workspace settings.'},
        'interaction_level': {'description': 'Balanced interaction style', 'explanation': 'You can work both independently and collaboratively.'},
        'task_preference': {'description': 'Diverse task orientation', 'explanation': 'You can handle both detail-oriented and creative tasks.'},
        'additional_insights': {'description': 'No additional insights', 'explanation': ''}
    }

# Function to send metrics to langtrace
def send_langtrace_metric(agent_name, metric_name, metric_value, trace_id=None, metadata=None):
    """
    Send a metric to langtrace
    
    Args:
        metric_name: Name of the metric
        metric_value: Value of the metric (will be converted to string)
        trace_id: Optional trace ID for grouping
        metadata: Optional metadata dictionary
    """
    if not langtrace_api_key:
        app_logger.warning("Langtrace API key not found, skipping metric tracking")
        return
        
    trace_id = trace_id or str(uuid.uuid4())
    str_value = str(metric_value)  # Convert to string as required
    
    # Prepare the payload
    current_time = int(time.time() * 1000000000)  # Current time in nanoseconds
    
    # Define attributes as an array of key-value pairs, which is what OpenTelemetry expects
    resource_attributes = [
        {"key": "service.name", "value": {"stringValue": "neurodiverse-job-quest"}},
        {"key": "service.version", "value": {"stringValue": "1.0.0"}}
    ]
    
    # Create span attributes as an array too
    span_attributes = [
        {"key": "metric.name", "value": {"stringValue": metric_name}},
        {"key": "metric.value", "value": {"stringValue": str_value}}
    ]
    
    # Add metadata as additional attributes if provided
    if metadata:
        metadata_str = json.dumps(metadata)
        span_attributes.append({"key": "metric.metadata", "value": {"stringValue": metadata_str}})
    
    payload = {
        "resourceSpans": [{
            "resource": {
                "attributes": resource_attributes
            },
            "scopeSpans": [{
                "spans": [{
                    "traceId": trace_id,
                    "spanId": str(uuid.uuid4()).replace('-', '')[:16],
                    "name": f"{agent_name} metrics: {metric_name}",
                    "kind": 1,
                    "startTimeUnixNano": str(current_time),
                    "endTimeUnixNano": str(current_time + 1000000),  # 1ms later
                    "attributes": span_attributes
                }]
            }]
        }]
    }
    
    # Send to Langtrace
    try:
        url = 'https://app.langtrace.ai/api/trace'
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'opentelemetry-python',
            'x-api-key': langtrace_api_key
        }
        
        app_logger.info(f"Sending {metric_name} metric to Langtrace: {str_value}")
        response = requests.post(url, headers=headers, json=payload)
        
        if response.status_code != 200:
            app_logger.error(f"Failed to send metric to Langtrace: {response.text}")
        else:
            app_logger.info(f"Successfully sent {metric_name} metric to Langtrace")
    except Exception as e:
        app_logger.error(f"Error sending metric to Langtrace: {str(e)}")

# DynamoDB data formatting
def normalize_analysis_data(analysis_data):
    """
    Normalize analysis data to ensure consistent structure between DynamoDB and local data
    
    Args:
        analysis_data: The analysis data from either local or DynamoDB source
        
    Returns:
        A normalized analysis data structure
    """
    # If this is None, return early
    if not analysis_data:
        return None
        
    # Initialize with default structure
    normalized = {
        'work_style': {
            'description': '',
            'explanation': ''
        },
        'environment': {
            'description': '',
            'explanation': ''
        },
        'interaction_level': {
            'description': '',
            'explanation': ''
        },
        'task_preference': {
            'description': '',
            'explanation': ''
        },
        'additional_insights': {
            'description': 'No additional insights',
            'explanation': ''
        }
    }
    
    # Handle the flattened structure from DynamoDB
    # Check for flattened field pairs (e.g., work_style_description and work_style_explanation)
    for section in ['work_style', 'environment', 'interaction_level', 'task_preference']:
        desc_key = f"{section}_description"
        exp_key = f"{section}_explanation"
        
        if desc_key in analysis_data:
            normalized[section]['description'] = analysis_data[desc_key]
        if exp_key in analysis_data:
            normalized[section]['explanation'] = analysis_data[exp_key]
    
    # Also handle the nested structure (for backward compatibility)
    for section in ['work_style', 'environment', 'interaction_level', 'task_preference']:
        if section in analysis_data:
            if isinstance(analysis_data[section], dict):
                # Handle nested dict structure (local format)
                if 'description' in analysis_data[section]:
                    normalized[section]['description'] = analysis_data[section]['description']
                if 'explanation' in analysis_data[section]:
                    normalized[section]['explanation'] = analysis_data[section]['explanation']
            elif isinstance(analysis_data[section], str):
                # Handle DynamoDB's potential string conversion
                try:
                    section_data = json.loads(analysis_data[section])
                    normalized[section]['description'] = section_data.get('description', '')
                    normalized[section]['explanation'] = section_data.get('explanation', '')
                except (json.JSONDecodeError, TypeError):
                    # If it's not valid JSON, use as is
                    normalized[section]['description'] = analysis_data[section]
    
    # Handle additional insights separately as it might be added later
    if 'additional_insights' in analysis_data:
        if isinstance(analysis_data['additional_insights'], dict):
            normalized['additional_insights']['description'] = analysis_data['additional_insights'].get('description', 'No additional insights')
            normalized['additional_insights']['explanation'] = analysis_data['additional_insights'].get('explanation', '')
        elif isinstance(analysis_data['additional_insights'], str):
            try:
                insights_data = json.loads(analysis_data['additional_insights'])
                normalized['additional_insights']['description'] = insights_data.get('description', 'No additional insights')
                normalized['additional_insights']['explanation'] = insights_data.get('explanation', '')
            except (json.JSONDecodeError, TypeError):
                normalized['additional_insights']['description'] = analysis_data['additional_insights']
    
    return normalized

# Distinguish between pre-computed and Bedrock KB analyses
def get_job_recommendations(analysis, answers=None):
    """Get job recommendations based on user preferences"""
    debug("Generating job recommendations")
    
    # Check if answers were provided
    if answers is None:
        answers = {}
    
    # Check if q5 (free response) is empty - if it is, use recommended_jobs from DynamoDB
    q5_response = answers.get('q5', '')
    if not q5_response:
        debug("Question 5 is empty, using recommended_jobs from analysis template")
        return get_recommendations_from_dynamo(answers)
    else:
        debug("Question 5 has content, using Bedrock for recommendations")
        return get_recommendations_from_bedrock(analysis)

# Get job recommendations from recommended_jobs in the analysis template
def get_recommendations_from_dynamo(answers=None):
    """Get job recommendations from recommended_jobs in the analysis template"""
    try:
        # Default answers if none provided
        if answers is None:
            answers = {}
            
        # Get the template ID based on the answers to questions 1-4
        template_id = (
            answers.get('q1', 'A') + 
            answers.get('q2', 'A') + 
            answers.get('q3', 'A') + 
            answers.get('q4', 'A')
        )
        
        debug(f"Looking up template with ID: {template_id}")
        
        # Initialize the AnalysisTemplates table
        analysis_table = dynamodb.Table('AnalysisTemplates')
        
        # Get the template with recommended_jobs
        response = analysis_table.get_item(Key={'template_id': template_id})
        if 'Item' not in response:
            debug(f"Template {template_id} not found, using fallback")
            return get_fallback_recommendations()
        
        template = response['Item']
        debug(f"Template found: {template}")
        
        # Check if recommended_jobs exists and parse it from JSON if needed
        if 'recommended_jobs' in template:
            # If recommended_jobs is a string (JSON), parse it
            recommended_jobs = template['recommended_jobs']
            if isinstance(recommended_jobs, str):
                try:
                    recommended_jobs = json.loads(recommended_jobs)
                    debug(f"Parsed recommended_jobs from JSON: {recommended_jobs}")
                except:
                    debug("Failed to parse recommended_jobs from JSON")
            matching_job_ids = recommended_jobs
        else:
            # For backward compatibility, check for matching_jobs
            matching_job_ids = template.get('matching_jobs', [])
        
        debug(f"Found job IDs: {matching_job_ids}")
        
        if not matching_job_ids:
            debug("No job IDs found, using fallback")
            return get_fallback_recommendations()
        
        # Initialize the JobBank table
        job_table = dynamodb.Table('JobBank')
        
        # Retrieve each matching job
        job_recommendations = []
        for job_id in matching_job_ids:
            try:
                # Convert to integer if it's a string
                if isinstance(job_id, str) and job_id.isdigit():
                    job_id = int(job_id)
                
                debug(f"Looking up job with ID: {job_id}")
                job_response = job_table.get_item(Key={'job_id': job_id})
                if 'Item' in job_response:
                    job_recommendations.append(job_response['Item'])
                else:
                    debug(f"Job ID {job_id} not found in JobBank")
            except Exception as e:
                debug(f"Error retrieving job ID {job_id}: {str(e)}")
        
        debug(f"Retrieved {len(job_recommendations)} jobs from JobBank")
        
        if not job_recommendations:
            debug("Failed to retrieve any matching jobs, using fallback")
            return get_fallback_recommendations()
        
        return job_recommendations
        
    except Exception as e:
        debug(f"Error retrieving recommendations from DynamoDB: {str(e)}")
        return get_fallback_recommendations()

# Get job recommendations from Bedrock knowledge base
def get_recommendations_from_bedrock(analysis):
    """Get job recommendations from Bedrock knowledge base"""
    # Import time module explicitly to avoid scope issues
    import time
    
    # Generate a trace ID for this job recommendation process
    trace_id = str(uuid.uuid4())
    job_analyzer_metrics = {
        "tool_call_accuracy": 0,
        "agent_goal_accuracy": 0,
        "execution_time": 0
    }
    
    # Metrics for Bedrock Knowledge Base
    bedrock_metrics = {
        "response_relevancy": 0.0,
        "query_constructed": False,
        "retrieval_count": 0
    }
    
    try:
        # Extract key points from the analysis to form a query
        query = "Find job postings suitable for someone who:"
        
        # Check if analysis is HTML (legacy format) or JSON
        is_html_format = isinstance(analysis, str) and analysis.strip().startswith("<div")
        
        if is_html_format:
            # Legacy HTML format - extract details using regex
            debug("Analysis is in HTML format, extracting with regex")
            
            # Check for "not relevant" in the additional insights
            not_relevant_check = re.search(r'Additional information not relevant|not useful for job recommendations', analysis, re.IGNORECASE)
            
            if not_relevant_check:
                debug("Found 'not relevant' in additional insights, using basic query plus MC answers")
                
                # Extract work style, environment, etc. from multiple choice answers
                descriptions = re.findall(r'<strong>(.*?)</strong>', analysis)
                relevant_descriptions = [d for d in descriptions if "not relevant" not in d.lower() and "not available" not in d.lower()]
                
                if relevant_descriptions:
                    # Include only the descriptions from multiple choice questions (first 4)
                    query += " " + " ".join(relevant_descriptions[:4]) if len(relevant_descriptions) > 4 else " ".join(relevant_descriptions)
                else:
                    query = "Find tech jobs suitable for neurodiverse candidates with various work preferences"
            else:
                # Simple parsing to extract description text from the HTML
                descriptions = re.findall(r'<strong>(.*?)</strong>', analysis)
                if descriptions:
                    query += " " + " ".join(descriptions)
                else:
                    query = "Find tech jobs suitable for neurodiverse candidates with various work preferences"
        else:
            # JSON format - extract details from structured data
            debug("Analysis is in JSON format, extracting from structured data")
            
            # Extract descriptions from each section
            descriptions = []
            
            for section in ['work_style', 'environment', 'interaction_level', 'task_preference']:
                if section in analysis:
                    if isinstance(analysis[section], dict) and 'description' in analysis[section]:
                        descriptions.append(analysis[section]['description'])
                    elif isinstance(analysis[section], str):
                        descriptions.append(analysis[section])
            
            # Add additional insights if relevant
            if 'additional_insights' in analysis:
                additional_info = analysis['additional_insights']
                if isinstance(additional_info, dict) and 'description' in additional_info:
                    insight_text = additional_info['description']
                    # Only add if it's not a 'no insights' message
                    if insight_text and 'no additional insights' not in insight_text.lower():
                        descriptions.append(insight_text)
                elif isinstance(additional_info, str) and additional_info:
                    descriptions.append(additional_info)
            
            # Build the query
            if descriptions:
                query += " " + " ".join(descriptions)
            else:
                query = "Find tech jobs suitable for neurodiverse candidates with various work preferences"
        
        debug(f"Query for Bedrock: {query}")
        bedrock_metrics["query_constructed"] = True
        
        # Query the Bedrock knowledge base with retry logic for auto-pause situations
        retrieval_results = []
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                debug(f"Querying Bedrock knowledge base (attempt {attempt+1}/{max_retries})")
                response = bedrock.retrieve(
                    knowledgeBaseId=knowledge_base_id,
                    retrievalQuery={"text": query},
                    retrievalConfiguration={
                        "vectorSearchConfiguration": {
                            "numberOfResults": 10  # Get top 10 results
                        }
                    }
                )
                
                retrieval_results = response.get('retrievalResults', [])
                bedrock_metrics["retrieval_count"] = len(retrieval_results)
                debug(f"Retrieved {len(retrieval_results)} results from Bedrock")
                
                # Calculate response relevancy based on results
                if retrieval_results:
                    # If we have results, check for relevance scores if available
                    scores = []
                    for result in retrieval_results:
                        if 'score' in result:
                            scores.append(float(result['score']))
                        elif 'metadata' in result and 'score' in result['metadata']:
                            scores.append(float(result['metadata']['score']))
                    
                    # If we have scores, calculate an average relevancy
                    if scores:
                        avg_score = sum(scores) / len(scores)
                        # Raw score without normalization
                        bedrock_metrics["response_relevancy"] = avg_score
                        
                        # Convert to percentage for display (0-100 scale)
                        bedrock_relevancy_percentage = int(avg_score * 100)
                        debug(f"Average Bedrock relevancy: {bedrock_relevancy_percentage}%")
                    else:
                        # If we don't have explicit scores but have results, give a moderate score
                        bedrock_metrics["response_relevancy"] = 0.5
                        bedrock_relevancy_percentage = 50
                        debug("No explicit relevance scores, using default 50%")
                else:
                    bedrock_metrics["response_relevancy"] = 0
                    bedrock_relevancy_percentage = 0
                
                break  # Successful, exit the retry loop
                
            except Exception as e:
                error_msg = str(e)
                debug(f"Bedrock query error (attempt {attempt+1}): {error_msg}")
                
                # Check if this is the auto-pause resumption error
                if "resuming after being auto-paused" in error_msg and attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)  # Exponential backoff
                    debug(f"Vector database is resuming after auto-pause. Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue  # Try again
                elif attempt < max_retries - 1:
                    # Other error but still have retries left
                    time.sleep(retry_delay)
                    continue
                else:
                    # Last attempt failed, log and continue with empty results
                    app_logger.error(f"Error querying Bedrock after {max_retries} attempts: {error_msg}")
        
        # Send Response Relevancy metric to Langtrace for Bedrock
        send_langtrace_metric(
            "Bedrock Knowledge Base",
            "response_relevancy",
            bedrock_metrics["response_relevancy"],
            trace_id=str(uuid.uuid4()),
            metadata={
                "query": query[:100],  # Truncate long queries
                "retrieval_count": bedrock_metrics["retrieval_count"],
                "query_constructed": str(bedrock_metrics["query_constructed"]),
                "score_calculation": "Raw vector similarity score without normalization"
            }
        )
        
        if not retrieval_results:
            debug("No results retrieved from Bedrock, using fallback recommendations")
            return get_fallback_recommendations()
            
        # Extract user profile from the analysis HTML for personalized job matching
        user_profile = extract_user_profile_from_analysis(analysis)
        debug(f"Extracted user profile for job matching: {user_profile}")
        
        # Initialize the JobAnalyzer with the user's profile
        job_analyzer = JobAnalyzer(
            s3_client=s3,
            debug_func=debug,
            user_profile=user_profile
        )
        
        # Start time for metrics
        start_time = time.time()
        
        # Process all retrieved job results with CrewAI agents
        debug("Processing job results with CrewAI agents")
        try:
            # Use the consistent bedrock_relevancy_percentage for all job recommendations
            job_recommendations = job_analyzer.process_job_results(retrieval_results, bedrock_relevancy_percentage)
            
            # Tool Call Accuracy - successful if we got recommendations
            if job_recommendations and len(job_recommendations) > 0:
                job_analyzer_metrics["tool_call_accuracy"] = 1
                
                # Agent Goal Accuracy - successful if we have reasoning for at least one job
                if any("reasoning" in job for job in job_recommendations):
                    job_analyzer_metrics["agent_goal_accuracy"] = 1
                    
                # Also send average match score as a separate metric
                try:
                    # We expect bedrock_score to be consistent across all recommendations
                    # since we're using the same bedrock_relevancy_percentage
                    avg_bedrock_score = bedrock_relevancy_percentage
                    avg_agent_score = sum(job.get("agent_score", 0) for job in job_recommendations) / len(job_recommendations)
                    avg_final_score = sum(job.get("match_score", 0) for job in job_recommendations) / len(job_recommendations)
                    
                    send_langtrace_metric(
                        "Bedrock Knowledge Base",
                        "average_match_score",
                        str(avg_final_score),
                        trace_id=str(uuid.uuid4()),
                        metadata={
                            "avg_bedrock_score": str(avg_bedrock_score),
                            "avg_agent_score": str(avg_agent_score),
                            "recommendation_count": len(job_recommendations),
                            "score_formula": "Simple average of (Bedrock similarity + Agent analysis)",
                            "using_consistent_bedrock_score": "true"
                        }
                    )
                except Exception as e:
                    app_logger.error(f"Error calculating average scores: {str(e)}")
                    debug(f"Error in average score calculation: {str(e)}")
            
            job_analyzer_metrics["execution_time"] = time.time() - start_time
                
        except Exception as e:
            app_logger.error(f"Error in JobAnalyzer: {str(e)}")
            job_analyzer_metrics["tool_call_accuracy"] = 0
            job_analyzer_metrics["agent_goal_accuracy"] = 0
            job_analyzer_metrics["execution_time"] = time.time() - start_time
            job_recommendations = []
        
        if not job_recommendations:
            debug("No valid job recommendations generated, using fallback")
            job_recommendations = get_fallback_recommendations()
            
        # Send metrics to Langtrace
        debug("Sending JobAnalyzer metrics to Langtrace")
        # 1. Tool Call Accuracy
        send_langtrace_metric(
            "Agent job_analyzer",
            "tool_call_accuracy",
            job_analyzer_metrics["tool_call_accuracy"],
            trace_id=trace_id,
            metadata={
                "agent_name": "job_analyzer",
                "num_results": len(retrieval_results),
                "num_recommendations": len(job_recommendations),
                "execution_time": str(job_analyzer_metrics["execution_time"])
            }
        )
        
        # 2. Agent Goal Accuracy
        send_langtrace_metric(
            "Agent job_analyzer",
            "agent_goal_accuracy",
            job_analyzer_metrics["agent_goal_accuracy"],
            trace_id=trace_id,
            metadata={
                "agent_name": "job_analyzer",
                "num_results": len(retrieval_results),
                "num_recommendations": len(job_recommendations)
            }
        )
            
        debug(f"Successfully processed {len(job_recommendations)} job recommendations")
        return job_recommendations
        
    except Exception as e:
        app_logger.error(f"Error in get_recommendations_from_bedrock: {str(e)}")
        debug(f"Bedrock recommendation error: {str(e)}")
        
        # Send failure metrics to Langtrace
        send_langtrace_metric(
            "Agent job_analyzer",
            "tool_call_accuracy",
            0,
            trace_id=trace_id,
            metadata={
                "agent_name": "job_analyzer",
                "error": str(e)[:100]  # Truncate long error messages
            }
        )
        
        send_langtrace_metric(
            "Agent job_analyzer",
            "agent_goal_accuracy",
            0,
            trace_id=trace_id,
            metadata={
                "agent_name": "job_analyzer",
                "error": str(e)[:100]  # Truncate long error messages
            }
        )
        
        return get_fallback_recommendations()

def extract_user_profile_from_analysis(analysis):
    """Extract user profile information from the analysis HTML or JSON"""
    try:
        # Initialize default profile with only the 5 core analysis portions
        profile = {
            "work_style": "Not specified",
            "environment": "Not specified",
            "interaction_level": "Not specified",
            "task_preference": "Not specified",
            "additional_insights": ""
        }
        
        # Check if analysis is already a structured JSON object
        if isinstance(analysis, dict):
            debug("Analysis is already in JSON format")
            
            # Direct mapping for structured data
            for key in ['work_style', 'environment', 'interaction_level', 'task_preference']:
                if key in analysis:
                    if isinstance(analysis[key], dict):
                        # Format: { description: "...", explanation: "..." }
                        profile[key] = analysis[key].get('description', 'Not specified')
                        if 'explanation' in analysis[key]:
                            profile[f"{key}_details"] = analysis[key]['explanation']
                    else:
                        # Format: "description string"
                        profile[key] = analysis[key]
            
            # Handle additional insights
            if 'additional_insights' in analysis:
                if isinstance(analysis['additional_insights'], dict):
                    profile['additional_insights'] = analysis['additional_insights'].get('description', '')
                else:
                    profile['additional_insights'] = analysis['additional_insights']
            
            return profile
            
        # If it's HTML, extract information using regex
        elif isinstance(analysis, str) and analysis.strip().startswith("<div"):
            debug("Extracting profile from HTML analysis")
            
            # Extract descriptions from analysis HTML using regex
            descriptions = re.findall(r'<strong>(.*?)</strong>', analysis)
            explanations = re.findall(r'<p class="text-muted mb-4">(.*?)</p>', analysis)
            
            # Map extracted information to profile sections
            section_keys = ["work_style", "environment", "interaction_level", "task_preference", "additional_insights"]
            
            for i, (key, desc) in enumerate(zip(section_keys, descriptions[:len(section_keys)])):
                profile[key] = desc
                
                # Add explanation if available
                if i < len(explanations):
                    profile[f"{key}_details"] = explanations[i]
            
            return profile
        
        # If it's neither a dict nor HTML, return the basic profile
        return profile
        
    except Exception as e:
        debug(f"Error extracting user profile from analysis: {str(e)}")
        # Return a basic profile if extraction fails
        return {
            "work_style": "Flexible",
            "environment": "Adaptable",
            "interaction_level": "Moderate",
            "task_preference": "Varied",
            "additional_insights": ""
        }

# Return fallback job recommendations when other methods fail
def get_fallback_recommendations():
    """Return fallback job recommendations when other methods fail"""
    debug("Using fallback job recommendations")
    return [
        {
            "title": "Data Quality Analyst",
            "company": "Oracle",
            "location": "Austin, TX (Remote Available)",
            "match_score": 95,
            "reasoning": "Fallback job match for neurodiverse candidates. This role offers a structured environment with clear objectives and minimal interruptions.",
            "url": "https://careers.oracle.com/jobs"
        },
        {
            "title": "Software Developer - Backend",
            "company": "Oracle Cloud Infrastructure", 
            "location": "Seattle, WA (Hybrid)",
            "match_score": 92,
            "reasoning": "Fallback job match for neurodiverse candidates. This role features flexible scheduling with dedicated quiet time for deep work.",
            "url": "https://careers.oracle.com/jobs"
        },
        {
            "title": "Quality Assurance Engineer",
            "company": "Oracle",
            "location": "Reston, VA",
            "match_score": 88,
            "reasoning": "Fallback job match for neurodiverse candidates. This role provides structured work environment with clear processes.",
            "url": "https://careers.oracle.com/jobs"
        }
    ]
