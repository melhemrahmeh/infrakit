FROM python:3.9-slim as python
FROM golang:1.18-alpine as go

# Build Go service
COPY go-service /go/src
WORKDIR /go/src
RUN go build -o /go/bin/infrakit-go-service

# Python environment
FROM python
COPY --from=go /go/bin/infrakit-go-service /usr/local/bin/
COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
ENTRYPOINT ["python", "-m", "cli.main"]