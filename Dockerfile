FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app/src \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# зависимости отдельным слоем для кэширования
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# код приложения
COPY alembic.ini ./
COPY migrations ./migrations
COPY src ./src

# по умолчанию запускаем API; consumer/relay переопределяют command в compose
CMD ["uvicorn", "worker.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
