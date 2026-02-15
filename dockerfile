FROM python:3.11-slim

WORKDIR /app

# ติดตั้ง git + dependencies
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

# copy entrypoint สำหรับ pull repo + run
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]

