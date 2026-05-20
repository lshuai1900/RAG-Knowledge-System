#!/bin/bash
set -e

echo "Waiting for Milvus..."
until curl -s -o /dev/null -w '%{http_code}' http://milvus:19530/healthz | grep -q 200; do
    sleep 2
done

echo "Starting application..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
