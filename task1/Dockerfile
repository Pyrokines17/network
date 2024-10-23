FROM golang:1.20 AS builder
WORKDIR /app
COPY . .
RUN go mod tidy
RUN go build -o main .

FROM ubuntu:latest
LABEL authors="pyro"
WORKDIR /root/
COPY --from=builder /app/main .
CMD ["./main"]