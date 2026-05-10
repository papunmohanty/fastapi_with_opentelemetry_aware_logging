install-all: install otel-init

install:
	@echo "\e[1;34mInstalling package dependencies...\e[0m"
	uv sync
	.venv/bin/python -m ensurepip --upgrade        # OTEL required `pip` to be installed
	.venv/bin/python -m pip install --upgrade pip  # Upgrading the `pip` just in case

otel-init:
	@echo "\e[1;34mInitializing the OTEL configuration for the app...\e[0m"
	.venv/bin/opentelemetry-bootstrap -a install

# Below command only intrument(show OTEL logs) in the local terminal
# run-app: # Run the FastAPI Service with OTEL extractor enabled, which instrument logs
# 	export OTEL_PYTHON_LOGGING_AUTO_INSTRUMENTATION_ENABLED=true
# 	.venv/bin/opentelemetry-instrument \
# 	--traces_exporter console \
# 	--metrics_exporter console \
# 	--logs_exporter console \
# 	--service_name dice-server \
# 	.venv/bin/uvicorn main:app

# Below command, instruments OTEL logs in the Jaeger UI instead of the local terminal
run-app: # Run the FastAPI Service with OTEL exporter enabled, which instrument logs
	.venv/bin/opentelemetry-instrument --service_name roll.dice5 .venv/bin/uvicorn main:app

docker-run:  # Run Jaeger using docker command
	docker run --rm \
	-e COLLECTOR_ZIPKIN_HOST_PORT=:9411 \
	-p 16686:16686 \
	-p 4317:4317 \
	-p 4318:4318 \
	-p 9411:9411 \
	jaegertracing/all-in-one:latest
