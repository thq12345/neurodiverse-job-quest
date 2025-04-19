from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import os
import logging
from pydantic import BaseModel
from typing import Dict, List, Optional, Any, Union
import uuid
import json

# Import project files
from utils import QUESTIONS, create_response, save_assessment, create_dynamodb_table, ASSESSMENT_TABLE_NAME
from models import Assessment

# Configure logging
logger = logging.getLogger("questionnaire-api")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

# Initialize FastAPI app
app = FastAPI(title="Neurodiverse Job Quest API",
              description="API for the Neurodiverse Job Quest questionnaire",
              version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

class QuestionnaireResponse(BaseModel):
    q1: str
    q2: str
    q3: str
    q4: str
    q5: Optional[str] = None

@app.on_event("startup")
async def startup_db_client():
    """Initialize DynamoDB table on startup"""
    try:
        create_dynamodb_table(ASSESSMENT_TABLE_NAME)
        logger.info(f"DynamoDB table '{ASSESSMENT_TABLE_NAME}' is ready")
    except Exception as e:
        logger.error(f"Error initializing DynamoDB table: {e}")

@app.get("/questionnaire", response_model=Dict[str, List[Dict[str, Any]]])
async def get_questionnaire():
    """
    Return the questionnaire questions and options.
    """
    logger.info("Questionnaire requested")
    return {"questions": QUESTIONS}

@app.post("/submit_questionnaire", response_model=Dict[str, str])
async def submit_questionnaire(response: QuestionnaireResponse):
    """
    Submit questionnaire responses and return an assessment ID.
    """
    logger.info(f"Questionnaire submission received: {response}")
    
    # Create assessment object
    assessment_data = {
        "id": str(uuid.uuid4()),
        "q1_answer": response.q1,
        "q2_answer": response.q2,
        "q3_answer": response.q3,
        "q4_answer": response.q4,
        "q5_answer": response.q5 if response.q5 else "",
    }
    
    # Save to DynamoDB
    try:
        assessment_id = save_assessment(assessment_data)
        logger.info(f"Assessment saved with ID: {assessment_id}")
        return {"assessment_id": assessment_id}
    except Exception as e:
        logger.error(f"Error saving assessment: {e}")
        raise HTTPException(status_code=500, detail=f"Error saving assessment: {str(e)}")

# Create Lambda handler
handler = Mangum(app)

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000) 