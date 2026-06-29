FROM python:3.12-slim

WORKDIR /app

# Зависимости отдельно от кода — для кэша слоёв
COPY pyproject.toml ./
RUN pip install --no-cache-dir .

COPY . .
RUN pip install --no-cache-dir -e .

ENV PYTHONPATH=/app/src
CMD ["python", "-m", "aifashion.main"]
