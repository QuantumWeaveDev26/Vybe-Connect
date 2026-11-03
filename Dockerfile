FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TW_DATA_DIR=/var/lib/teamwave/active
WORKDIR /app
COPY *.py ./
COPY static ./static
RUN mkdir -p /var/lib/teamwave && chown -R 10001:10001 /app /var/lib/teamwave
USER 10001:10001
EXPOSE 8788
HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 CMD ["python", "healthcheck.py"]
CMD ["python", "server.py", "--port", "8788"]
