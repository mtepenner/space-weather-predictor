# ---- Build Stage ----
FROM golang:1.21-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .
RUN CGO_ENABLED=0 GOOS=linux go build -ldflags="-w -s" -o /bin/poller ./cmd/poller

# ---- Runtime Stage ----
FROM alpine:latest

RUN apk --no-cache add ca-certificates tzdata

WORKDIR /app

COPY --from=builder /bin/poller /app/poller

EXPOSE 8080

ENTRYPOINT ["/app/poller"]
