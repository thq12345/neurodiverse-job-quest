"""
Frontend Proxy Lambda Function

This Lambda function serves as a proxy for frontend requests, handling CORS
and potentially routing to other Lambda functions based on the request path.
"""

import json
import logging
import boto3
import os
from typing import Dict, Any, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from mangum import Mangum
import requests

# Configure logging
logger = logging.getLogger("frontend-proxy")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
logger.addHandler(handler)

# Initialize FastAPI app
app = FastAPI(title="Neurodiverse Job Quest Frontend Proxy",
              description="Proxy for frontend requests to Lambda functions",
              version="1.0.0")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Get API Gateway base URL from environment variable or use a default for local testing
API_GATEWAY_URL = os.environ.get("API_GATEWAY_URL", "https://your-api-gateway-id.execute-api.your-region.amazonaws.com/prod")

@app.get("/health")
async def health_check():
    """
    Simple health check endpoint
    """
    return {"status": "healthy", "service": "frontend-proxy"}

@app.get("/api/{path:path}")
async def proxy_get_request(path: str, request: Request):
    """
    Proxy GET requests to the appropriate Lambda function via API Gateway
    """
    logger.info(f"Proxying GET request to /{path}")
    
    # Forward query parameters
    params = dict(request.query_params)
    
    # Construct the full URL
    url = f"{API_GATEWAY_URL}/{path}"
    
    try:
        # Forward the request to API Gateway
        response = requests.get(url, params=params)
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Error proxying GET request: {e}")
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

@app.post("/api/{path:path}")
async def proxy_post_request(path: str, request: Request):
    """
    Proxy POST requests to the appropriate Lambda function via API Gateway
    """
    logger.info(f"Proxying POST request to /{path}")
    
    # Get the request body
    body = await request.json()
    
    # Construct the full URL
    url = f"{API_GATEWAY_URL}/{path}"
    
    try:
        # Forward the request to API Gateway
        response = requests.post(url, json=body)
        return json.loads(response.text)
    except Exception as e:
        logger.error(f"Error proxying POST request: {e}")
        raise HTTPException(status_code=500, detail=f"Proxy error: {str(e)}")

# Direct Lambda handler function for simple requests
def direct_handler(event, context):
    """
    Direct Lambda handler for API Gateway integration
    This can be used for simple requests without FastAPI
    """
    logger.info(f"Direct handler received event: {json.dumps(event)}")
    
    try:
        # Parse the request path
        path = event.get('pathParameters', {}).get('proxy', '')
        
        # Get HTTP method
        http_method = event.get('httpMethod', 'GET')
        
        # Construct the full URL
        url = f"{API_GATEWAY_URL}/{path}"
        
        # Forward the request based on the HTTP method
        if http_method == 'GET':
            # Get query parameters
            query_params = event.get('queryStringParameters', {}) or {}
            response = requests.get(url, params=query_params)
        elif http_method == 'POST':
            # Get body
            body = json.loads(event.get('body', '{}'))
            response = requests.post(url, json=body)
        else:
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f"Unsupported HTTP method: {http_method}"})
            }
        
        # Return the response
        return {
            'statusCode': response.status_code,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True
            },
            'body': response.text
        }
    except Exception as e:
        logger.error(f"Error in direct handler: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*',
                'Access-Control-Allow-Credentials': True
            },
            'body': json.dumps({'error': str(e)})
        }

# Create Lambda handler
handler = Mangum(app)

# For local development
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002) 