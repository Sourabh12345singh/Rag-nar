# Use official Python base image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of the project
COPY . .

# Expose the port Railway will use
EXPOSE 8080

# Set environment variable for Python
ENV PYTHONUNBUFFERED=1

# Command to run your app (FastAPI example)
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
