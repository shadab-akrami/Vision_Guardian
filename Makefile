# VisionGuardian Makefile
# Convenience commands for development and deployment

.PHONY: help install test run clean benchmark calibrate train-faces setup-service

help:
	@echo "VisionGuardian - Make Commands"
	@echo ""
	@echo "  make install        - Install all dependencies"
	@echo "  make test          - Run unit tests"
	@echo "  make run           - Run VisionGuardian"
	@echo "  make benchmark     - Run performance benchmarks"
	@echo "  make calibrate     - Run calibration tool"
	@echo "  make train-faces   - Train facial recognition"
	@echo "  make setup-service - Install systemd service"
	@echo "  make clean         - Clean cache and logs"
	@echo "  make models        - Download models"
	@echo ""

install:
	@echo "Running installation script..."
	chmod +x setup.sh
	./setup.sh

test:
	@echo "Running unit tests..."
	. venv/bin/activate && python3 -m pytest tests/ -v

run:
	@echo "Starting VisionGuardian..."
	. venv/bin/activate && python3 src/main.py

benchmark:
	@echo "Running performance benchmarks..."
	. venv/bin/activate && python3 scripts/benchmark.py

calibrate:
	@echo "Running calibration tool..."
	. venv/bin/activate && python3 scripts/calibrate.py

train-faces:
	@echo "Training facial recognition..."
	. venv/bin/activate && python3 scripts/train_faces.py

setup-service:
	@echo "Installing systemd service..."
	sudo cp visionguardian.service /etc/systemd/system/
	sudo systemctl daemon-reload
	@echo "Service installed. Enable with: sudo systemctl enable visionguardian"

models:
	@echo "Downloading models..."
	chmod +x scripts/download_models.sh
	./scripts/download_models.sh

clean:
	@echo "Cleaning cache and logs..."
	rm -rf cache/*
	rm -rf logs/*.log
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@echo "Clean complete"

status:
	@echo "VisionGuardian Status:"
	@systemctl status visionguardian --no-pager || echo "Service not running"

logs:
	@echo "Showing VisionGuardian logs (Ctrl+C to exit)..."
	@sudo journalctl -u visionguardian -f
