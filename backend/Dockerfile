# Dockerfile for NoorTime Backend

# 1. Use an official Python runtime as a parent image
FROM python:3.11-slim

# 2. Set environment variables
# Prevents Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED 1
# Set the Flask app entry point
ENV FLASK_APP="project:create_app('production')"
# Set the environment to production
ENV FLASK_ENV=production

# 3. Set the working directory in the container
WORKDIR /app

# 4. Install dependencies
# Copy the requirements file first to leverage Docker cache
COPY requirements.txt ./

# Install the dependencies
RUN pip install --no-cache-dir -r requirements.txt

# 5. Copy the rest of the application code into the container
COPY . .

# 6. Expose the port the app runs on
# The Gunicorn command below will run on port 5000
EXPOSE 5000

# 7. Define the command to run the application
# Use Gunicorn, a production-ready WSGI server.
# It will run the 'create_app' function from the 'project' package.
# We specify 4 workers and bind to 0.0.0.0:5000 so it's accessible from outside the container.
CMD ["gunicorn", "--workers=4", "--bind=0.0.0.0:5000", "project:create_app('production')"]
