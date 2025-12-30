SHELL := /bin/bash
PORT ?= 5175
build:
	cd cmd/dev-api && go build -o ../../bin/dev-api
run: build
	PORT=$(PORT) DEV_TOKEN=dev ./bin/dev-api
