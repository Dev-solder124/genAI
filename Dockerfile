# Start with a standard Python 3.11 image
FROM python:3.11-slim

# Set the working directory inside the container
WORKDIR /app

# Copy and install the requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy your application code
COPY . .

# Command to run the production server
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "main:app"]