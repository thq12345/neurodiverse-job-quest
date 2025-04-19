# Use the Lambda base image for Python
FROM public.ecr.aws/lambda/python:3.11

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy the entire app (all code, templates, static, etc.)
COPY . .

# Set the Lambda function handler
# Format: <python file name>.<handler variable>
CMD ["app.handler"]
