FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    ca-certificates \
    curl \
    git \
 && update-ca-certificates

# กำหนดตำแหน่งของ CA Certificates ให้ Python สามารถตรวจสอบ SSL ได้ถูกต้อง
ENV SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

CMD ["/entrypoint.sh"]
