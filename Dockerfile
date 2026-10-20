FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHON_DOTENV_DISABLED=1 \
    PORT=8080

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY manage.py ./
COPY gfood/ ./gfood/
COPY accounts/ ./accounts/
COPY cards/ ./cards/
COPY orders/ ./orders/
COPY products/ ./products/
COPY reports/ ./reports/
COPY templates/ ./templates/
COPY static/ ./static/

# Build sem credenciais reais nem acesso ao banco de dados.
RUN DEBUG=True DJANGO_SETTINGS_MODULE=gfood.settings python manage.py collectstatic --noinput
RUN useradd --create-home --uid 10001 appuser
USER appuser

ENV DJANGO_SETTINGS_MODULE=gfood.production
EXPOSE 8080
CMD ["sh", "-c", "exec gunicorn gfood.wsgi:application --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 8 --timeout 120 --access-logfile - --error-logfile -"]
