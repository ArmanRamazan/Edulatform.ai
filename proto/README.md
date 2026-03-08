# Proto Contracts

Source of truth for all inter-service API calls and async events in KnowledgeOS.

## Contract-first approach

Every inter-service interaction must have a proto contract defined here before any implementation begins. No call crosses a service boundary without a corresponding `.proto` file.

## Directory structure

```
proto/
├── services/v1/     — synchronous RPC contracts (currently HTTP/REST shaped)
│   ├── ai.proto     — AIService: GetDailyMission, UnifiedSearch, CompleteMission
│   ├── rag.proto    — RAGService: Search, IngestDocument
│   └── learning.proto — LearningService: GetMastery, GetUserStats
└── events/v1/       — async event contracts published to NATS JetStream
    ├── mastery.proto  — MasteryUpdated (platform.mastery.updated)
    ├── mission.proto  — MissionCompleted (platform.mission.completed)
    └── badge.proto    — BadgeEarned (platform.badge.earned)
```

## How to read these contracts

### Service contracts (`services/v1/`)

Each file documents which service owns the RPC and which services are allowed to call it. The comments in each file identify the callers.

| Proto file | Owning service | Known callers |
|------------|---------------|---------------|
| `ai.proto` | ai (port 8006) | learning |
| `rag.proto` | rag (port 8008) | ai |
| `learning.proto` | learning (port 8007) | notification |

### Event contracts (`events/v1/`)

All events flow through NATS JetStream on the `PLATFORM_EVENTS` stream. Each message type documents its subject in a top-level comment.

| Proto file | NATS subject | Publisher | Subscribers |
|------------|-------------|-----------|-------------|
| `mastery.proto` | `platform.mastery.updated` | learning | notification |
| `mission.proto` | `platform.mission.completed` | learning | notification |
| `badge.proto` | `platform.badge.earned` | learning | notification |

### Backward compatibility rules

- New fields may be added to any message at any time.
- Existing fields must never be removed or renumbered.
- Field semantics must not change without a new message version.

## Code generation

Code generation from these protos is deferred. The contracts serve as documentation and design validation until gRPC transport replaces the current HTTP calls. At that point, `protoc` with the appropriate language plugins will be added to the build pipeline.

Current transport: services communicate via HTTP REST. These contracts document the logical API surface that HTTP endpoints implement.
