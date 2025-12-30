# syntax=docker/dockerfile:1.7
FROM golang:1.22-alpine AS build
WORKDIR /src
COPY . .
RUN --mount=type=cache,target=/root/.cache/go-build <<EOF
cd cmd/dev-api && go build -trimpath -o /out/dev-api
EOF

FROM alpine:3.20
RUN adduser -D -u 10003 app
USER app
WORKDIR /home/app
COPY --from=build /out/dev-api /usr/local/bin/dev-api
ENV PORT=5175 DEV_TOKEN=dev
EXPOSE 5175
ENTRYPOINT ["/usr/local/bin/dev-api"]
