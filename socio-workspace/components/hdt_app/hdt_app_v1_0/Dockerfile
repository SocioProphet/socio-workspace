FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY ops/requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt
COPY api /app/api
COPY ucum /app/ucum
COPY examples /app/examples
COPY linkage/api/static /app/linkage_static
EXPOSE 8080
CMD ["uvicorn","api.main:app","--host","0.0.0.0","--port","8080"]
