FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install dependencies (add pandas and rdflib if needed)
RUN pip install --no-cache-dir fastapi uvicorn sparqlwrapper pandas rdflib

# Copy entire project so src/ is available
COPY . .

EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]