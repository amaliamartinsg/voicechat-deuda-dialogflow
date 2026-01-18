# Usar Python 3.12 como base
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app:/app

COPY ./requirements.txt .

# Instalar uv y dependencias
RUN pip install --no-cache-dir uv && \
	pip install --no-cache-dir -r requirements.txt

COPY main.py ./
COPY data/ ./data/
COPY src/ ./src/
COPY routers/ ./routers/
COPY config/ ./config/
COPY helpers/ ./helpers/

EXPOSE 8008

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8008"]