.PHONY: build test

build:
	cd go-service && go build -o ../bin/infrakit-go-service

install: build
	cp bin/infrakit-go-service /usr/local/bin/
	pip install -e .

test:
	pytest tests/