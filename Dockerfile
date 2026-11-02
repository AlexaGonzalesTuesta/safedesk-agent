FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
ENV SAFEDESK_TRACE_DIR=/app/traces
EXPOSE 8000
CMD ["uvicorn", "safedesk.api:app", "--host", "0.0.0.0", "--port", "8000"]
