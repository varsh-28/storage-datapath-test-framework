FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src ./src
COPY tests ./tests
COPY pytest.ini .
RUN mkdir -p /app/reports

CMD ["python", "-m", "pytest", "tests", "--ignore=tests/integration"]
