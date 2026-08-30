# ==============================================================================
# PatientTriage.ai — Backend Dockerfile
# ==============================================================================
# python:3.11 (full image) already ships with gcc, build-essential, and
# libgomp1 so we skip the apt-get layer that needs internet at build time.
FROM python:3.11

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

# Ensure runtime data/report directories exist inside the image.
RUN mkdir -p data reports

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
