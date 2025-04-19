FROM python:3.11-slim

WORKDIR /app

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy all application files
COPY . .

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Expose port for FastAPI
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "questionnaire_api:app", "--host", "0.0.0.0", "--port", "8000"] 