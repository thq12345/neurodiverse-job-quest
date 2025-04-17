import os
from dotenv import load_dotenv
load_dotenv() 

langtrace_api_key = os.environ.get("LANGTRACE_API_KEY")
from langtrace_python_sdk import langtrace
langtrace.init(api_key = langtrace_api_key)
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
        "text": "Is there anything else we should know about you?",
        "type": "free_response"
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
    
    # Verify all questions are answered
    if not all(f"q{i+1}" in request.form for i in range(len(questions))):
        debug("Missing required answers")
        return redirect(url_for("questionnaire"))
    
    # Store answers in session
    for i in range(len(questions)):
        question_key = f"q{i+1}"
        session[question_key] = request.form.get(question_key)
        
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
    
    # Extract the first 4 multiple-choice answers from the session (if available)
    mc_answers = []
    for i in range(4):  # First 4 questions are multiple choice
        answer_key = f"q{i+1}"
        if answer_key in session:
            mc_answers.append(session[answer_key])
        else:
            mc_answers.append(None)
    
    # Check if we have all 4 multiple-choice answers
    if all(mc_answers) and len(mc_answers) == 4:
        debug("Using pre-computed analysis for multiple choice answers")
        q1, q2, q3, q4 = mc_answers
        pre_computed_analysis = get_analysis_for_combination(q1, q2, q3, q4)
        
        if pre_computed_analysis:
            debug(f"Found pre-computed analysis for combination {q1}{q2}{q3}{q4}")
            
            # Normalize data structure
            pre_computed_analysis = normalize_analysis_data(pre_computed_analysis)
            
            # Get the free response answer (if provided)
            free_response = session.get("q5", "")
            
            # If free response is provided, customize the additional insights
            if free_response and free_response.strip():
                debug("Customizing additional insights based on free response")
                
                # If we have an API key, we can use OpenAI to customize the additional insights
                if openai_api_key:
                    try:
                        prompt = f"""
                        Based on the user's additional information: "{free_response}"
                        
                        Please provide a brief, personalized insight about their work preferences.
                        Format as a JSON object with these fields:
                        - description: A concise title/summary (max 10 words)
                        - explanation: How their additional information informs their work preferences (1-2 sentences)
                        
                        Response format:
                        {{
                            "description": "brief description",
                            "explanation": "brief explanation"
                        }}
                        """
                        
                        response = client.chat.completions.create(
                            model="gpt-4o",
                            messages=[{"role": "user", "content": prompt}],
                            response_format={
                                "type": "json_schema",
                                "json_schema": {
                                    "name": "additional_insights",
                                    "strict": True,
                                    "schema": {
                                        "type": "object",
                                        "properties": {
                                            "description": {
                                                "type": "string",
                                                "description": "A concise title/summary (max 10 words)"
                                            },
                                            "explanation": {
                                                "type": "string",
                                                "description": "How additional information informs work preferences (1-2 sentences)"
                                            }
                                        },
                                        "required": ["description", "explanation"],
                                        "additionalProperties": False
                                    }
                                }
                            }
                        )
                        
                        custom_insights = json.loads(response.choices[0].message.content)
                        pre_computed_analysis["additional_insights"] = custom_insights
                    except Exception as e:
                        # If there's an error, just use a generic additional insight
                        app_logger.error(f"Error customizing additional insights: {str(e)}")
                        pre_computed_analysis["additional_insights"] = {
                            "description": "Additional information provided, but we couldn't customize the additional insights",
                            "explanation": "You shared specific preferences that provide further context for your work environment needs."
                        }
                else:
                    # Simple custom insight without API
                    pre_computed_analysis["additional_insights"] = {
                        "description": "Additional information provided, but we couldn't customize the additional insights",
                        "explanation": "OPENAI API KEY NOT FOUND, UNABLE TO CUSTOMIZE ADDITIONAL INSIGHTS"
                    }
            else:
                # If no free response, add default additional insights
                pre_computed_analysis["additional_insights"] = {
                    "description": "No additional information provided, and we couldn't customize the additional insights",
                    "explanation": "You did not provide any additional context about your work preferences."
                }
            
            return format_analysis(pre_computed_analysis)
    
    # If we don't have pre-computed analysis (missing answers or combination not found),
    # fall back to the original method
    debug("No pre-computed analysis available, using standard analysis method")
    
    # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
    prompt = "\n".join([
        "Based on these assessment responses, provide a detailed analysis of the ideal",
        "work environment for this candidate. For each aspect, explain how it specifically",
        "relates to their assessment answers. Format the response in JSON with these fields:",
        "- work_style: {",
        "    description: brief description of preferred work style,",
        "    explanation: how this connects to their assessment answers",
        "  }",
        "- environment: {",
        "    description: ideal work environment,",
        "    explanation: how this matches their preferences",
        "  }",
        "- interaction_level: {",
        "    description: preferred level of social interaction,",
        "    explanation: why this level suits them based on their responses",
        "  }",
        "- task_preference: {",
        "    description: type of tasks they excel at,",
        "    explanation: how this aligns with their answers",
        "  }",
        "- additional_insights: {",
        "    description: insights from additional information provided,",
        "    explanation: how this further informs their work preferences",
        "  }",
        "",
        "Here are the responses:",
        *answers
    ])

    try:
        # If API key is not available, we'll still use our pre-computed analyses
        # The code that calls analyze_responses should already have checked for pre-computed analyses
        # This section only runs if we couldn't find a matching pre-computed analysis
        
        if not openai_api_key:
            debug("No API key available and no matching pre-computed analysis found")
            # Return a message asking the user to provide an API key
            return "To generate a personalized analysis, please provide an OpenAI API key or ensure your answers match our pre-computed templates."
        
        debug("Calling OpenAI API for analysis")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": "work_analysis",
                    "strict": True,
                    "schema": {
                        "type": "object",
                        "properties": {
                            "work_style": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string"},
                                    "explanation": {"type": "string"}
                                },
                                "required": ["description", "explanation"],
                                "additionalProperties": False
                            },
                            "environment": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string"},
                                    "explanation": {"type": "string"}
                                },
                                "required": ["description", "explanation"],
                                "additionalProperties": False
                            },
                            "interaction_level": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string"},
                                    "explanation": {"type": "string"}
                                },
                                "required": ["description", "explanation"],
                                "additionalProperties": False
                            },
                            "task_preference": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string"},
                                    "explanation": {"type": "string"}
                                },
                                "required": ["description", "explanation"],
                                "additionalProperties": False
                            },
                            "additional_insights": {
                                "type": "object",
                                "properties": {
                                    "description": {"type": "string"},
                                    "explanation": {"type": "string"}
                                },
                                "required": ["description", "explanation"],
                                "additionalProperties": False
                            }
                        },
                        "required": ["work_style", "environment", "interaction_level", "task_preference", "additional_insights"],
                        "additionalProperties": False
                    }
                }
            }
        )

        analysis = json.loads(response.choices[0].message.content)
        debug("Analysis generated successfully")
        
        # Normalize data from OpenAI to ensure consistent structure
        normalized_analysis = normalize_analysis_data(analysis)
        return format_analysis(normalized_analysis)
    except Exception as e:
        app_logger.error(f"Error analyzing responses: {str(e)}")
        debug(f"Analysis error: {str(e)}")
        return "We encountered an error analyzing your responses. Please try again."

def format_analysis(analysis):
    """Format the analysis data into HTML"""
    return f"""
<div class='analysis-section'>
    <h3>Work Style</h3>
    <p class="mb-2"><strong>{analysis['work_style']['description']}</strong></p>
    <p class="text-muted mb-4">{analysis['work_style']['explanation']}</p>

    <h3>Ideal Environment</h3>
    <p class="mb-2"><strong>{analysis['environment']['description']}</strong></p>
    <p class="text-muted mb-4">{analysis['environment']['explanation']}</p>

    <h3>Interaction Level</h3>
    <p class="mb-2"><strong>{analysis['interaction_level']['description']}</strong></p>
    <p class="text-muted mb-4">{analysis['interaction_level']['explanation']}</p>

    <h3>Task Preferences</h3>
    <p class="mb-2"><strong>{analysis['task_preference']['description']}</strong></p>
    <p class="text-muted mb-4">{analysis['task_preference']['explanation']}</p>
    
    <h3>Additional Insights</h3>
    <p class="mb-2"><strong>{analysis.get('additional_insights', {}).get('description', 'No additional insights')}</strong></p>
    <p class="text-muted mb-4">{analysis.get('additional_insights', {}).get('explanation', '')}</p>
</div>
"""

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
    
    # Copy data from the source to our normalized structure
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

def get_job_recommendations(analysis):
    """Get job recommendations based on user preferences"""
    debug("Generating job recommendations from AWS Bedrock")
    
    try:
        # Extract key points from the analysis to form a query
        query = "Find job postings suitable for someone who:"
        
        # Check if analysis is a string (error message) or formatted HTML
        if isinstance(analysis, str) and not analysis.startswith("<div"):
            debug("Analysis is error message or incomplete, using generic query")
            query = "Find entry-level tech jobs suitable for neurodiverse candidates"
        else:
            # Extract key points from the analysis HTML
            debug("Extracting key points from analysis for query")
            
            # Simple parsing to extract description text from the HTML
            descriptions = re.findall(r'<strong>(.*?)</strong>', analysis)
            if descriptions:
                query += " " + " ".join(descriptions)
            else:
                query = "Find tech jobs suitable for neurodiverse candidates with various work preferences"
        
        debug(f"Query for Bedrock: {query}")
        
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
                debug(f"Retrieved {len(retrieval_results)} results from Bedrock")
                break  # Successful, exit the retry loop
                
            except Exception as e:
                error_msg = str(e)
                debug(f"Bedrock query error (attempt {attempt+1}): {error_msg}")
                
                # Check if this is the auto-pause resumption error
                if "resuming after being auto-paused" in error_msg and attempt < max_retries - 1:
                    import time
                    wait_time = retry_delay * (attempt + 1)  # Exponential backoff
                    debug(f"Vector database is resuming after auto-pause. Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue  # Try again
                elif attempt < max_retries - 1:
                    # Other error but still have retries left
                    import time
                    time.sleep(retry_delay)
                    continue
                else:
                    # Last attempt failed, log and continue with empty results
                    app_logger.error(f"Error querying Bedrock after {max_retries} attempts: {error_msg}")
        
        job_recommendations = []
        
        # Process each result
        for i, result in enumerate(retrieval_results):
            try:
                # Extract S3 location information
                s3_uri = result["location"]["s3Location"]["uri"]
                score = int(float(result["score"]) * 100)  # Convert score to percentage
                
                debug(f"Processing result {i+1} with score {score}, URI: {s3_uri}")
                
                # Parse the S3 URI to get bucket and key
                bucket, key = s3_uri.replace("s3://", "").split("/", 1)
                
                # Get the document from S3 with retry logic
                max_s3_retries = 2
                s3_retry_delay = 2  # seconds
                content = None  # Initialize content variable
                
                for s3_attempt in range(max_s3_retries):
                    try:
                        debug(f"Retrieving S3 object {bucket}/{key} (attempt {s3_attempt+1}/{max_s3_retries})")
                        obj = s3.get_object(Bucket=bucket, Key=key)
                        content_bytes = obj["Body"].read()
                        
                        # Check if it's a PDF (starts with %PDF)
                        if content_bytes.startswith(b'%PDF'):
                            debug(f"Processing PDF document from {key}")
                            # Parse PDF using PyPDF2
                            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content_bytes))
                            content = ""
                            for page in range(len(pdf_reader.pages)):
                                content += pdf_reader.pages[page].extract_text() + "\n"
                        else:
                            # Assume it's plain text
                            content = content_bytes.decode("utf-8", errors="ignore")
                        
                        debug(f"Content extracted, length: {len(content)} characters")
                        break  # Success, exit retry loop
                        
                    except Exception as e:
                        error_msg = str(e)
                        debug(f"S3 retrieval error (attempt {s3_attempt+1}): {error_msg}")
                        
                        if s3_attempt < max_s3_retries - 1:
                            # Still have retries left
                            import time
                            time.sleep(s3_retry_delay)
                            continue
                        else:
                            # Last attempt failed, re-raise the exception to be caught by the outer try/except
                            raise
                
                # If content retrieval failed, skip this job
                if content is None:
                    debug(f"Failed to retrieve content for {s3_uri}, skipping")
                    continue
                
                # Extract job title from filename if possible (often contains good info)
                filename_title = key.split('/')[-1]
                if "-" in filename_title:
                    # Format is often "ID-Job Title.pdf"
                    parts = filename_title.split('-', 1)
                    if len(parts) > 1:
                        filename_title = parts[1].replace('.pdf', '').strip()
                
                # Default values
                job_title = filename_title if filename_title else "Unknown Position"
                company = "Unknown Company"
                location = "Location Not Specified"
                job_description = ""
                
                # Try to extract job title
                title_match = None
                for pattern in [
                    r"Job\s+Requisition\s+Title:\s*(.*?)(?:\n|$)",
                    r"Position\s+Title:\s*(.*?)(?:\n|$)",
                    r"Title:\s*(.*?)(?:\n|$)",
                ]:
                    title_match = re.search(pattern, content, re.IGNORECASE)
                    if title_match and title_match.group(1).strip():
                        job_title = title_match.group(1).strip()
                        break
                
                # Try to extract company
                company_match = None
                for pattern in [
                    r"at\s+([\w\s]+(?:University|College|Corporation|Inc\.|LLC|Company))",
                    r"Company:\s*(.*?)(?:\n|$)",
                    r"Employer:\s*(.*?)(?:\n|$)",
                    r"organization:\s*(.*?)(?:\n|$)"
                ]:
                    company_match = re.search(pattern, content, re.IGNORECASE)
                    if company_match and company_match.group(1).strip():
                        company = company_match.group(1).strip()
                        break
                
                # Try to extract location
                location_match = None
                for pattern in [
                    r"Location:\s*(.*?)(?:\n|$)",
                    r"Place:\s*(.*?)(?:\n|$)",
                    r"(?:Full Time or Part Time).*?(?:\n|$).*?(?:Date Posted).*?(?:\n|$).*?(?:Location|Place):\s*(.*?)(?:\n|$)"
                ]:
                    location_match = re.search(pattern, content, re.IGNORECASE)
                    if location_match and location_match.group(1).strip():
                        location = location_match.group(1).strip()
                        break
                
                # Try to extract description
                description_match = re.search(
                    r"(?:External\s+Description|Description|Responsibilities|Duties|Overview)\s*(.*?)(?=\n\n|\n[A-Z]|$)",
                    content, 
                    re.IGNORECASE | re.DOTALL
                )
                if description_match:
                    job_description = description_match.group(1).strip()
                    if len(job_description) > 200:
                        job_description = job_description[:197] + "..."
                
                # Generate reasoning based on the job description
                reasoning = f"This position matches your preferences with a {score}% compatibility score."
                if job_description:
                    reasoning = f"{reasoning} The role involves {job_description}"
                
                # Create job recommendation object
                job = {
                    "title": job_title,
                    "company": company,
                    "location": location,
                    "match_score": score,
                    "reasoning": reasoning,
                    "url": f"https://console.aws.amazon.com/s3/object/{bucket}/{key}"
                }
                
                job_recommendations.append(job)
                debug(f"Successfully processed job: {job_title}")
                
            except Exception as e:
                app_logger.error(f"Error processing result {i}: {str(e)}")
                debug(f"Result processing error: {str(e)}")
        
        # If we couldn't retrieve any jobs, fall back to sample data
        if not job_recommendations:
            debug("No jobs retrieved from Bedrock, falling back to sample data")
            job_recommendations = [
                {
                    "title": "CANT FIND A JOB",
                    "company": "PLACEHOLDER",
                    "location": "PLACEHOLDER",
                    "match_score": 0,
                    "reasoning": "PLACEHOLDER",
                    "url": "https://careers.oracle.com/jobs"
                }
            ]
            
            job_recommendations = [
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
                },
                {
                    "title": "Technical Documentation Specialist",
                    "company": "Oracle",
                    "location": "Remote",
                    "match_score": 85,
                    "reasoning": "Fallback job match for neurodiverse candidates. This role offers flexible remote work with minimal interruptions.",
                    "url": "https://careers.oracle.com/jobs"
                },
                {
                    "title": "Database Administrator",
                    "company": "Oracle",
                    "location": "Denver, CO",
                    "match_score": 82, 
                    "reasoning": "Fallback job match for neurodiverse candidates. This role features clear procedures and predictable interactions.",
                    "url": "https://careers.oracle.com/jobs"
                }
            ]
        
        # Sort by match score
        job_recommendations.sort(key=lambda x: x["match_score"], reverse=True)
        
        # Limit to top 10
        job_recommendations = job_recommendations[:10]
        
        debug(f"Returning {len(job_recommendations)} job recommendations")
        return job_recommendations

    except Exception as e:
        app_logger.error(f"Error generating job recommendations: {str(e)}")
        debug(f"Job recommendation error: {str(e)}")
        return []

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)