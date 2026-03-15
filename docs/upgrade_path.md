# Upgrade Path

1. Containerize each service: backend, phoneme-detector, local-tts, redis.
2. Add versioned API endpoints for each service and health checks at `/api/health`.
3. Replace WebSocket hub with Redis Pub/Sub or Kafka for horizontal scale.
4. Offload phoneme detection to GPU-enabled service; provide gRPC endpoint.
5. Migrate voice stream broker to chunked object store (S3) + signed URLs for large-scale streaming.
6. Add observability: Prometheus metrics, Grafana dashboards, structured logs.
7. Introduce zero-downtime rolling updates with readiness/liveness probes.
