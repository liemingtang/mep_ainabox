FROM python:3.11-slim

WORKDIR /app

COPY file_watcher/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY file_watcher/ .
COPY volume_manager.py .
COPY ../processors/ /app/processors/

EXPOSE 8009

CMD ["python", "main.py"] 