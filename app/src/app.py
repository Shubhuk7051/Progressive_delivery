import os
import random
import time
from flask import Flask, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

app = Flask(__name__)

VERSION = os.environ.get("APP_VERSION", "v1")
FAIL_MODE = os.environ.get("FAIL_MODE", "false").lower() == "true"
FAIL_RATE = float(os.environ.get("FAIL_RATE", "0.5"))  # 50% error rate when enabled

REQUEST_COUNT = Counter(
    "http_requests_total", "Total HTTP requests", ["method", "path", "status", "version"]
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds", "Request latency", ["path", "version"]
)

READY = True  # flips False briefly at startup to demo readiness gating if needed


@app.before_request
def start_timer():
    global _start
    _start = time.time()


@app.route("/")
def hello():
    status = 200
    if FAIL_MODE and random.random() < FAIL_RATE:
        status = 500

    latency = time.time() - _start
    REQUEST_LATENCY.labels(path="/", version=VERSION).observe(latency)
    REQUEST_COUNT.labels(method="GET", path="/", status=str(status), version=VERSION).inc()

    if status == 500:
        return Response("Internal Server Error (simulated)", status=500)
    return Response(f"Hello from Progressive Delivery {VERSION}", status=200)


@app.route("/healthz")
def healthz():
    REQUEST_COUNT.labels(method="GET", path="/healthz", status="200", version=VERSION).inc()
    return Response("ok", status=200)


@app.route("/readyz")
def readyz():
    status = 200 if READY else 503
    REQUEST_COUNT.labels(method="GET", path="/readyz", status=str(status), version=VERSION).inc()
    return Response("ready" if READY else "not ready", status=status)


@app.route("/metrics")
def metrics():
    return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)