# Base Python image
FROM python:3.11-slim-bullseye
WORKDIR /app

# Create a non-root user
RUN groupadd -r appgroup && useradd --no-log-init -r -g appgroup -d /app -s /sbin/nologin appuser

# Copy main agent scripts, TUI app (though not run directly in this test), and the orchestrator
COPY ./scribe_agent.py /app/scribe_agent.py           # Ensure this file is named scribe_agent.py on host
COPY ./ex_work_agentv2.py /app/ex_work_agentv2.py
COPY ./nai_tui_app.py /app/nai_tui_app.py           # For completeness of NAI environment
COPY ./quick_run.py /app/quick_run.py               # Our new orchestrator
COPY ./.scribe.toml /app/.scribe.toml               # Scribe config for the orchestrator

COPY ./requirements.txt /app/requirements.txt
COPY ./nai_tui_styles.css /app/nai_tui_styles.css # If it exists

RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    procps \
    patch \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r /app/requirements.txt \
    && chmod +x /app/scribe_agent.py /app/ex_work_agentv2.py /app/nai_tui_app.py /app/quick_run.py \
    && chown -R appuser:appgroup /app

ENV PYTHONUNBUFFERED=1
VOLUME /workspace 
# Other volumes like /app/user_exwork_templates, /app/logs are fine if defined but not critical for this specific test CMD

USER appuser

# Default CMD will be overridden by docker-compose for this test
CMD ["python", "/app/quick_run.py"]
