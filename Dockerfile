FROM python:3.11-slim

# Install system dependencies for duckdb/pandas if needed
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python libraries
RUN pip install --no-cache-dir \
    duckdb \
    requests \
    pandas \
    tqdm

# Copy the rest of the code
COPY . .

CMD ["python", "src/main.py"]