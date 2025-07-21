FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

ENV FLASK_APP=app/api/app.py
ENV PYTHONUNBUFFERED=1

EXPOSE 5000

# On lance le script d'init puis les migrations Alembic, puis l'app Flask
CMD ["sh", "-c", "python init_superuser.py && flask db upgrade && python app/api/app.py"]

