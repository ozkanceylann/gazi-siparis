FROM python:3.12-slim
WORKDIR /srv
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app
COPY web ./web
RUN useradd --uid 10001 --create-home gazi
USER gazi
CMD ["uvicorn","app.main:app","--host","0.0.0.0","--port","8000","--no-proxy-headers"]
