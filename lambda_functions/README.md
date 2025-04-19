# Neurodiverse Job Quest - Serverless API

This directory contains the serverless Lambda functions for the Neurodiverse Job Quest application, now fully migrated to use DynamoDB with on-demand capacity.

## Architecture

- **AWS Lambda** - Serverless compute for API endpoints
- **API Gateway** - API management and routing
- **DynamoDB** - NoSQL database for assessment data (on-demand capacity)
- **S3** - Static website hosting for frontend
- **CloudFormation/SAM** - Infrastructure as code for deployment

## Project Structure

- `questionnaire_api.py` - FastAPI app for questionnaire endpoints
- `results_api.py` - FastAPI app for results analysis endpoints
- `models.py` - Pydantic models for API validation
- `utils.py` - Utility functions and AWS client initialization
- `app_init.py` - Lambda function to initialize resources
- `template.yaml` - SAM/CloudFormation template for deployment
- All original helper modules are included (`job_analyzer.py`, `response_evaluator.py`, etc.)

## Key Features

- **DynamoDB On-Demand Mode** - No need to provision capacity upfront, pay-per-request pricing
- **FastAPI** - Modern, high-performance web framework
- **Pydantic Models** - Type validation for request/response data
- **Serverless Architecture** - Scalable, cost-effective solution
- **CloudFormation** - Infrastructure as code for repeatable deployments

## Prerequisites

- AWS CLI installed and configured
- AWS SAM CLI installed
- Python 3.9+

## Local Development

1. Create a virtual environment and install dependencies:
   ```
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

2. Run the FastAPI applications locally:
   ```
   # Run questionnaire API
   uvicorn questionnaire_api:app --reload --port 8000
   
   # Run results API
   uvicorn results_api:app --reload --port 8001
   ```

3. Access the API documentation:
   - Questionnaire API: http://localhost:8000/docs
   - Results API: http://localhost:8001/docs

## Deployment

1. Build the SAM application:
   ```
   sam build
   ```

2. Deploy the application:
   ```
   sam deploy --guided
   ```
   
   During the guided deployment, you'll need to provide:
   - Stack name (e.g., `neurodiverse-job-quest`)
   - AWS Region
   - Parameter values for API keys and credentials
   - Confirmation for IAM role creation

3. Note the API Gateway endpoint URL from the deployment outputs.

## DynamoDB Table Structure

The application uses a single DynamoDB table with the following structure:

- **Table Name**: Assessments
- **Primary Key**: id (UUID string)
- **Attributes**:
  - id - UUID string
  - q1_answer - String (questionnaire answer)
  - q2_answer - String (questionnaire answer)
  - q3_answer - String (questionnaire answer)
  - q4_answer - String (questionnaire answer)
  - q5_answer - String (free-text questionnaire answer)
  - analysis - JSON string (analysis results)
  - created_at - ISO 8601 date string

## S3 Frontend Deployment

1. Build your frontend assets

2. Create an S3 bucket for hosting:
   ```
   aws s3 mb s3://your-bucket-name
   ```

3. Configure the bucket for static website hosting:
   ```
   aws s3 website s3://your-bucket-name --index-document index.html --error-document index.html
   ```

4. Upload your frontend assets:
   ```
   aws s3 sync ./frontend/build s3://your-bucket-name
   ```

5. Set bucket policy to allow public read access (for hosting purposes).

## Frontend Configuration

Update your frontend code to use the API Gateway endpoint URL for all API calls. This URL will be provided in the CloudFormation stack outputs after deployment. 