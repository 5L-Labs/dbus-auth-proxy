# Use a lightweight Python base image
FROM python:3.12-slim

# Set working directory
WORKDIR /app

# Copy the client script into the container
COPY client.py .

# Command to run the client
CMD ["python3", "client.py"]
