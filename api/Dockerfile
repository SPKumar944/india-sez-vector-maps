FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY api/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Copy API and data directory
COPY api /app/api
COPY data /app/data

ENV DB_PATH=/app/data/560034_koramangala/koramangala_560034_cloud_kitchen.sqlite
ENV DATA_DIR=/app/data/560034_koramangala

EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
