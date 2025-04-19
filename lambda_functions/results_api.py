from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import os
import logging
import re
import io
import time
import uuid
from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Union
import json

# Import project files
from utils import (
    create_response, get_assessment, update_assessment, get_template_by_id, 
    get_job_by_id, get_jobs_by_ids, ASSESSMENT_TABLE_NAME, 
    ANALYSIS_TEMPLATES_TABLE_NAME, JOB_BANK_TABLE_NAME, KNOWLEDGE_BASE_ID,
    get_bedrock_client, get_s3_client
)
from models import Assessment, AnalysisResult, JobRecommendation
from job_analyzer import JobAnalyzer
from response_evaluator import ResponseEvaluator
from analysis_templates import get_analysis_for_combination

# Configure logging
logger = logging.getLogger("results-api")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

# Initialize AWS clients
s3_client = get_s3_client()
bedrock_client = get_bedrock_client()

# Initialize FastAPI app
app = FastAPI(title="Neurodiverse Job Quest Results API",
              description="API for the Neurodiverse Job Quest analysis results",
              version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Initialize analyzers
job_analyzer = JobAnalyzer(s3_client=s3_client)
response_evaluator = ResponseEvaluator()

class AnalysisResponse(BaseModel):
    analysis: Dict[str, Any]
    recommendations: List[Dict[str, Any]]
    profile: Dict[str, Any]

@app.get("/results/{assessment_id}", response_model=AnalysisResponse)
async def get_results(assessment_id: str):
    """
    Get analysis results for a completed assessment.
    """
    logger.info(f"Results requested for assessment ID: {assessment_id}")
    
    # Get assessment from DynamoDB
    assessment = get_assessment(assessment_id)
    
    if not assessment:
        logger.warning(f"Assessment not found: {assessment_id}")
        raise HTTPException(status_code=404, detail="Assessment not found")
    
    # Check if analysis already exists
    if assessment.get('analysis'):
        try:
            analysis_data = json.loads(assessment['analysis'])
            logger.info(f"Using cached analysis for assessment ID: {assessment_id}")
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in analysis field for assessment ID: {assessment_id}")
            analysis_data = {}
    else:
        # Perform analysis
        logger.info(f"Performing new analysis for assessment ID: {assessment_id}")
        analysis_data = analyze_responses({
            "q1": assessment["q1_answer"],
            "q2": assessment["q2_answer"],
            "q3": assessment["q3_answer"],
            "q4": assessment["q4_answer"],
            "q5": assessment["q5_answer"]
        })
        
        # Update assessment with analysis
        logger.info(f"Saving analysis results for assessment ID: {assessment_id}")
        update_assessment(assessment_id, {
            "analysis": json.dumps(analysis_data)
        })
    
    # Get job recommendations
    answers = {
        "q1": assessment["q1_answer"],
        "q2": assessment["q2_answer"],
        "q3": assessment["q3_answer"],
        "q4": assessment["q4_answer"],
        "q5": assessment["q5_answer"]
    }
    recommendations = get_job_recommendations(analysis_data, answers)
    
    # Extract user profile
    profile = extract_user_profile(analysis_data)
    
    return {
        "analysis": analysis_data,
        "recommendations": recommendations,
        "profile": profile
    }

def analyze_responses(answers):
    """Analyze questionnaire responses to determine profile and preferences"""
    # Get template analysis based on response combination
    template_analysis = get_analysis_for_combination(
        answers["q1"], 
        answers["q2"], 
        answers["q3"], 
        answers["q4"]
    )
    
    # Enhance with free-text response if provided
    if answers.get("q5") and answers["q5"].strip():
        enhanced_analysis = response_evaluator.evaluate_free_response(
            template_analysis, 
            answers["q5"]
        )
        return enhanced_analysis
    
    return template_analysis

def get_job_recommendations(analysis, answers):
    """Get job recommendations based on analysis results"""
    # Check if q5 (free response) is empty - if it is, use recommended_jobs from DynamoDB
    q5_response = answers.get('q5', '')
    if not q5_response or not q5_response.strip():
        logger.info("Question 5 is empty, using recommended_jobs from analysis template")
        return get_recommendations_from_dynamo(answers)
    else:
        logger.info("Question 5 has content, using Bedrock for recommendations")
        return get_recommendations_from_bedrock(analysis)

def get_recommendations_from_dynamo(answers):
    """Get job recommendations from recommended_jobs in the analysis template"""
    try:
        # Get the template ID based on the user's answers to questions 1-4
        template_id = (
            answers.get('q1', 'A') + 
            answers.get('q2', 'A') + 
            answers.get('q3', 'A') + 
            answers.get('q4', 'A')
        )
        
        logger.info(f"Looking up template with ID: {template_id}")
        
        # Get the template with recommended_jobs
        template = get_template_by_id(template_id)
        if not template:
            logger.warning(f"Template {template_id} not found, using fallback")
            return get_fallback_recommendations()
        
        logger.info(f"Template found: {template}")
        
        # Check if recommended_jobs exists and parse it from JSON if needed
        if 'recommended_jobs' in template:
            # If recommended_jobs is a string (JSON), parse it
            recommended_jobs = template['recommended_jobs']
            if isinstance(recommended_jobs, str):
                try:
                    recommended_jobs = json.loads(recommended_jobs)
                    logger.info(f"Parsed recommended_jobs from JSON: {recommended_jobs}")
                except:
                    logger.warning("Failed to parse recommended_jobs from JSON")
            matching_job_ids = recommended_jobs
        else:
            # For backward compatibility, check for matching_jobs
            matching_job_ids = template.get('matching_jobs', [])
        
        logger.info(f"Found job IDs: {matching_job_ids}")
        
        if not matching_job_ids:
            logger.warning("No job IDs found, using fallback")
            return get_fallback_recommendations()
        
        # Retrieve each matching job
        job_recommendations = []
        for job_id in matching_job_ids:
            try:
                # Convert to integer if it's a string
                if isinstance(job_id, str) and job_id.isdigit():
                    job_id = int(job_id)
                
                logger.info(f"Looking up job with ID: {job_id}")
                job = get_job_by_id(job_id)
                if job:
                    job_recommendations.append(job)
                else:
                    logger.warning(f"Job ID {job_id} not found in JobBank")
            except Exception as e:
                logger.error(f"Error retrieving job ID {job_id}: {str(e)}")
        
        logger.info(f"Retrieved {len(job_recommendations)} jobs from JobBank")
        
        if not job_recommendations:
            logger.warning("Failed to retrieve any matching jobs, using fallback")
            return get_fallback_recommendations()
        
        return job_recommendations
        
    except Exception as e:
        logger.error(f"Error retrieving recommendations from DynamoDB: {str(e)}")
        return get_fallback_recommendations()

def get_recommendations_from_bedrock(analysis):
    """Get job recommendations from Bedrock knowledge base"""
    trace_id = str(uuid.uuid4())
    
    try:
        # Extract key points from the analysis to form a query
        query = "Find job postings suitable for someone who:"
        
        # More robust check for valid HTML format
        is_valid_html = False
        if isinstance(analysis, str):
            is_valid_html = analysis.strip().startswith("<div")
        
        if not is_valid_html:
            logger.warning("Analysis is not valid HTML, using generic query")
            query = "Find entry-level tech jobs suitable for neurodiverse candidates"
        else:
            # Extract key points from the analysis HTML
            logger.info("Extracting key points from analysis for query")
            
            # Check for "not relevant" or similar in the additional insights
            not_relevant_check = re.search(r'Additional information not relevant|not useful for job recommendations', analysis, re.IGNORECASE)
            
            if not_relevant_check:
                logger.info("Found 'not relevant' in additional insights, using basic query plus MC answers")
                
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
        
        logger.info(f"Query for Bedrock: {query}")
        
        # Query the Bedrock knowledge base with retry logic for auto-pause situations
        retrieval_results = []
        max_retries = 3
        retry_delay = 5  # seconds
        
        for attempt in range(max_retries):
            try:
                logger.info(f"Querying Bedrock knowledge base (attempt {attempt+1}/{max_retries})")
                response = bedrock_client.retrieve(
                    knowledgeBaseId=KNOWLEDGE_BASE_ID,
                    retrievalQuery={"text": query},
                    retrievalConfiguration={
                        "vectorSearchConfiguration": {
                            "numberOfResults": 10  # Get top 10 results
                        }
                    }
                )
                
                retrieval_results = response.get('retrievalResults', [])
                logger.info(f"Retrieved {len(retrieval_results)} results from Bedrock")
                
                break  # Success, exit retry loop
                
            except Exception as e:
                logger.error(f"Error querying Bedrock (attempt {attempt+1}): {str(e)}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # Exponential backoff
                else:
                    logger.error("Max retries reached, failing over to fallback recommendations")
                    return get_fallback_recommendations()
        
        # Convert Bedrock results to job recommendations
        if not retrieval_results:
            logger.warning("No results from Bedrock, using fallback recommendations")
            return get_fallback_recommendations()
        
        # Process each result with the JobAnalyzer
        processed_results = []
        
        for i, result in enumerate(retrieval_results[:5]):  # Limit to top 5 results
            try:
                location = result.get('location', {}).get('s3Location', {})
                uri = f"s3://{location.get('uri', '')}"
                
                # Note: In a real implementation, you would process the content, but we'll simplify here
                processed_result = {
                    "title": f"Job {i+1} from Bedrock search",
                    "company": "Unknown Company",
                    "location": "Unknown Location",
                    "description": f"Job found based on your preferences. URI: {uri}",
                    "fit_score": (10 - i) / 10.0,  # Simple scoring based on rank
                    "strengths_match": ["Matches your work preferences", "Aligns with your skills"],
                    "considerations": ["Consider reaching out for more details"]
                }
                
                processed_results.append(processed_result)
            except Exception as e:
                logger.error(f"Error processing result {i}: {str(e)}")
        
        if not processed_results:
            logger.warning("Failed to process any Bedrock results, using fallback")
            return get_fallback_recommendations()
        
        return processed_results
        
    except Exception as e:
        logger.error(f"Error in Bedrock recommendation flow: {str(e)}")
        return get_fallback_recommendations()

def get_fallback_recommendations():
    """Return fallback job recommendations when other methods fail"""
    logger.info("Using fallback job recommendations")
    
    fallback_jobs = [
        {
            "title": "Software Developer",
            "company": "Tech Solutions Inc.",
            "location": "Remote",
            "description": "Develop and maintain software applications using modern programming languages and frameworks.",
            "fit_score": 0.85,
            "strengths_match": ["Detail-oriented tasks", "Structured environment", "Technical focus"],
            "considerations": ["May involve some team meetings", "Deadlines can vary"]
        },
        {
            "title": "Data Analyst",
            "company": "Data Insights Corp",
            "location": "Remote / Hybrid",
            "description": "Analyze complex datasets to extract insights and create reports for business stakeholders.",
            "fit_score": 0.82,
            "strengths_match": ["Pattern recognition", "Detailed analysis", "Independent work"],
            "considerations": ["May require some presentations", "Occasional client interaction"]
        },
        {
            "title": "Quality Assurance Specialist",
            "company": "Quality First Tech",
            "location": "Remote",
            "description": "Ensure software quality through systematic testing and documentation of issues.",
            "fit_score": 0.78,
            "strengths_match": ["Attention to detail", "Systematic approach", "Process-oriented"],
            "considerations": ["Daily team check-ins", "May require schedule flexibility"]
        }
    ]
    
    return fallback_jobs

def extract_user_profile(analysis):
    """Extract user profile highlights from analysis"""
    if isinstance(analysis, str):
        # If analysis is HTML string, extract key points
        strengths = re.findall(r'<li>(.*?)</li>', analysis)
        
        # Get work style and environment from the HTML
        work_style_match = re.search(r'Work Style:</strong>\s*(.*?)<', analysis)
        work_style = work_style_match.group(1) if work_style_match else "Flexible work style"
        
        env_match = re.search(r'Environment:</strong>\s*(.*?)<', analysis)
        environment = env_match.group(1) if env_match else "Adaptable to various environments"
        
        # Use first 3 list items as strengths if available
        return {
            "strengths": strengths[:3] if strengths else ["Detail-oriented", "Focused", "Analytical"],
            "challenges": ["Social interactions", "Multitasking", "Noise sensitivity"],
            "work_style": work_style,
            "environment": environment
        }
    elif isinstance(analysis, dict):
        # If analysis is dictionary, extract directly
        return {
            "strengths": analysis.get("strengths", [])[:3],
            "challenges": analysis.get("challenges", [])[:3],
            "work_style": analysis.get("work_style", ""),
            "environment": analysis.get("environment", "")
        }
    else:
        # Fallback
        return {
            "strengths": ["Detail-oriented", "Focused", "Analytical"],
            "challenges": ["Social interactions", "Multitasking", "Noise sensitivity"],
            "work_style": "Structured and predictable",
            "environment": "Quiet, low-distraction workspace"
        }

# Create Lambda handler
handler = Mangum(app)

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001) 