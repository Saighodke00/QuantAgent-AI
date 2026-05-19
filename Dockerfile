FROM python:3.10-slim

WORKDIR /app

# Install system build dependencies (required for some quant/ml libraries)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy all application code
COPY . .

# Expose port 7860 (Hugging Face Spaces default port)
EXPOSE 7860

# Run Streamlit on port 7860
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=7860", "--server.address=0.0.0.0"]
