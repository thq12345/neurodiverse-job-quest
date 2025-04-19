# Neurodiverse Job Quest - Lambda Implementation

This implementation of the Neurodiverse Job Quest is designed to be deployed as an AWS Lambda function with API Gateway integration.

## Project Structure

- `app.py` - Main Lambda handler that processes API requests
- `job_analyzer.py` - Job analysis logic
- `response_evaluator.py` - Evaluates user responses
- `utils.py` - Utility functions
- `create_tables.py` - Script to create required DynamoDB tables
- `front_end/` - Static front-end files

## Database Setup

Before deploying the Lambda function, you need to create the required DynamoDB tables:

```bash
# Run the table creation script
python create_tables.py
```

This script will create the following tables if they don't already exist:
- `UserAssessments` - Stores user questionnaire responses and results
- `AnalysisTemplates` - Stores pre-computed analysis templates
- `JobBank` - Stores job information for recommendations

## Deployment Instructions

### 1. Deploy the Backend Lambda Function

1. Package the Lambda code:

```bash
# Install dependencies into a 'package' directory
pip install -r requirements.txt --target ./package

# Navigate to the package directory
cd package

# Zip the dependencies
zip -r ../lambda_function.zip .

# Return to the project root
cd ..

# Add the Python files to the zip
zip -g lambda_function.zip app.py job_analyzer.py response_evaluator.py utils.py
```

2. Create a Lambda function in the AWS Console:
   - Runtime: Python 3.9+
   - Handler: app.lambda_handler
   - Upload the lambda_function.zip file
   - Set the appropriate environment variables:
     - `OPENAI_API_KEY`: Your OpenAI API key
     - `AWS_ACCESS_KEY_ID`: Your AWS access key (if using cross-account access)
     - `AWS_SECRET_ACCESS_KEY`: Your AWS secret key (if using cross-account access)
     - `AWS_REGION`: Your AWS region (e.g., us-east-1)
     - `LANGTRACE_API_KEY`: Your Langtrace API key (if using)

3. Configure Lambda function settings:
   - Memory: 256 MB or higher (recommendation: 512 MB)
   - Timeout: 30 seconds
   - Configure appropriate IAM role with permissions for:
     - Amazon Bedrock
     - DynamoDB
     - S3 (if needed)
     - CloudWatch Logs

### 2. Set Up API Gateway

1. Create a new REST API in API Gateway
2. Create the following resources and methods:
   - `GET /questionnaire` - Get questionnaire questions
   - `POST /submit_questionnaire` - Submit answers
   - `GET /results/{assessment_id}` - Get results by ID
   - `GET /health` - Health check endpoint

3. For each method:
   - Integration type: Lambda Function
   - Lambda Function: Select your Lambda function
   - Enable Lambda Proxy integration

4. Configure CORS:
   - Enable CORS for all resources
   - Allow headers: Content-Type, X-Amz-Date, Authorization, X-Api-Key
   - Allow methods: GET, POST, OPTIONS
   - Allow origin: * (or your specific domain)

5. Deploy the API to a stage (e.g., "prod")
6. Note your API Gateway URL: `https://{api-id}.execute-api.{region}.amazonaws.com/{stage}`

### 3. Deploy the Front-end

Option 1: Host on S3 with Static Website Hosting:
1. Create an S3 bucket
2. Enable Static Website Hosting
3. Update `front_end/static/js/api.js` with your API Gateway URL:
   ```javascript
   this.apiBaseUrl = 'https://your-api-id.execute-api.your-region.amazonaws.com/prod';
   ```
4. Upload the contents of the `front_end` directory to the S3 bucket
5. Configure bucket policy to allow public read access

Option 2: Host on another web server:
1. Update `front_end/static/js/api.js` with your API Gateway URL
2. Deploy the contents of the `front_end` directory to your web server

## Local Development

For local development and testing:

1. Set API URL in browser console:
   ```javascript
   window.API_GATEWAY_URL = 'https://your-api-id.execute-api.your-region.amazonaws.com/prod';
   ```

2. Or run without an API using the mock data implementation:
   - Just open the `front_end/index.html` file in a browser
   - The application will automatically detect it's running locally and use mock data

## Data Structure

### Profile JSON Structure

The application uses a structured JSON format for profile data:

```json
{
  "work_style": {
    "description": "You thrive with a structured schedule",
    "explanation": "You prefer clear guidelines and consistent routines."
  },
  "environment": {
    "description": "You prefer quiet and private spaces",
    "explanation": "You work best in environments with minimal distractions."
  },
  "interaction_level": {
    "description": "You prefer minimal interactions",
    "explanation": "You tend to focus better when working independently."
  },
  "task_preference": {
    "description": "You prefer highly detailed and focused tasks",
    "explanation": "You excel at work requiring precision and careful attention."
  },
  "additional_insights": {
    "description": "No additional insights",
    "explanation": ""
  },
  "strengths": ["Attention to detail", "Pattern recognition", "Logical thinking"]
}
```

The front-end converts this JSON structure into HTML for display.

## Dependencies

```
openai>=1.0.0
boto3>=1.28.0
python-dotenv>=1.0.0
langtrace-python-sdk>=0.1.0
requests>=2.31.0
```

## Customizing Questions

You can customize the questionnaire questions by modifying the `questions` array in `app.py`. 