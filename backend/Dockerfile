FROM python:3.14-slim
WORKDIR /app
COPY requirements.txt ./
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --upgrade pip && /opt/venv/bin/pip install -r requirements.txt
COPY . /app
ENV PATH="/opt/venv/bin:$PATH"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
