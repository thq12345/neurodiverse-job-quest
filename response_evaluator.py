from crewai import Agent, Crew, Task
import json
import logging
from typing import Dict, Any, Optional
import re

app_logger = logging.getLogger('app')

class ResponseEvaluator:
    """
    A class that uses CrewAI to evaluate free-form user responses
    and determine if they contain useful information for job recommendations.
    """
    
    def __init__(self, openai_client=None, debug_func=None):
        """
        Initialize the response evaluator.
        
        Args:
            openai_client: OpenAI client for API calls
            debug_func: Function for debug logging
        """
        self.openai_client = openai_client
        self.debug = debug_func or (lambda *args, **kwargs: None)
        
    def create_evaluation_agent(self) -> Agent:
        """Create the agent responsible for evaluating user responses"""
        return Agent(
            role="Response Evaluator",
            goal="Accurately determine if a user's free-form response contains useful information about their work preferences",
            backstory="""You are an expert at analyzing text to determine if it contains
            meaningful information about a person's work preferences, strengths, or job-related needs.
            You can identify when text is too vague, off-topic, or doesn't add value to job recommendations.""",
            verbose=True,
            allow_delegation=False
        )
    
    def create_evaluation_task(self, agent: Agent, free_response: str) -> Task:
        """Create the task for evaluating the user response"""
        return Task(
            description=f"""
            Analyze this user response and determine if it contains useful information
            about their work preferences that could inform job recommendations:
            
            "{free_response}"
            
            Return a JSON object with:
            1. "is_useful" (boolean): Whether the response contains useful information
            2. "reasoning" (string): Brief explanation for your decision
            """,
            agent=agent,
            expected_output="""
            {
                "is_useful": true/false,
                "reasoning": "explanation"
            }
            """
        )
        
    def evaluate_response(self, free_response: str) -> Dict[str, Any]:
        """
        Evaluate if the free response contains useful information.
        
        Args:
            free_response: The user's free-form text response
            
        Returns:
            Dictionary with evaluation results
        """
        self.debug("Creating CrewAI agent to evaluate user response")
        
        # Quick pre-check for obviously empty or meaningless responses
        if not free_response or not free_response.strip():
            return {
                "is_useful": False,
                "reasoning": "Response is empty"
            }
            
        # Check for very short responses that are unlikely to be useful
        if len(free_response.strip()) < 10:
            return {
                "is_useful": False,
                "reasoning": "Response is too short to provide meaningful information"
            }
        
        try:
            # Create crew for evaluation
            evaluator = self.create_evaluation_agent()
            evaluation_task = self.create_evaluation_task(evaluator, free_response)
            crew = Crew(
                agents=[evaluator],
                tasks=[evaluation_task],
                verbose=True
            )
            
            # Run the evaluation
            self.debug("Running CrewAI evaluation")
            result = crew.kickoff()
            
            # Debug the result object and its type
            self.debug(f"CrewAI result type: {type(result)}")
            self.debug(f"CrewAI result dir: {dir(result)}")
            
            # Handle CrewOutput object directly
            if hasattr(result, 'raw_output'):
                self.debug(f"CrewAI raw output: {result.raw_output}")
                try:
                    # Try to parse JSON directly from the output
                    json_match = re.search(r'\{.*\}', result.raw_output, re.DOTALL)
                    if json_match:
                        evaluation = json.loads(json_match.group(0))
                        self.debug(f"CrewAI evaluation result: {evaluation}")
                        return evaluation
                except (AttributeError, json.JSONDecodeError) as e:
                    app_logger.error(f"Failed to parse CrewAI result as JSON: {str(e)}")
            
            # If we have a string representation of the result
            result_str = str(result)
            json_match = re.search(r'\{.*\}', result_str, re.DOTALL)
            if json_match:
                try:
                    evaluation = json.loads(json_match.group(0))
                    self.debug(f"CrewAI evaluation result: {evaluation}")
                    return evaluation
                except json.JSONDecodeError:
                    app_logger.error("Failed to parse CrewAI result as JSON")
            
            # Check if we can access the actual result directly
            # This is the most reliable method if the CrewAI API supports it
            if hasattr(result, 'result') and isinstance(result.result, dict):
                if 'is_useful' in result.result:
                    self.debug(f"Using direct result object: {result.result}")
                    return result.result
                
            # Default response if we can't parse the result
            self.debug("Couldn't properly extract result from CrewAI output")
            return {
                "is_useful": False,  # Default to NOT using OpenAI to save costs
                "reasoning": "Unable to properly evaluate the response, defaulting to not useful"
            }
            
        except Exception as e:
            app_logger.error(f"Error in CrewAI evaluation: {str(e)}")
            self.debug(f"CrewAI evaluation error: {str(e)}")
            
            # Default response if CrewAI fails
            return {
                "is_useful": False,  # Default to NOT using OpenAI to save costs
                "reasoning": "Error in evaluation process, defaulting to not useful"
            }
    
    def get_additional_insights(self, free_response: str, normalized_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process the free response and return additional insights.
        
        Args:
            free_response: The user's free-form text response
            normalized_analysis: The current analysis data
            
        Returns:
            Updated normalized_analysis with additional insights
        """
        if not free_response or not free_response.strip():
            # If no free response, add default additional insights
            normalized_analysis["additional_insights"] = {
                "description": "No additional information provided",
                "explanation": "You did not provide any additional context about your work preferences."
            }
            return normalized_analysis
        
        # Evaluate if the response is useful
        evaluation = self.evaluate_response(free_response)
        self.debug(f"Evaluation result: {evaluation}")
        
        if evaluation["is_useful"] and self.openai_client:
            try:
                self.debug("Response evaluated as useful, calling OpenAI API")
                
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
                
                response = self.openai_client.chat.completions.create(
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
                normalized_analysis["additional_insights"] = custom_insights
                
            except Exception as e:
                # If there's an error, just use a generic additional insight
                app_logger.error(f"Error customizing additional insights: {str(e)}")
                normalized_analysis["additional_insights"] = {
                    "description": "Additional information provided, but we couldn't customize the additional insights",
                    "explanation": "You shared specific preferences that provide further context for your work environment needs."
                }
        else:
            # Response wasn't useful or we don't have an OpenAI client
            if not evaluation["is_useful"]:
                self.debug("Response evaluated as NOT useful, skipping OpenAI API call")
                normalized_analysis["additional_insights"] = {
                    "description": "Additional information not relevant for job matching",
                    "explanation": evaluation["reasoning"]
                }
            else:
                self.debug("Response was useful but OpenAI API key not found")
                normalized_analysis["additional_insights"] = {
                    "description": "Additional information provided, but couldn't be processed",
                    "explanation": "We couldn't process your additional information at this time due to technical limitations."
                }
            
        return normalized_analysis 