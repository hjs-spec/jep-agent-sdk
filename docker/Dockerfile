FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE ./
COPY jep/ ./jep/

RUN pip install --no-cache-dir -e ".[langchain,openai,mcp]"

EXPOSE 8080

CMD ["jep", "web", "--host", "0.0.0.0", "--port", "8080"]
