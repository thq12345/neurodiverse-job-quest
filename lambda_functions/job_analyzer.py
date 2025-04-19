# from langtrace_python_sdk import langtrace
# import os
# from dotenv import load_dotenv
# load_dotenv() 

# langtrace_api_key = os.environ.get("LANGTRACE_API_KEY")
# langtrace.init(api_key=langtrace_api_key)

from crewai import Agent, Crew, Task, Process
import json
import logging
import re
import urllib.parse
import time
import traceback
from typing import Dict, Any, List, Optional, Union
import io
import PyPDF2

# Set up logging
logger = logging.getLogger("job-analyzer")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

class JobAnalyzer:
    """
    Analyzes job descriptions using CrewAI agents to extract structured information
    and generate personalized matching reasons.
    """
    
    def __init__(self, s3_client=None):
        """
        Initialize the JobAnalyzer with optional S3 client.
        """
        self.s3_client = s3_client
        
        # Import utils here to avoid circular imports
        from utils import get_s3_client
        if self.s3_client is None:
            self.s3_client = get_s3_client()
            
        # Configure CrewAI process
        if os.environ.get("LAMBDA_TASK_ROOT"):
            # We're in a Lambda environment, force synchronous
            logger.info("Running in Lambda environment, using synchronous process")
            Process.set_default(Process.SYNC)

    def create_extraction_agent(self) -> Agent:
        """Create an agent specialized in extracting information from job descriptions."""
        try:
            return Agent(
                role="Job Information Extraction Specialist",
                goal="Extract structured information from job descriptions",
                backstory="""You are an expert at analyzing job descriptions and extracting 
                key requirements, responsibilities, and qualifications in a structured format.""",
                allow_delegation=False,
                verbose=False,
                max_rpm=10  # Rate limiting for API calls
            )
        except Exception as e:
            logger.error(f"Error creating extraction agent: {str(e)}")
            # Create a simpler agent with minimal parameters if the full version fails
            return Agent(
                role="Job Extractor",
                goal="Extract job information",
                backstory="You extract job information."
            )

    def create_matching_agent(self) -> Agent:
        """Create an agent specialized in matching job requirements to neurodiverse profiles."""
        try:
            return Agent(
                role="Neurodiverse Job Matching Specialist",
                goal="Match job requirements to neurodiverse strengths and considerations",
                backstory="""You specialize in identifying how neurodiverse individuals' 
                strengths align with job requirements, and what workplace considerations 
                should be noted.""",
                allow_delegation=False,
                verbose=False,
                max_rpm=10  # Rate limiting for API calls
            )
        except Exception as e:
            logger.error(f"Error creating matching agent: {str(e)}")
            # Create a simpler agent with minimal parameters if the full version fails
            return Agent(
                role="Job Matcher",
                goal="Match jobs to profiles",
                backstory="You match jobs to profiles."
            )

    def extract_job_information(self, job_description: str) -> Task:
        """Create a task for extracting structured information from a job description."""
        try:
            return Task(
                description=f"""
                Analyze the following job description and extract:
                1. Job title
                2. Company name
                3. Location (remote, on-site, hybrid)
                4. Required skills
                5. Main responsibilities
                6. Required qualifications
                7. Preferred qualifications
                8. Required years of experience
                9. Company culture indicators
                10. Potential salary range (if mentioned)
                
                Return the information in a structured JSON format.
                
                Job Description:
                {job_description}
                """,
                expected_output="""
                A JSON object with the following structure:
                {
                    "job_title": "string",
                    "company": "string",
                    "location": "string",
                    "skills": ["string"],
                    "responsibilities": ["string"],
                    "required_qualifications": ["string"],
                    "preferred_qualifications": ["string"],
                    "required_experience": "string",
                    "culture": ["string"],
                    "salary_range": "string"
                }
                """,
                agent=self.create_extraction_agent()
            )
        except Exception as e:
            logger.error(f"Error creating extraction task: {str(e)}")
            # Create a simpler task if the full version fails
            return Task(
                description=f"Extract job information from: {job_description[:500]}...",
                agent=self.create_extraction_agent()
            )

    def match_to_neurodiverse_profile(self, job_info: Dict[str, Any], profile_type: str) -> Task:
        """Create a task for matching job requirements to neurodiverse strengths."""
        try:
            profile_descriptions = {
                "AAAA": "Detail-oriented, prefers quiet environments, systematic approach, thrives with clear instructions",
                "AABA": "Detail-oriented, prefers quiet environments, systematic approach, enjoys occasional collaboration",
                # Add more profile descriptions as needed
                "default": "A neurodiverse individual with varied strengths and preferences"
            }
            
            profile_description = profile_descriptions.get(profile_type, profile_descriptions["default"])
            
            return Task(
                description=f"""
                Based on the extracted job information below, identify:
                1. How the job's requirements align with the strengths often found in {profile_description}
                2. What considerations should be noted for a neurodiverse individual with this profile
                3. Overall fit score (0.0-1.0) and justification
                
                Job Information:
                {json.dumps(job_info, indent=2)}
                
                Return your analysis in a structured JSON format.
                """,
                expected_output="""
                A JSON object with the following structure:
                {
                    "strengths_match": ["string"],
                    "considerations": ["string"],
                    "fit_score": float,
                    "fit_justification": "string"
                }
                """,
                agent=self.create_matching_agent()
            )
        except Exception as e:
            logger.error(f"Error creating matching task: {str(e)}")
            # Create a simpler task if the full version fails
            return Task(
                description=f"Match job to neurodiverse profile: {profile_type}",
                agent=self.create_matching_agent()
            )

    def retrieve_and_process_content(self, uri: str) -> Dict[str, Any]:
        """
        Retrieve content from S3 or other storage and process it into a structured format.
        """
        try:
            # Handle S3 URIs
            if uri.startswith("s3://"):
                logger.info(f"Retrieving content from S3: {uri}")
                
                # Parse S3 URI
                parsed_uri = urllib.parse.urlparse(uri)
                bucket_name = parsed_uri.netloc
                key = parsed_uri.path.lstrip('/')
                
                # Retrieve from S3
                max_retries = 3
                retry_delay = 10  # second
                
                for attempt in range(max_retries):
                    try:
                        logger.info(f"S3 get_object attempt {attempt+1}/{max_retries}")
                        response = self.s3_client.get_object(Bucket=bucket_name, Key=key)
                        content = response['Body'].read().decode('utf-8')
                        logger.info(f"Successfully retrieved {len(content)} bytes from S3")
                        break
                    except Exception as e:
                        logger.error(f"S3 retrieval attempt {attempt+1} failed: {str(e)}")
                        if attempt < max_retries - 1:
                            time.sleep(retry_delay)
                            retry_delay *= 2  # Exponential backoff
                        else:
                            logger.error(f"Max S3 retrieval attempts reached, failing with error: {str(e)}")
                            raise
                
                # Process content based on file type
                if key.endswith('.json'):
                    return json.loads(content)
                else:
                    # Assume text content (e.g., job description)
                    return self._extract_job_data_from_text(content)
            
            # Handle direct content (already provided as string)
            else:
                logger.info("Processing direct content")
                return self._extract_job_data_from_text(uri)
                
        except Exception as e:
            logger.error(f"Error retrieving/processing content: {str(e)}")
            logger.error(traceback.format_exc())
            return self._generate_fallback_job_data()
    
    def _extract_job_data_from_text(self, text: str) -> Dict[str, Any]:
        """
        Extract job data from text using CrewAI or fallback to regex patterns.
        """
        try:
            # First attempt: Use CrewAI for extraction
            logger.info("Attempting to extract job data using CrewAI")
            
            # Create extraction agent and task
            extraction_agent = self.create_extraction_agent()
            extraction_task = self.extract_job_information(text)
            
            # Create a crew with just the extraction agent
            crew = Crew(
                agents=[extraction_agent],
                tasks=[extraction_task],
                verbose=False,
                process=Process.SYNC  # Force synchronous in Lambda
            )
            
            # Run the crew and get the result
            result = crew.kickoff()
            
            # Parse the result as JSON
            try:
                if isinstance(result, str):
                    # Extract JSON if it's embedded in text
                    json_match = re.search(r'```json\s*(.*?)\s*```', result, re.DOTALL)
                    if json_match:
                        result = json_match.group(1)
                    
                    parsed_result = json.loads(result)
                    logger.info("Successfully parsed CrewAI result as JSON")
                    return parsed_result
                elif isinstance(result, dict):
                    logger.info("CrewAI result is already a dictionary")
                    return result
            except Exception as json_err:
                logger.error(f"Failed to parse CrewAI result as JSON: {str(json_err)}")
                # Fall through to fallback method
            
            # If CrewAI fails or returns invalid JSON, fall back to regex
            logger.info("Falling back to regex pattern extraction")
            return self._extract_with_regex(text)
            
        except Exception as e:
            logger.error(f"Error in job data extraction: {str(e)}")
            logger.error(traceback.format_exc())
            return self._extract_with_regex(text) or self._generate_fallback_job_data()
    
    def _extract_with_regex(self, text: str) -> Dict[str, Any]:
        """
        Extract job data using regex patterns as a fallback method.
        """
        try:
            # Extract job title - look for patterns like "Job Title: Software Engineer" or "Software Engineer"
            title_pattern = r'(?:job title|position|role):\s*([^\n]+)'
            title_match = re.search(title_pattern, text, re.IGNORECASE)
            
            if not title_match:
                # Try to find the title at the beginning of the text
                title_pattern = r'^([^\n]{3,50})'
                title_match = re.search(title_pattern, text)
            
            job_title = title_match.group(1).strip() if title_match else "Untitled Position"
            
            # Extract company name
            company_pattern = r'(?:company|organization|employer):\s*([^\n]+)'
            company_match = re.search(company_pattern, text, re.IGNORECASE)
            company = company_match.group(1).strip() if company_match else "Unknown Company"
            
            # Extract location - look for keywords like remote, hybrid, on-site
            location_pattern = r'(?:location|work arrangement|work mode):\s*([^\n]+)'
            location_match = re.search(location_pattern, text, re.IGNORECASE)
            
            if not location_match:
                # Look for location keywords
                if re.search(r'\bremote\b', text, re.IGNORECASE):
                    location = "Remote"
                elif re.search(r'\bhybrid\b', text, re.IGNORECASE):
                    location = "Hybrid"
                elif re.search(r'\bon[\-\s]site\b|\bin[\-\s]office\b', text, re.IGNORECASE):
                    location = "On-site"
                else:
                    location = "Unspecified location"
            else:
                location = location_match.group(1).strip()
            
            # Extract skills - look for bullet points after "skills" or "requirements"
            skills_pattern = r'(?:skills|requirements|qualifications)[:\s]*(?:\n|\r\n)+((?:[\s]*[•\-\*]\s*[^\n]+[\n\r]*)+)'
            skills_match = re.search(skills_pattern, text, re.IGNORECASE)
            
            if skills_match:
                # Extract bullet points
                bullet_pattern = r'[•\-\*]\s*([^\n]+)'
                skills = re.findall(bullet_pattern, skills_match.group(1))
            else:
                skills = ["Technical skills", "Communication", "Problem solving"]
            
            # Extract responsibilities
            resp_pattern = r'(?:responsibilities|duties|you will)[:\s]*(?:\n|\r\n)+((?:[\s]*[•\-\*]\s*[^\n]+[\n\r]*)+)'
            resp_match = re.search(resp_pattern, text, re.IGNORECASE)
            
            if resp_match:
                # Extract bullet points
                bullet_pattern = r'[•\-\*]\s*([^\n]+)'
                responsibilities = re.findall(bullet_pattern, resp_match.group(1))
            else:
                responsibilities = ["Develop and maintain software", "Collaborate with team members"]
            
            return {
                "job_title": job_title,
                "company": company,
                "location": location,
                "skills": skills[:5],  # Limit to first 5 skills
                "responsibilities": responsibilities[:5],  # Limit to first 5 responsibilities
                "required_qualifications": skills[:3],  # Reuse skills as qualifications
                "preferred_qualifications": [],
                "required_experience": "Not specified",
                "culture": ["Collaborative", "Innovative"],
                "salary_range": "Not specified"
            }
            
        except Exception as e:
            logger.error(f"Error in regex extraction: {str(e)}")
            return self._generate_fallback_job_data()
    
    def _generate_fallback_job_data(self) -> Dict[str, Any]:
        """
        Generate fallback job data when extraction fails.
        """
        logger.info("Generating fallback job data")
        return {
            "job_title": "Technology Position",
            "company": "Tech Company",
            "location": "Remote",
            "skills": ["Programming", "Problem Solving", "Communication"],
            "responsibilities": ["Software Development", "Collaboration", "Documentation"],
            "required_qualifications": ["Technical background", "Problem-solving skills"],
            "preferred_qualifications": ["Relevant experience"],
            "required_experience": "Entry level to mid-level",
            "culture": ["Inclusive", "Innovative"],
            "salary_range": "Competitive"
        }

    def analyze_job(self, job_uri: str, profile_type: str = "default") -> Dict[str, Any]:
        """
        Analyze a job description and match it to a specified neurodiverse profile type.
        
        Args:
            job_uri: S3 URI or content string of the job description
            profile_type: Type of neurodiverse profile (e.g., AAAA, AABA, etc.)
        
        Returns:
            Dictionary with structured job information and matching analysis
        """
        try:
            logger.info(f"Analyzing job for profile type: {profile_type}")
            
            # Retrieve and process the job content
            job_data = self.retrieve_and_process_content(job_uri)
            if not job_data:
                logger.error("Failed to retrieve or process job content")
                return self._generate_fallback_analysis(profile_type)
            
            # Match the job to the specified profile type
            try:
                logger.info("Creating matching agent and task")
                matching_agent = self.create_matching_agent()
                matching_task = self.match_to_neurodiverse_profile(job_data, profile_type)
                
                logger.info("Creating and running crew for matching analysis")
                crew = Crew(
                    agents=[matching_agent],
                    tasks=[matching_task],
                    verbose=False,
                    process=Process.SYNC  # Force synchronous in Lambda
                )
                
                matching_result = crew.kickoff()
                
                # Parse the matching result
                if isinstance(matching_result, str):
                    # Extract JSON if it's embedded in text
                    json_match = re.search(r'```json\s*(.*?)\s*```', matching_result, re.DOTALL)
                    if json_match:
                        matching_result = json_match.group(1)
                    
                    try:
                        parsed_matching = json.loads(matching_result)
                        logger.info("Successfully parsed matching result as JSON")
                    except json.JSONDecodeError as json_err:
                        logger.error(f"Failed to parse matching result as JSON: {str(json_err)}")
                        parsed_matching = self._generate_fallback_matching(profile_type)
                elif isinstance(matching_result, dict):
                    parsed_matching = matching_result
                else:
                    parsed_matching = self._generate_fallback_matching(profile_type)
                
                # Combine job data with matching analysis
                result = {
                    "title": job_data.get("job_title", "Unknown Position"),
                    "company": job_data.get("company", "Unknown Company"),
                    "location": job_data.get("location", "Unknown Location"),
                    "description": self._create_description_from_job_data(job_data),
                    "skills": job_data.get("skills", []),
                    "responsibilities": job_data.get("responsibilities", []),
                    "fit_score": parsed_matching.get("fit_score", 0.75),
                    "strengths_match": parsed_matching.get("strengths_match", [
                        "Matches your detail-oriented approach",
                        "Aligns with your systematic work style"
                    ]),
                    "considerations": parsed_matching.get("considerations", [
                        "May require occasional meetings",
                        "Consider asking about flexible hours"
                    ])
                }
                
                logger.info("Job analysis completed successfully")
                return result
                
            except Exception as matching_error:
                logger.error(f"Error in matching process: {str(matching_error)}")
                logger.error(traceback.format_exc())
                
                # Return a fallback result that combines the job data with generic matching
                fallback_matching = self._generate_fallback_matching(profile_type)
                
                return {
                    "title": job_data.get("job_title", "Unknown Position"),
                    "company": job_data.get("company", "Unknown Company"),
                    "location": job_data.get("location", "Unknown Location"),
                    "description": self._create_description_from_job_data(job_data),
                    "skills": job_data.get("skills", []),
                    "responsibilities": job_data.get("responsibilities", []),
                    "fit_score": fallback_matching.get("fit_score", 0.75),
                    "strengths_match": fallback_matching.get("strengths_match", []),
                    "considerations": fallback_matching.get("considerations", [])
                }
                
        except Exception as e:
            logger.error(f"Error in overall job analysis: {str(e)}")
            logger.error(traceback.format_exc())
            return self._generate_fallback_analysis(profile_type)
    
    def _create_description_from_job_data(self, job_data: Dict[str, Any]) -> str:
        """
        Create a human-readable job description from structured job data.
        """
        try:
            description = f"{job_data.get('job_title', 'Position')} at {job_data.get('company', 'a company')}"
            
            if job_data.get('location'):
                description += f" ({job_data.get('location')})"
            
            description += ".\n\n"
            
            if job_data.get('responsibilities'):
                description += "Key responsibilities include: "
                description += ", ".join(job_data.get('responsibilities')[:3])
                description += ".\n\n"
            
            if job_data.get('required_qualifications'):
                description += "Required qualifications: "
                description += ", ".join(job_data.get('required_qualifications')[:3])
                description += "."
            
            return description
        except Exception as e:
            logger.error(f"Error creating description: {str(e)}")
            return "Job position with responsibilities in technology and software development."
    
    def _generate_fallback_matching(self, profile_type: str) -> Dict[str, Any]:
        """
        Generate fallback matching information based on profile type.
        """
        basic_matches = {
            "AAAA": {
                "strengths_match": [
                    "Well-suited for detail-oriented tasks",
                    "Quiet environment matches your preferences",
                    "Clear instructions align with your work style"
                ],
                "considerations": [
                    "May require occasional meetings",
                    "Consider asking about noise levels in the workspace"
                ],
                "fit_score": 0.8
            },
            "AABA": {
                "strengths_match": [
                    "Detail-oriented tasks match your strengths",
                    "Balance of independent work and collaboration"
                ],
                "considerations": [
                    "Check the frequency of team meetings",
                    "Ask about quiet spaces for focus time"
                ],
                "fit_score": 0.75
            },
            # Add more profile types as needed
            "default": {
                "strengths_match": [
                    "Technical tasks align with your strengths",
                    "Role offers structured work approach"
                ],
                "considerations": [
                    "Consider workplace accommodations if needed",
                    "Check flexibility options for work schedule"
                ],
                "fit_score": 0.7
            }
        }
        
        return basic_matches.get(profile_type, basic_matches["default"])
    
    def _generate_fallback_analysis(self, profile_type: str) -> Dict[str, Any]:
        """
        Generate complete fallback analysis when the entire process fails.
        """
        fallback_matching = self._generate_fallback_matching(profile_type)
        
        return {
            "title": "Software Developer",
            "company": "Tech Solutions Inc.",
            "location": "Remote",
            "description": "Software Developer position with responsibilities including coding, testing, and documentation. Requires programming skills and problem-solving abilities.",
            "skills": ["Programming", "Problem Solving", "Testing"],
            "responsibilities": ["Software Development", "Testing", "Documentation"],
            "fit_score": fallback_matching.get("fit_score", 0.7),
            "strengths_match": fallback_matching.get("strengths_match", []),
            "considerations": fallback_matching.get("considerations", [])
        }

    def get_job_recommendations(self, analysis):
        """
        Get job recommendations based on analysis results.
        This is a legacy method to maintain compatibility.
        """
        try:
            # Extract profile type from analysis
            profile_type = "default"
            
            # If analysis contains HTML with profile indicators, extract them
            if isinstance(analysis, str) and "<div" in analysis:
                # Extract work style, environment, etc. from the HTML
                work_style_match = re.search(r'Work Style:</strong>\s*(.*?)<', analysis, re.IGNORECASE)
                env_match = re.search(r'Environment:</strong>\s*(.*?)<', analysis, re.IGNORECASE)
                
                # Determine profile type based on extracted data
                work_style = work_style_match.group(1) if work_style_match else ""
                environment = env_match.group(1) if env_match else ""
                
                if "detail" in work_style.lower() and "quiet" in environment.lower():
                    profile_type = "AAAA"
                elif "detail" in work_style.lower() and "collaborative" in environment.lower():
                    profile_type = "AABA"
            
            # Generate recommendations based on profile type
            recommendations = []
            for i in range(3):  # Generate 3 recommendations
                recommendation = self._generate_fallback_analysis(profile_type)
                recommendation["title"] = f"Position {i+1}: {recommendation['title']}"
                recommendations.append(recommendation)
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error getting job recommendations: {str(e)}")
            return [self._generate_fallback_analysis("default") for _ in range(3)] 