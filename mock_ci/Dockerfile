FROM python:3.12-slim
WORKDIR /app
# git: a /verify végpont "git apply"-jal alkalmazza a patch-et; pytest + pyyaml: a célrepó tesztjeihez
RUN apt-get update && apt-get install -y --no-install-recommends git && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "fastapi>=0.115" "uvicorn>=0.30" "pyyaml==6.0.3" "pytest==9.2.0"
COPY mock_ci /app/mock_ci
COPY target_repo /app/target_repo
ENV BASE_REPO=/app/target_repo \
    SCENARIO_DIRS="/app/scenarios;/app/hidden" \
    DATA_DIR=/data
EXPOSE 9000
CMD ["uvicorn", "mock_ci.app:app", "--host", "0.0.0.0", "--port", "9000"]
