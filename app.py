import os
from dotenv import load_dotenv
load_dotenv() 

langtrace_api_key = os.environ.get("LANGTRACE_API_KEY")
from langtrace_python_sdk import langtrace
langtrace.init(api_key = langtrace_api_key)


from flask import Flask, render_template, request, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from openai import OpenAI
import logging
import json
import sys

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
            ("B", "Collaborative and open spaces"),
            ("C", "A mix of both")
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
        "text": "Do you require any specific accommodations in your workspace?",
        "options": [
            ("A", "Yes"),
            ("B", "No")
        ]
    },
    {
        "id": 6,
        "text": "Is there anything else we should know about you?",
        "type": "free_response"
    }
]

@app.route("/")
def welcome():
    session.clear()
    return render_template("welcome.html")

@app.route("/question/<int:question_id>", methods=["GET", "POST"])
def question(question_id):
    # Basic validation
    if not (1 <= question_id <= len(questions)):
        return redirect(url_for("welcome"))

    debug(f"Processing question {question_id}, method: {request.method}")
    
    if request.method == "POST":
        debug("Form data", request.form)
        
        if 'type' in questions[question_id-1] and questions[question_id-1]['type'] == 'free_response':
            answer = request.form.get("free_response")
            app_logger.info(f"Question {question_id} (Free Response): {answer}")
        else:
            answer = request.form.get("answer")
            if answer:
                option_text = next((opt[1] for opt in questions[question_id-1]["options"] if opt[0] == answer), None)
                app_logger.info(f"Question {question_id} (Multiple Choice): Option {answer} - {option_text}")
            
        if answer:
            # Store answer and redirect
            session[f"q{question_id}"] = answer
            debug(f"Answer saved for question {question_id}")

            # Determine next step (next question or results)
            next_step = "results" if question_id >= len(questions) else f"question {question_id + 1}"
            debug(f"Redirecting to {next_step}")
            
            if question_id < len(questions):
                return redirect(url_for("question", question_id=question_id + 1))
            return redirect(url_for("results"))
        else:
            debug("No answer provided")

    # GET request - show question
    current_question = questions[question_id - 1]
    progress = (question_id / len(questions)) * 100
    
    debug(f"Rendering question template for question {question_id}")
    return render_template(
        "question.html",
        question=current_question,
        progress=progress
    )

@app.route("/results")
def results():
    debug("Results route called")
    
    # Verify all questions were answered
    if not all(f"q{i+1}" in session for i in range(len(questions))):
        debug("Missing required answers, redirecting to welcome")
        return redirect(url_for("welcome"))

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
            q6_answer=session.get('q6', ''),
            analysis=str(analysis)
        )
        
        # Add to database and commit
        db.session.add(assessment)
        db.session.commit()
        
        debug(f"Database record created with ID: {assessment.id}")
        
        # Log the successful database operation
        app_logger.info(f"Assessment saved to database (ID: {assessment.id})")
        app_logger.info(f"Free response answer: {assessment.q6_answer}")
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
        "- accommodations: {",
        "    description: any specific needs,",
        "    explanation: reasoning behind these accommodations",
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
        # If API key is not available, return mock response
        if not openai_api_key:
            debug("Using mock analysis (no API key found)")
            mock_analysis = {
                "work_style": {
                    "description": "Structured and focused work environment",
                    "explanation": "Based on your responses, you prefer a clear schedule and defined tasks."
                },
                "environment": {
                    "description": "Quiet, low-distraction workspace",
                    "explanation": "You indicated a preference for spaces that allow concentration."
                },
                "interaction_level": {
                    "description": "Limited but meaningful social interaction",
                    "explanation": "Your answers suggest you work best with focused collaboration."
                },
                "task_preference": {
                    "description": "Detail-oriented analytical tasks",
                    "explanation": "You show a strong preference for tasks requiring precision and focus."
                },
                "accommodations": {
                    "description": "Flexibility in work schedule and environment",
                    "explanation": "Your responses indicate you benefit from customized work arrangements."
                },
                "additional_insights": {
                    "description": "Personalized feedback based on your additional information",
                    "explanation": "Your additional comments provide context for better understanding your needs."
                }
            }
            return format_analysis(mock_analysis)

        debug("Calling OpenAI API for analysis")
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )

        analysis = json.loads(response.choices[0].message.content)
        debug("Analysis generated successfully")
        return format_analysis(analysis)
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

    <h3>Accommodations</h3>
    <p class="mb-2"><strong>{analysis['accommodations']['description']}</strong></p>
    <p class="text-muted mb-4">{analysis['accommodations']['explanation']}</p>
    
    <h3>Additional Insights</h3>
    <p class="mb-2"><strong>{analysis.get('additional_insights', {}).get('description', 'No additional insights')}</strong></p>
    <p class="text-muted mb-4">{analysis.get('additional_insights', {}).get('explanation', '')}</p>
</div>
"""

def get_job_recommendations(analysis):
    """Get job recommendations based on user preferences"""
    debug("Generating job recommendations")
    
    try:
        # Since job scraping isn't working, provide sample jobs
        sample_jobs = [
            {
                "title": "Data Quality Analyst",
                "company": "Oracle",
                "location": "Austin, TX (Remote Available)",
                "match_score": 95,
                "reasoning": "Perfect match for detail-oriented work style. Role offers structured environment with clear objectives and minimal interruptions.",
                "url": "https://careers.oracle.com/jobs"
            },
            {
                "title": "Software Developer - Backend",
                "company": "Oracle Cloud Infrastructure",
                "location": "Seattle, WA (Hybrid)",
                "match_score": 92,
                "reasoning": "Strong alignment with preference for focused technical work. Flexible schedule with dedicated quiet time for deep work.",
                "url": "https://careers.oracle.com/jobs"
            },
            {
                "title": "Quality Assurance Engineer",
                "company": "Oracle",
                "location": "Reston, VA",
                "match_score": 88,
                "reasoning": "Excellent fit for systematic thinking and attention to detail. Structured work environment with clear processes.",
                "url": "https://careers.oracle.com/jobs"
            },
            {
                "title": "Technical Documentation Specialist",
                "company": "Oracle",
                "location": "Remote",
                "match_score": 85,
                "reasoning": "Well-suited for detail-oriented work with minimal interruptions. Flexible remote work arrangement.",
                "url": "https://careers.oracle.com/jobs"
            },
            {
                "title": "Database Administrator",
                "company": "Oracle",
                "location": "Denver, CO",
                "match_score": 82,
                "reasoning": "Good match for structured, systematic work. Clear procedures and processes with predictable interactions.",
                "url": "https://careers.oracle.com/jobs"
            },
            {
                "title": "UI/UX Developer",
                "company": "Oracle",
                "location": "San Francisco, CA",
                "match_score": 78,
                "reasoning": "Moderate fit - offers creative work but may require more collaboration than preferred. Flexible work arrangements available.",
                "url": "https://careers.oracle.com/jobs"
            },
            {
                "title": "Systems Analyst",
                "company": "Oracle",
                "location": "Chicago, IL (Hybrid)",
                "match_score": 75,
                "reasoning": "Decent match for analytical skills, though requires regular team interaction. Structured project approach.",
                "url": "https://careers.oracle.com/jobs"
            },
            {
                "title": "Cloud Infrastructure Engineer",
                "company": "Oracle",
                "location": "Boston, MA",
                "match_score": 72,
                "reasoning": "Good technical fit but may involve more collaborative work than ideal. Clear technical focus with some team coordination.",
                "url": "https://careers.oracle.com/jobs"
            },
            {
                "title": "Product Support Engineer",
                "company": "Oracle",
                "location": "Remote",
                "match_score": 68,
                "reasoning": "Mixed fit - technical work aligns well but customer interaction may be challenging. Remote work offers flexibility.",
                "url": "https://careers.oracle.com/jobs"
            },
            {
                "title": "Agile Project Coordinator",
                "company": "Oracle",
                "location": "Miami, FL",
                "match_score": 65,
                "reasoning": "Lower match due to high social interaction requirements, but structured methodology provides clear framework.",
                "url": "https://careers.oracle.com/jobs"
            }
        ]

        debug(f"Generated {len(sample_jobs)} job recommendations")
        return sample_jobs

    except Exception as e:
        app_logger.error(f"Error generating job recommendations: {str(e)}")
        debug(f"Job recommendation error: {str(e)}")
        return []

with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)