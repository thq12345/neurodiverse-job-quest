import os
from dotenv import load_dotenv
load_dotenv() 

langtrace_api_key = os.environ.get("LANGTRACE_API_KEY")
from langtrace_python_sdk import langtrace
langtrace.init(api_key=langtrace_api_key)

# Import pre-computed analyses
from analysis_templates import get_analysis_for_combination
from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from openai import OpenAI
import logging
import json
import sys
import boto3
import re
import io
import PyPDF2
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
dynamodb = aws_session.resource('dynamodb')

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

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY") or "neurodiversity_app_secret"
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///app.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

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

@app.route("/")
def welcome():
    session.clear()
    return render_template("welcome.html")

@app.route("/questionnaire", methods=["GET"])
def questionnaire():
    debug("Rendering questionnaire page")
    return render_template("question.html", questions=questions)

@app.route("/submit_questionnaire", methods=["POST"])
def submit_questionnaire():
    debug("Questionnaire submitted")
    debug("Form data", request.form)
    
    # Verify required questions are answered (now excluding q5 which is optional)
    required_questions = [f"q{i+1}" for i in range(len(questions)) 
                          if not (i+1 == 5 and 'optional' in questions[i] and questions[i]['optional'])]
    
    if not all(q in request.form for q in required_questions):
        debug("Missing required answers")
        return redirect(url_for("questionnaire"))
    
    # Store answers in session
    for i in range(len(questions)):
        question_key = f"q{i+1}"
        
        # Handle case when optional question is not answered
        if i+1 == 5 and 'optional' in questions[i] and questions[i]['optional'] and question_key not in request.form:
            session[question_key] = ""
            continue
            
        session[question_key] = request.form.get(question_key, "")
        
        # Log the answer
        question_text = questions[i]["text"]
        answer = session[question_key]
        
        # Format log message based on question type
        if 'type' in questions[i] and questions[i]['type'] == 'free_response':
            app_logger.info(f"Q{i+1}: {question_text} - Answer: {answer}")
        else:
            option_text = next((opt[1] for opt in questions[i]["options"] if opt[0] == answer), "Unknown")
            app_logger.info(f"Q{i+1}: {question_text} - Option: {answer} - {option_text}")
    
    return redirect(url_for("results"))

@app.route("/results")
def results():
    debug("Results route called")
    
    # Verify all questions were answered
    if not all(f"q{i+1}" in session for i in range(len(questions))):
        debug("Missing required answers, redirecting to questionnaire")
        return redirect(url_for("questionnaire"))

    debug("Session data verification started")
    
    # Log all session data for verification
    app_logger.info("\n*** SESSION DATA VERIFICATION ***")
    
    for i in range(len(questions)):
        question_key = f"q{i+1}"
        if question_key in session:
            question_text = questions[i]["text"]
            answer = session[question_key]
            
            # Format log message based on question type
            if 'type' in questions[i] and questions[i]['type'] == 'free_response':
                app_logger.info(f"Q{i+1}: {question_text} - Answer: {answer}")
            else:
                option_text = next((opt[1] for opt in questions[i]["options"] if opt[0] == answer), "Unknown")
                app_logger.info(f"Q{i+1}: {question_text} - Option: {answer} - {option_text}")
                
    app_logger.info("*** END SESSION DATA ***")

    # Prepare answers for AI analysis
    answers = []
    for i, q in enumerate(questions):
        answer_key = session[f"q{i+1}"]
        if 'type' in q and q['type'] == 'free_response':
            answer_text = answer_key  # Use the free response text directly
        else:
            answer_text = next(opt[1] for opt in q["options"] if opt[0] == answer_key)
        answers.append(f"Q: {q['text']}\nA: {answer_text}")

    analysis = analyze_responses(answers)
    recommendations = get_job_recommendations(analysis)
    
    # Store in database
    try:
        debug("Starting database storage process")
        from models import Assessment
        
        # Create new assessment record
        assessment = Assessment(
            q1_answer=session.get('q1', ''),
            q2_answer=session.get('q2', ''),
            q3_answer=session.get('q3', ''),
            q4_answer=session.get('q4', ''),
            q5_answer=session.get('q5', ''),
            analysis=str(analysis)
        )
        
        # Add to database and commit
        db.session.add(assessment)
        db.session.commit()
        
        debug(f"Database record created with ID: {assessment.id}")
        
        # Log the successful database operation
        app_logger.info(f"Assessment saved to database (ID: {assessment.id})")
        app_logger.info(f"Free response answer: {assessment.q5_answer}")
    except Exception as e:
        # Log database errors
        app_logger.error(f"Database error: {str(e)}")
        debug(f"Database operation failed: {str(e)}")

    return render_template(
        "results.html",
        analysis=analysis,
        recommendations=recommendations
    )

def analyze_responses(answers):
    debug("Starting response analysis")
    
    # Import time module explicitly to avoid scope issues
    import time
    
    # Generate a trace ID for this analysis session
    trace_id = str(uuid.uuid4())
    
    # Extract the first 4 multiple-choice answers from the session (if available)
    mc_answers = []
    for i in range(4):  # First 4 questions are multiple choice
        answer_key = f"q{i+1}"
        if answer_key in session:
            mc_answers.append(session[answer_key])
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
        free_response = session.get("q5", "")
        
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
            
            return format_analysis(normalized_analysis)
        
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
        
        return format_analysis(normalized_analysis)

# Format the analysis data into HTML
def format_analysis(analysis):
    """Format the analysis data into HTML"""
    try:
        # Make sure analysis is a valid dictionary
        if not isinstance(analysis, dict):
            app_logger.error(f"Invalid analysis format: {type(analysis)}")
            analysis = {
                'work_style': {'description': 'Not available', 'explanation': 'Analysis data was not properly structured.'},
                'environment': {'description': 'Not available', 'explanation': 'Analysis data was not properly structured.'},
                'interaction_level': {'description': 'Not available', 'explanation': 'Analysis data was not properly structured.'},
                'task_preference': {'description': 'Not available', 'explanation': 'Analysis data was not properly structured.'},
                'additional_insights': {'description': 'No additional insights', 'explanation': 'Analysis data was not properly structured.'}
            }
        
        # Ensure all required sections exist
        for section in ['work_style', 'environment', 'interaction_level', 'task_preference']:
            if section not in analysis or not isinstance(analysis[section], dict):
                analysis[section] = {'description': 'Not available', 'explanation': 'This section was missing from the analysis.'}
        
        # Ensure additional_insights exists
        if 'additional_insights' not in analysis or not isinstance(analysis['additional_insights'], dict):
            analysis['additional_insights'] = {'description': 'No additional insights', 'explanation': ''}
            
        # Format the HTML output
        html_output = f"""
        <div class='analysis-section'>
            <h3>Work Style</h3>
            <p class="mb-2"><strong>{analysis['work_style'].get('description', 'Not available')}</strong></p>
            <p class="text-muted mb-4">{analysis['work_style'].get('explanation', '')}</p>

            <h3>Ideal Environment</h3>
            <p class="mb-2"><strong>{analysis['environment'].get('description', 'Not available')}</strong></p>
            <p class="text-muted mb-4">{analysis['environment'].get('explanation', '')}</p>

            <h3>Interaction Level</h3>
            <p class="mb-2"><strong>{analysis['interaction_level'].get('description', 'Not available')}</strong></p>
            <p class="text-muted mb-4">{analysis['interaction_level'].get('explanation', '')}</p>

            <h3>Task Preferences</h3>
            <p class="mb-2"><strong>{analysis['task_preference'].get('description', 'Not available')}</strong></p>
            <p class="text-muted mb-4">{analysis['task_preference'].get('explanation', '')}</p>
            
            <h3>Additional Insights</h3>
            <p class="mb-2"><strong>{analysis.get('additional_insights', {}).get('description', 'No additional insights')}</strong></p>
            <p class="text-muted mb-4">{analysis.get('additional_insights', {}).get('explanation', '')}</p>
        </div>
        """
        debug(f"Successfully formatted analysis into HTML: {html_output[:50]}...")
        return html_output
        
    except Exception as e:
        app_logger.error(f"Error formatting analysis data: {str(e)}")
        debug(f"Failed to format analysis: {str(e)}")
        
        # Return a minimal valid HTML in case of error
        return """
<div class='analysis-section'>
    <h3>Analysis Error</h3>
    <p class="mb-2"><strong>We encountered an error processing your responses</strong></p>
    <p class="text-muted mb-4">Please try again or contact support if the issue persists.</p>
</div>
"""

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
def get_job_recommendations(analysis):
    """Get job recommendations based on user preferences"""
    debug("Generating job recommendations")
    
    # Check if q5 (free response) is empty - if it is, use recommended_jobs from DynamoDB
    q5_response = session.get('q5', '')
    if not q5_response:
        debug("Question 5 is empty, using recommended_jobs from analysis template")
        return get_recommendations_from_dynamo()
    else:
        debug("Question 5 has content, using Bedrock for recommendations")
        return get_recommendations_from_bedrock(analysis)

# Get job recommendations from recommended_jobs in the analysis template
def get_recommendations_from_dynamo():
    """Get job recommendations from recommended_jobs in the analysis template"""
    try:
        # Get the template ID based on the user's answers to questions 1-4
        template_id = (
            session.get('q1', 'A') + 
            session.get('q2', 'A') + 
            session.get('q3', 'A') + 
            session.get('q4', 'A')
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
        
        # More robust check for valid HTML format
        is_valid_html = False
        if isinstance(analysis, str):
            is_valid_html = analysis.strip().startswith("<div")
        
        if not is_valid_html:
            debug("Analysis is not valid HTML, using generic query")
            query = "Find entry-level tech jobs suitable for neurodiverse candidates"
        else:
            # Extract key points from the analysis HTML
            debug("Extracting key points from analysis for query")
            
            # Check for "not relevant" or similar in the additional insights
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
    """Extract user profile information from the analysis HTML"""
    try:
        # Initialize default profile
        profile = {
            "work_style": "Not specified",
            "environment": "Not specified",
            "interaction_level": "Not specified",
            "task_preference": "Not specified",
            "additional_info": ""
        }
        
        # Extract descriptions from analysis HTML using regex
        descriptions = re.findall(r'<strong>(.*?)</strong>', analysis)
        explanations = re.findall(r'<p class="text-muted mb-4">(.*?)</p>', analysis)
        
        # Map extracted information to profile sections
        section_keys = ["work_style", "environment", "interaction_level", "task_preference", "additional_info"]
        
        for i, (key, desc) in enumerate(zip(section_keys, descriptions[:len(section_keys)])):
            profile[key] = desc
            
            # Add explanation if available
            if i < len(explanations):
                profile[f"{key}_details"] = explanations[i]
        
        return profile
        
    except Exception as e:
        debug(f"Error extracting user profile from analysis: {str(e)}")
        # Return a basic profile if extraction fails
        return {
            "work_style": "Flexible",
            "environment": "Adaptable",
            "interaction_level": "Moderate",
            "task_preference": "Varied",
            "additional_info": ""
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

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)