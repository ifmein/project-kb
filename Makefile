NAME = project-kb
TAG = $(shell git rev-parse --short HEAD)

fmt:
	uvx ruff check --fix .

pull:
	git pull origin main

install:
	uv tool install .

install-skill:
	mkdir -p ~/.agents/skills/project-kb
	cp reference/project-kb/SKILL.md ~/.agents/skills/project-kb/SKILL.md

reinstall:
	uv tool install . --reinstall

docker-clean:
	docker builder prune -f

docker-build: docker-clean
	docker build -t $(NAME):$(TAG) .
	docker tag $(NAME):$(TAG) $(NAME):latest

.PHONY: fmt pull install reinstall docker-build docker-clean
