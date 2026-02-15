FROM python:3.11-slim

WORKDIR /app

# ติดตั้ง git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# copy entrypoint
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
