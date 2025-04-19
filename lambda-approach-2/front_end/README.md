# Neurodiverse Job Quest - Frontend

This directory contains the frontend assets for the Neurodiverse Job Quest application, designed to be hosted in an AWS S3 bucket.

## Structure

- `index.html` - Main application entry point
- `static/css/styles.css` - Stylesheet for the application
- `static/js/api.js` - API service for communicating with the Lambda functions
- `static/js/app.js` - Main application logic
- `static/images/` - Directory for image assets

## Features

- Single-page application with client-side routing
- Responsive design using Bootstrap
- Questionnaire interface
- Results display with profile information and job recommendations
- Shareable results via URL parameters

## Local Testing

1. Edit the API Gateway URL in `static/js/api.js` to point to your deployed API Gateway
2. Open `index.html` in a web browser (or use a local server)

## Deployment to S3

1. Create an S3 bucket for static website hosting:

```bash
aws s3 mb s3://your-bucket-name
```

2. Configure the bucket for static website hosting:

```bash
aws s3 website s3://your-bucket-name --index-document index.html --error-document index.html
```

3. Upload the frontend assets:

```bash
aws s3 sync . s3://your-bucket-name
```

4. Set bucket policy to allow public read access:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "PublicReadGetObject",
            "Effect": "Allow",
            "Principal": "*",
            "Action": "s3:GetObject",
            "Resource": "arn:aws:s3:::your-bucket-name/*"
        }
    ]
}
```

5. Access your website at:
   `http://your-bucket-name.s3-website-<region>.amazonaws.com`

## API Integration

The frontend communicates with the following API endpoints:

- `GET /questionnaire` - Fetches the questionnaire questions
- `POST /submit_questionnaire` - Submits questionnaire responses
- `GET /results/{assessment_id}` - Retrieves analysis results for an assessment
- `GET /health` - Health check endpoint

Before deploying to production, replace the API Gateway URL in `static/js/api.js` with your actual API Gateway URL.

## Customization

- To change the appearance, modify `static/css/styles.css`
- To add additional pages or features, modify `index.html` and `static/js/app.js`
- To change API endpoints or add new ones, modify `static/js/api.js`

## Notes for Production

- Consider using a CloudFront distribution in front of your S3 bucket for improved performance and HTTPS
- Set appropriate CORS headers in your API Gateway configuration
- Consider adding authentication if needed
- For improved SEO, consider using server-side rendering or a static site generator 