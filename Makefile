NAME = project-kb
TAG = $(shell git rev-parse --short HEAD)

fmt:
	uvx ruff check --fix .

pull:
	git pull origin main

install:
	uv tool install .

reinstall:
	uv tool install . --reinstall

docker-clean:
	docker builder prune -f

docker-build: docker-clean
	docker build -t $(NAME):$(TAG) .
	docker tag $(NAME):$(TAG) $(NAME):latest

.PHONY: fmt pull install reinstall docker-build docker-clean
