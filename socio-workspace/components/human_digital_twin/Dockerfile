
FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY ops/requirements.txt /app/ops/requirements.txt
RUN pip install -U pip && pip install -r /app/ops/requirements.txt
COPY api /app/api
COPY trpc /app/trpc
ENV API_KEY=test
EXPOSE 8080
CMD ["uvicorn","api.main:app","--host","0.0.0.0","--port","8080"]
