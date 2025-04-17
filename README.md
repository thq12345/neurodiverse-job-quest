# Neurodiverse Job Quest Application

This application helps neurodiverse individuals find suitable job opportunities based on their preferences and work styles.

## New Feature: CrewAI-based Response Evaluation

The application now uses CrewAI to intelligently evaluate free-form user responses before deciding whether to use the OpenAI API for generating additional insights. This optimization:

1. Saves API costs by only using OpenAI when the user input is actually useful
2. Provides better feedback to users when their input isn't helpful
3. Creates a more intelligent evaluation pipeline using specialized AI agents

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Set Up Environment Variables

Create a `.env` file with the following keys:

```
OPENAI_API_KEY=your_openai_api_key
LANGTRACE_API_KEY=your_langtrace_api_key
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_REGION=us-east-1
FLASK_SECRET_KEY=your_secret_key
```

### 3. Run the Application

```bash
python app.py
```

The server will start on port 5000, and you can access the application at http://localhost:5000.

## How the CrewAI Evaluation Works

1. When a user submits the questionnaire, their free-form response (question 5) is captured
2. The `ResponseEvaluator` class uses CrewAI to:
   - Create an agent specialized in evaluating text for job-related insights
   - Determine if the response contains useful information about work preferences
   - Return a structured evaluation with reasoning
3. If the response is deemed useful and an OpenAI API key is available, the application generates personalized insights
4. If not, it provides appropriate feedback explaining why the response wasn't processed

## Files

- `app.py`: Main Flask application
- `response_evaluator.py`: CrewAI implementation for evaluating user responses
- `requirements.txt`: Project dependencies
- `analysis_templates.py`: Pre-computed analysis templates

## Notes

- The application will fall back to pre-computed responses if CrewAI evaluation fails
- The CrewAI agent is configured to be precise in determining if text contains job-relevant information
- For optimal performance, ensure you have proper API credentials for both CrewAI and OpenAI
