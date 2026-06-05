FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY src/ .
RUN mkdir -p /app/data && mkdir -p /app/published
EXPOSE 3744
CMD ["python", "app.py"]
