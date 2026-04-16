FROM python:3.10-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --default-timeout=1000 --no-cache-dir -r requirements.txt

COPY . .

# Run migrations and start server
CMD python manage.py migrate --noinput && python manage.py runserver 0.0.0.0:8000
