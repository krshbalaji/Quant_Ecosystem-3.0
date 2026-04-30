FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir flask

ENV PORT=8080

CMD ["python", "cloudrun_app.py"]