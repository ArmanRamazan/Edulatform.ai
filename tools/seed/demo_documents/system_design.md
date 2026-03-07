# System Design Fundamentals for Distributed Systems

## Introduction

System design is the process of defining the architecture, components, and data flows of a system to meet specified requirements. At scale, the difference between good and bad design is not just performance — it is the difference between a system that degrades gracefully and one that fails catastrophically. This document covers the foundational concepts that every engineer working on distributed systems must understand.

## Microservices Architecture

Microservices decompose a monolithic application into independently deployable services, each owning its domain and data. Each service is responsible for a bounded context: a specific area of business functionality with clear boundaries.

The key benefits of microservices include independent deployability (one service can be deployed without coordinating with others), independent scalability (the payment service can scale independently of the notification service), and technology heterogeneity (each service can use the language and framework best suited to its task).

The costs are real: distributed systems are harder to debug, have higher operational overhead, and introduce network latency and partial failure modes that do not exist in monoliths. Migrate from monolith to microservices only when the complexity of coordination within the monolith exceeds the complexity of operating multiple services.

Define service boundaries along domain lines, not technical layers. A service owns its data model and database. Services never share databases — communication happens through APIs and events, never through shared tables.

## API Gateway

The API gateway is the single entry point for all client requests. It handles cross-cutting concerns: authentication, rate limiting, request routing, SSL termination, and response caching.

In a microservices architecture, having clients call each service directly creates tight coupling between clients and the internal topology. The API gateway decouples this: clients communicate with one endpoint, the gateway routes requests to the appropriate service.

Common API gateway responsibilities:
- **Authentication**: Verify JWT tokens, extract user identity, forward it to downstream services via request headers
- **Rate limiting**: Protect services from traffic spikes and abuse
- **Request routing**: Map public paths to internal service endpoints
- **Load balancing**: Distribute requests across service instances
- **Circuit breaking**: Stop forwarding requests to unhealthy services
- **Response aggregation**: Combine responses from multiple services into one (Backend for Frontend pattern)

Implement the gateway in a high-performance language (Rust, Go, Java) since every request passes through it. A gateway written in a slow language or with a slow implementation creates a bottleneck that affects the entire system.

## Caching Strategies

Caching reduces load on databases and downstream services by storing the result of expensive computations near the consumer.

**Cache-aside (lazy loading)**: The application checks the cache first. On a miss, it fetches from the database and populates the cache. This is the most common strategy and works well for read-heavy workloads where some cache misses are acceptable.

```python
async def get_user(user_id: str) -> User:
    cached = await redis.get(f"user:{user_id}")
    if cached:
        return User.parse_raw(cached)
    user = await db.fetch_user(user_id)
    await redis.setex(f"user:{user_id}", 300, user.json())  # TTL: 5 minutes
    return user
```

**Write-through**: Write to the cache and database simultaneously. Cache is always consistent with the database. The cost is higher write latency and cache space for data that may not be read.

**Write-behind (write-back)**: Write to cache immediately, asynchronously flush to database. Lower write latency, but risk of data loss if the cache node fails before the flush.

**Cache eviction policies**: LRU (least recently used) evicts the item not accessed for the longest time. LFU (least frequently used) evicts the item accessed least often. TTL-based eviction removes items after a fixed time, ensuring eventual consistency.

Cache invalidation is one of the hardest problems in computer science. Design your data access patterns to minimize the need for manual invalidation. Use short TTLs for mutable data and long TTLs (or no expiry) for immutable data.

## Load Balancing

Load balancing distributes incoming requests across a pool of service instances. It is essential for horizontal scaling and fault tolerance.

**Round-robin**: Requests are distributed sequentially across all instances. Simple and effective when instances are homogeneous and requests have similar cost.

**Least connections**: Route to the instance with the fewest active connections. Better than round-robin when request durations vary significantly.

**IP hash**: Hash the client IP to consistently route the same client to the same instance. Useful for session-based applications that lack distributed session storage.

**Weighted**: Assign weights to instances based on capacity. Route proportionally more traffic to more powerful instances during gradual rollouts.

Layer 4 load balancers (TCP/UDP) route based on IP address and port. They are extremely fast and suitable for high-throughput scenarios. Layer 7 load balancers (HTTP) can route based on URL path, headers, and cookies, enabling more sophisticated routing strategies like path-based routing to different backend services.

Use health checks to automatically remove unhealthy instances from rotation. A health check pings a `/health` endpoint and removes the instance if it fails N consecutive checks. Return the instance to rotation after M successful checks.

## Database Sharding

Sharding horizontally partitions data across multiple database instances. Each shard holds a subset of the data. Together, all shards hold the complete dataset.

**Range-based sharding**: Partition by a range of values (user IDs 1–1M on shard 1, 1M–2M on shard 2). Simple to implement and supports range queries efficiently. Prone to hotspots if data is not uniformly distributed.

**Hash-based sharding**: Hash the shard key to determine which shard holds the data. Distributes data uniformly but makes range queries require hitting all shards.

**Directory-based sharding**: A lookup table maps keys to shards. Flexible — you can re-shard without changing the application. The lookup table is a single point of failure and a performance bottleneck.

Choosing the shard key is the most important decision in sharding design. A good shard key distributes data and load uniformly, supports your most common query patterns, and rarely needs to change.

Avoid cross-shard joins and transactions. If your application frequently needs to join data from multiple shards, your sharding strategy is wrong. Denormalize data or reconsider your domain boundaries.

## Event-Driven Architecture

In event-driven systems, services communicate asynchronously by publishing and consuming events. A producer publishes an event describing something that happened. Consumers react independently.

Events decouple producers from consumers. The notification service can consume `order.created` events without the order service knowing the notification service exists.

Use a durable message broker (NATS JetStream, Kafka, RabbitMQ) to ensure events survive broker restarts and are delivered reliably. Consumers track their offset/position in the event stream, so they can replay events after a crash.

Design event schemas for evolution. Add fields, never remove them. Use semantic versioning for major breaking changes. Consumers should ignore fields they do not understand.

Idempotency is critical in event-driven systems. A consumer must produce the same result whether it processes an event once or ten times. Use unique event IDs and record processed events in a deduplication table.

## Circuit Breaker Pattern

The circuit breaker prevents cascading failures by stopping requests to a downstream service that is known to be unhealthy.

States:
- **Closed** (normal): Requests flow through. Failures are counted.
- **Open** (failing): Requests are rejected immediately without reaching the downstream service. A timer determines how long the circuit stays open.
- **Half-open** (testing): One request is allowed through. If it succeeds, the circuit closes. If it fails, the circuit opens again.

```python
class CircuitBreaker:
    def __init__(self, threshold: int = 5, timeout: float = 60.0):
        self.failure_count = 0
        self.threshold = threshold
        self.state = "closed"
        self.opened_at: float | None = None
        self.timeout = timeout

    async def call(self, coro):
        if self.state == "open":
            if time.time() - self.opened_at > self.timeout:
                self.state = "half-open"
            else:
                raise ServiceUnavailableError("Circuit is open")
        try:
            result = await coro
            self._on_success()
            return result
        except Exception:
            self._on_failure()
            raise
```

## Rate Limiting

Rate limiting protects services from being overwhelmed by too many requests from a single client. It enforces fair use and prevents abuse.

**Token bucket**: A bucket holds tokens up to a maximum capacity. Each request consumes one token. Tokens are added at a fixed rate. A request is rejected if no tokens are available. Allows bursting up to the bucket capacity.

**Sliding window**: Count requests in a rolling time window. Smoother than fixed window — avoids the thundering herd at window boundaries.

Implement rate limiting at the API gateway for external clients. Implement it at the service level for internal service-to-service calls. Use Redis for distributed rate limiting state so the limit applies across all gateway instances.

Return `429 Too Many Requests` with a `Retry-After` header telling the client when it can try again.

## Monitoring and Observability

Observability is the ability to understand the internal state of a system from its external outputs. The three pillars are metrics, logs, and traces.

**Metrics**: Numeric measurements over time. Track request rate, error rate, and latency (the RED method). Also track saturation (CPU, memory, queue depth) and utilization. Use Prometheus for collection and Grafana for visualization.

**Logs**: Structured events describing what happened. Use JSON format so logs are machine-parseable. Include a correlation ID (request ID, trace ID) in every log line to enable tracing a request through multiple services.

**Distributed tracing**: Trace a single request as it flows through multiple services. Each service adds a span to the trace. Tools like Jaeger and Zipkin visualize the trace. Tracing reveals latency hotspots that are invisible in aggregate metrics.

Set up alerting on SLOs (service level objectives), not arbitrary thresholds. An SLO might be: "99.9% of requests complete in under 200ms." Alert when the error budget (the allowed failure rate) is being consumed faster than expected.
