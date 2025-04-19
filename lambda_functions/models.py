from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime

class Assessment(BaseModel):
    id: str  # UUID as string
    q1_answer: str
    q2_answer: str
    q3_answer: str
    q4_answer: str
    q5_answer: Optional[str] = None  # Free response text
    analysis: Optional[str] = None
    created_at: datetime = datetime.utcnow()

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "q1_answer": "A",
                "q2_answer": "B",
                "q3_answer": "A",
                "q4_answer": "C",
                "q5_answer": "I prefer a calm work environment with minimal distractions.",
                "analysis": "Analysis results will be stored here",
                "created_at": "2023-04-18T12:34:56.789Z"
            }
        }

class AnalysisResult(BaseModel):
    strengths: List[str]
    challenges: List[str]
    work_style: str
    environment: str
    additional_notes: Optional[List[str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "strengths": ["Detail-oriented", "Focused", "Analytical"],
                "challenges": ["Social interactions", "Multitasking", "Noise sensitivity"],
                "work_style": "Prefers structured work with clear expectations",
                "environment": "Quiet, low-distraction workspace with minimal interruptions",
                "additional_notes": ["May benefit from noise-cancelling headphones", "Prefers written instructions"]
            }
        }

class JobRecommendation(BaseModel):
    title: str
    description: str
    fit_score: float
    strengths_match: List[str]
    considerations: Optional[List[str]] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "title": "Data Analyst",
                "description": "Analyzes complex datasets to extract insights and patterns",
                "fit_score": 0.87,
                "strengths_match": ["Attention to detail", "Analytical thinking", "Pattern recognition"],
                "considerations": ["May require occasional team meetings", "Some client interaction might be needed"]
            }
        } 