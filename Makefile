SHELL := /usr/bin/env bash

.PHONY: install scan compose-up compose-logs

install:
	pip install -r requirements.txt && pip install -e .

scan:
	python -m scamgeo.cli.app run -i ./demo/sample_channels.txt -o ./data/out --zip ./data/out/evidence.zip

compose-up:
	cd packaging && docker compose up -d

compose-logs:
	cd packaging && docker compose logs -f app
