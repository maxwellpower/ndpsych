FROM python:3.9-slim

# Metadata
LABEL org.opencontainers.image.source="https://github.com/maxwellpower/ndpsych"

RUN pip install --no-cache-dir requests

WORKDIR /app
COPY main.py /app/main.py

CMD ["python", "main.py"]
