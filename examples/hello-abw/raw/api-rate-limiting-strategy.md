# API Rate Limiting Strategy

The service uses token-bucket rate limiting at the API gateway.

- burst: 100 requests
- steady rate: 20 requests per second
- authenticated users receive higher burst limits
