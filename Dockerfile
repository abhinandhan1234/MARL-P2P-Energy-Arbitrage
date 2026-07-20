FROM python:3.13-slim

WORKDIR /app

# Install system dependencies (if any) and Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire repository into the container
COPY . .

# Expose the default port for HF Spaces (7860)
EXPOSE 7860

# Start the FastAPI app
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "7860"]
