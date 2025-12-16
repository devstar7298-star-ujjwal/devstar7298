# Use an official Python runtime as a parent image
# Changed from 3.9 to 3.8 to address dependency compatibility issues
FROM python:3.8-slim-buster

# Set the working directory in the container
WORKDIR /app

# Copy the dependency files to the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of your application's code to the container, including the tools directory
COPY . .

# Gunicorn is a common choice for running Flask apps in production for Cloud Run
# It should listen on the port specified by the PORT environment variable.
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 main:app
