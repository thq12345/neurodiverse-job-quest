# from langtrace_python_sdk import langtrace
# import os
# from dotenv import load_dotenv
# load_dotenv() 

# langtrace_api_key = os.environ.get("LANGTRACE_API_KEY")
# langtrace.init(api_key=langtrace_api_key)

from crewai import Agent, Crew, Task
import json
import logging
import re
from typing import Dict, Any, List, Optional
import io
import PyPDF2


app_logger = logging.getLogger('app')

class JobAnalyzer:
    """
    Uses CrewAI to analyze job descriptions from Bedrock knowledge base,
    extract structured information, and generate personalized matching reasons.
    """
    
    def __init__(self, s3_client=None, debug_func=None, user_profile=None):
        """
        Initialize the job analyzer.
        
        Args:
            s3_client: AWS S3 client for retrieving job documents
            debug_func: Function for debug logging
            user_profile: Dict containing user profile information from questionnaire
        """
        self.s3_client = s3_client
        self.debug = debug_func or (lambda *args, **kwargs: None)
        self.user_profile = user_profile or {}
        
    def create_extraction_agent(self) -> Agent:
        """Create the agent responsible for extracting structured data from job descriptions"""
        return Agent(
            role="Job Information Extractor",
            goal="Extract accurate structured information from job descriptions",
            backstory="""You are an expert at analyzing job descriptions and extracting
            key information in a structured format. You can identify job titles, companies,
            locations, and key responsibilities even when this information is embedded in
            complex documents.""",
            verbose=True,
            allow_delegation=False,
            metadata={
                "langtrace": {
                    "agent_name": "job_information_extractor",
                    "agent_type": "extraction"
                }
            }
        )
    
    def create_matching_agent(self) -> Agent:
        """Create the agent responsible for generating personalized job matching reasoning"""
        return Agent(
            role="Job Match Analyst",
            goal="Generate personalized reasons why a job matches a candidate's preferences",
            backstory="""You are an expert at matching job characteristics to candidate preferences.
            You can analyze a job description and a candidate's profile to identify specific aspects
            of the job that align with the candidate's work style, environment needs, interaction 
            preferences, and task preferences.""",
            verbose=True,
            allow_delegation=False,
            metadata={
                "langtrace": {
                    "agent_name": "job_match_analyst",
                    "agent_type": "matching"
                }
            }
        )
    
    def create_extraction_task(self, agent: Agent, job_content: str, job_uri: str) -> Task:
        """Create the task for extracting structured data from a job description"""
        return Task(
            description=f"""
            Extract the following information from this job description:
            
            Job Content: "{job_content[:5000]}..." (truncated for length)
            Source URI: {job_uri}
            
            Return a JSON object with these fields:
            - title: The job title
            - company: The company or organization
            - location: The job location (city, state, remote status)
            - responsibilities: A brief summary of key responsibilities (1-2 sentences)
            - requirements: A brief summary of key requirements (1-2 sentences)
            - benefits: Any mentioned benefits or perks (if available)
            
            If any field cannot be confidently extracted, use a reasonable default based on the document.
            """,
            agent=agent,
            expected_output="""
            {
                "title": "Job Title",
                "company": "Company Name",
                "location": "Location",
                "responsibilities": "Key responsibilities summary",
                "requirements": "Key requirements summary",
                "benefits": "Benefits summary or 'Not specified'"
            }
            """,
            metadata={
                "langtrace": {
                    "task_name": "job_info_extraction",
                    "job_uri": job_uri
                }
            }
        )
    
    def create_matching_task(self, agent: Agent, job_info: Dict[str, Any], user_profile: Dict[str, Any]) -> Task:
        """Create the task for generating personalized job matching reasoning"""
        return Task(
            description=f"""
            Generate a personalized explanation for why this job matches the candidate's preferences:
            
            JOB INFORMATION:
            {json.dumps(job_info, indent=2)}
            
            CANDIDATE PROFILE:
            {json.dumps(user_profile, indent=2)}
            
            Return a JSON object with:
            - match_reasoning: A 1-2 sentence personalized explanation of why this job is a good match
            - match_score: A score from 0-100 indicating how well the job matches the candidate (where 100 is perfect)
            - key_highlights: 2-3 bullet points (very short phrases) highlighting job aspects that match preferences
            """,
            agent=agent,
            expected_output="""
            {
                "match_reasoning": "This job is a great match because...",
                "match_score": 85,
                "key_highlights": [
                    "Flexible schedule",
                    "Quiet work environment",
                    "Detailed technical tasks"
                ]
            }
            """,
            metadata={
                "langtrace": {
                    "task_name": "job_matching_analysis",
                    "job_title": job_info.get("title", "Unknown Position")
                }
            }
        )
    
    def extract_text_from_content(self, content_bytes: bytes, uri: str) -> str:
        """Extract text content from binary data (PDF or plain text)"""
        try:
            # Check if it's a PDF (starts with %PDF)
            if content_bytes.startswith(b'%PDF'):
                self.debug(f"Processing PDF document from {uri}")
                # Parse PDF using PyPDF2
                pdf_reader = PyPDF2.PdfReader(io.BytesIO(content_bytes))
                content = ""
                for page in range(len(pdf_reader.pages)):
                    content += pdf_reader.pages[page].extract_text() + "\n"
                return content
            else:
                # Assume it's plain text
                return content_bytes.decode("utf-8", errors="ignore")
        except Exception as e:
            self.debug(f"Error extracting text from {uri}: {str(e)}")
            return f"Error extracting text: {str(e)}"
    
    def retrieve_and_process_content(self, s3_uri: str, bedrock_score: int) -> Optional[Dict[str, Any]]:
        """Retrieve job content from S3 and process it with CrewAI agents"""
        try:
            if not self.s3_client:
                self.debug("S3 client not available, returning generic job info")
                return {
                    "title": f"Job from {s3_uri}",
                    "company": "Unknown Company", 
                    "location": "Unknown Location",
                    "match_score": bedrock_score,
                    "reasoning": "Unable to access job details without S3 client.",
                    "url": s3_uri
                }
            
            # Parse the S3 URI to get bucket and key
            bucket, key = s3_uri.replace("s3://", "").split("/", 1)
            
            # Get the document from S3
            self.debug(f"Retrieving S3 object {bucket}/{key}")
            obj = self.s3_client.get_object(Bucket=bucket, Key=key)
            content_bytes = obj["Body"].read()
            
            # Extract text content
            content = self.extract_text_from_content(content_bytes, s3_uri)
            
            if not content or len(content.strip()) < 50:
                self.debug(f"Retrieved content too short or empty from {s3_uri}")
                return None
                
            self.debug(f"Content extracted from {s3_uri}, length: {len(content)} characters")
            
            # Create extraction agent and task
            extractor = self.create_extraction_agent()
            extraction_task = self.create_extraction_task(extractor, content, s3_uri)
            
            # Run the extraction task with Langtrace tracing
            extraction_crew = Crew(
                agents=[extractor],
                tasks=[extraction_task],
                verbose=True,
                metadata={
                    "langtrace": {
                        "crew_name": "job_extraction_crew",
                        "job_uri": s3_uri
                    }
                }
            )
            
            extraction_result = extraction_crew.kickoff()
            self.debug(f"Extraction complete for {s3_uri}")
            
            # Parse the extraction result to get structured job info
            job_info = self._parse_json_result(extraction_result)
            if not job_info:
                self.debug(f"Failed to extract structured data from {s3_uri}")
                return None
                
            self.debug(f"Successfully extracted job info: {job_info.get('title', 'Unknown Title')}")
            
            # Create matching agent and task
            matcher = self.create_matching_agent()
            matching_task = self.create_matching_task(matcher, job_info, self.user_profile)
            
            # Run the matching task with Langtrace tracing
            matching_crew = Crew(
                agents=[matcher],
                tasks=[matching_task],
                verbose=True,
                metadata={
                    "langtrace": {
                        "crew_name": "job_matching_crew",
                        "job_title": job_info.get("title", "Unknown Position")
                    }
                }
            )
            
            matching_result = matching_crew.kickoff()
            self.debug(f"Matching analysis complete for {s3_uri}")
            
            # Parse the matching result
            match_info = self._parse_json_result(matching_result)
            if not match_info:
                self.debug(f"Failed to generate matching info for {s3_uri}")
                match_info = {
                    "match_reasoning": f"This position matches your preferences with a {bedrock_score}% compatibility score.",
                    "match_score": bedrock_score,
                    "key_highlights": ["Job details extracted successfully"]
                }
            
            # Calculate final score - simple average of Bedrock score and agent score
            if 'match_score' in match_info:
                agent_score = match_info['match_score']
                # Simple average of Bedrock and agent scores
                final_score = (bedrock_score + agent_score) // 2
                self.debug(f"Score calculation: Bedrock score {bedrock_score} + Agent score {agent_score} = Average {final_score}")
            else:
                final_score = bedrock_score
                
            # Combine the extracted info and matching info
            result = {
                "title": job_info.get("title", "Unknown Position"),
                "company": job_info.get("company", "Unknown Company"),
                "location": job_info.get("location", "Unknown Location"),
                "match_score": final_score,
                "reasoning": match_info.get("match_reasoning", f"This position matches your preferences with a {final_score}% compatibility score."),
                "highlights": match_info.get("key_highlights", []),
                "url": f"https://console.aws.amazon.com/s3/object/{bucket}/{key}",
                "bedrock_score": bedrock_score,  # Include the original Bedrock score for reference
                "agent_score": match_info.get("match_score", 0)  # Include the agent score for reference
            }
            
            return result
            
        except Exception as e:
            self.debug(f"Error processing job from {s3_uri}: {str(e)}")
            return None
    
    def _parse_json_result(self, result) -> Dict[str, Any]:
        """Parse JSON from CrewAI result output"""
        try:
            # First try to access the result directly
            if hasattr(result, 'result') and isinstance(result.result, dict):
                return result.result
                
            # If that fails, try to parse JSON from the output
            result_str = str(result)
            json_match = re.search(r'\{.*\}', result_str, re.DOTALL)
            if json_match:
                return json.loads(json_match.group(0))
            
            # If we have raw_output attribute
            if hasattr(result, 'raw_output'):
                json_match = re.search(r'\{.*\}', result.raw_output, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
            
            return {}
        except Exception as e:
            self.debug(f"Error parsing JSON result: {str(e)}")
            return {}
    
    def process_job_results(self, retrieval_results: List[Dict[str, Any]], bedrock_score: int = None) -> List[Dict[str, Any]]:
        """
        Process a list of Bedrock retrieval results into structured job recommendations
        
        Args:
            retrieval_results: List of retrieval results from Bedrock
            bedrock_score: Optional consistent bedrock score to use for all recommendations (0-100)
        
        Returns:
            List of structured job recommendations
        """
        job_recommendations = []
        
        for i, result in enumerate(retrieval_results):
            try:
                # Extract S3 location information
                s3_uri = result["location"]["s3Location"]["uri"]
                
                # Use the provided consistent bedrock_score if available
                if bedrock_score is not None:
                    current_bedrock_score = bedrock_score
                    self.debug(f"Using consistent Bedrock score {current_bedrock_score} for all recommendations")
                else:
                    # Otherwise calculate individual scores
                    if 'score' in result:
                        current_bedrock_score = int(float(result['score']) * 100)
                    elif 'metadata' in result and 'score' in result['metadata']:
                        current_bedrock_score = int(float(result['metadata']['score']) * 100)
                    else:
                        current_bedrock_score = 75  # Default score if not available
                
                self.debug(f"Processing result {i+1} with Bedrock score {current_bedrock_score}, URI: {s3_uri}")
                
                # Process the job content with CrewAI
                job_info = self.retrieve_and_process_content(s3_uri, current_bedrock_score)
                
                if job_info:
                    job_recommendations.append(job_info)
                    self.debug(f"Added job to recommendations: {job_info.get('title', 'Unknown')}")
                
            except Exception as e:
                self.debug(f"Error processing result {i}: {str(e)}")
        
        # Sort recommendations by match score (descending)
        job_recommendations.sort(key=lambda x: x.get("match_score", 0), reverse=True)
        
        return job_recommendations 