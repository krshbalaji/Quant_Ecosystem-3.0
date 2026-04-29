FROM python:3.11-slim

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

ENV EXECUTION_MODE=D
ENV PAPER_MODE=true
ENV LIVE_BROKER_DISABLED=true
ENV DISPATCH_ENABLED=true
ENV GLOBAL_KILL_SWITCH=true

CMD ["python", "cloudrun_app.py"]