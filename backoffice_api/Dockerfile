FROM python:3.12-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8080

# Run the application using shell format to support environment variables
CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8080}
