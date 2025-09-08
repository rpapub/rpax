# ADR-022: Minimal rpax Access API Implementation

**Status:** Approved  
**Date:** 2024-01-01  
**Updated:** 2025-09-08  

## Context

The rpax tool requires a lightweight HTTP API layer to enable external tool integration and programmatic access to parsed UiPath project data. Based on the 4-layer architecture (ADR-002), this Access API layer should provide read-only access to artifacts stored in the rpax lake without exposing parsing complexity.

Current requirements include basic service discovery, health monitoring, and operational metadata exposure for PowerShell integration and external tooling.

## Decision

We will implement a **minimal** rpax Access API focused on essential endpoints and robust operational characteristics, following a bootstrap-first approach that prioritizes reliability over feature completeness.

## Bootstrap & Configuration

### Configuration Schema
Integration with existing `.rpax.json` configuration system (ADR-004):

```json
{
  "api": {
    "enabled": false,        // default false in dev, true when packaged
    "bind": "127.0.0.1",     // never public by default - localhost only
    "port": 8623,            // RPAX port (R-P-A-X numeric); auto-increment on clash
    "readOnly": true         // always true - no mutations allowed
  }
}
```

### Port Management Strategy
- **Default port**: `8623` (R-P-A-X mnemonic mapping)
- **Collision handling**: Auto-increment within ephemeral range (49152-65535)
- **Failure mode**: Fail fast with clear error if no available ports found
- **Logging**: Log final bound address for operational visibility

### Lake Root Validation
- Validate all configured lake roots from `.rpax.json` during startup
- Verify lake structure integrity (projects.json, schema files)
- Fail fast with actionable error messages for invalid/missing lakes
- Log lake discovery summary and project count

## Service Discovery & Operational Integration

### Discoverability File
Write service metadata to `%LOCALAPPDATA%\rpax\api-info.json` for external tool integration:

```json
{
  "url": "http://127.0.0.1:8623",
  "pid": 12345,
  "startedAt": "2025-09-06T10:30:00Z",
  "rpaxVersion": "0.1.0",
  "lakes": ["/path/to/.rpax-lake"],
  "projectCount": 3,
  "configPath": "/path/to/.rpax.json"
}
```

**File Management**:
- Atomic write with temp file + rename for consistency
- Cleanup on graceful shutdown
- Overwrites existing files from previous instances

### Startup Output Format
Single-line summary optimized for PowerShell parsing and logging:

```
rpax API started at http://127.0.0.1:8623 (3 projects, 1 lake)
```

**Format specification**:
- Always single line for easy parsing
- Includes essential operational info
- Machine-readable structure: `rpax API started at {url} ({projectCount} projects, {lakeCount} lake{s})`

## Minimal Endpoint Specification

### Health Check Endpoint
```
GET /health
→ 200 {
  "status": "ok",
  "timestamp": "2025-09-06T10:30:00Z"
}
```

**Characteristics**:
- Always returns 200 OK if service is responsive
- No authentication or authorization required
- Minimal response payload for performance
- Suitable for load balancer health checks and monitoring

### Service Status Endpoint
```
GET /status
→ 200 {
  "rpaxVersion": "0.1.0",
  "uptime": "2h15m30s", 
  "startedAt": "2025-09-06T08:15:00Z",
  "mountedLakes": [
    {
      "path": "/path/to/.rpax-lake",
      "projectCount": 3,
      "lastScanAt": "2025-09-06T08:15:00Z"
    }
  ],
  "totalProjectCount": 3,
  "latestActivityAt": "2025-09-06T08:15:00Z",
  "memoryUsage": {
    "heapUsed": "45.2MB",
    "heapTotal": "67.1MB"
  }
}
```

**Operational Metadata**:
- **Runtime information**: Version, uptime, memory usage
- **Lake status**: Path, project count, last activity timestamp
- **Activity tracking**: Latest parse/scan across all projects
- **Resource monitoring**: Memory usage for operational visibility

## Protocol Standards & Error Handling

### HTTP Response Standards
- **Content-Type**: Always `application/json; charset=utf-8`
- **Compression**: Support `gzip` when client requests with `Accept-Encoding: gzip`
- **Pretty printing**: Enable in development mode for debugging
- **CORS**: Not supported in minimal implementation (localhost-only)

### Standardized Error Model
All error responses follow consistent JSON structure:

```json
{
  "error": "bad_request|not_found|internal|service_unavailable",
  "detail": "Human-readable error description", 
  "traceId": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-09-06T10:30:00Z",
  "requestPath": "/invalid-endpoint"
}
```

**Error Categories**:
- `bad_request` (400): Invalid request parameters or format
- `not_found` (404): Unknown endpoint or resource
- `internal` (500): Unexpected server error
- `service_unavailable` (503): Lake validation failed, service degraded

### HTTP Status Code Mapping
- **200 OK**: Successful request with data
- **400 Bad Request**: Invalid client request
- **404 Not Found**: Unknown endpoint or resource
- **405 Method Not Allowed**: Unsupported HTTP method
- **500 Internal Server Error**: Unexpected server failure
- **503 Service Unavailable**: Lake unavailable, startup failed

## Security & Network Considerations

### Network Security
- **Localhost binding**: Default bind to `127.0.0.1` only - never expose publicly
- **No authentication**: Minimal implementation relies on localhost-only access
- **Read-only operations**: No data modification endpoints
- **Process isolation**: Service runs in same security context as CLI

### Future Security Extensions
Architectural support for future security enhancements:
- API key authentication for remote access
- Role-based access control for multi-user scenarios  
- TLS support for encrypted communication
- Request rate limiting and abuse prevention

## Implementation Architecture

### Technology Stack
- **HTTP Server**: Standard library implementation for minimal dependencies
- **JSON Processing**: Built-in JSON marshaling/unmarshaling
- **Configuration**: Leverage existing `.rpax.json` system from ADR-004
- **Logging**: Integrate with existing rpax logging infrastructure

### Operational Characteristics
- **Request Model**: Synchronous request/response (no async complexity)
- **Data Access**: Direct file system reads from lake artifacts
- **Memory Management**: No in-memory caching initially
- **Graceful Degradation**: Continue serving if individual lakes become unavailable

### Integration Points
- **Lake Data Model**: Read artifacts defined in lake-data-model.md
- **Configuration System**: Extend existing `.rpax.json` schema (ADR-004)
- **CLI Integration**: Share configuration and lake validation logic
- **Future API Expansion**: Architectural hooks for additional endpoints

## Deferred Features & Extension Points

### Phase 2 Capabilities
- **Project Listing**: `GET /projects` with metadata
- **Artifact Access**: `GET /projects/{slug}/artifacts/{type}`
- **Workflow Details**: `GET /projects/{slug}/workflows/{id}`
- **Search & Filtering**: Query parameters for artifact filtering

### Extension Architecture
- **Plugin System**: Extensible endpoint registration
- **Lake-Specific Routing**: `/lakes/{slug}/...` URL structure
- **Streaming Support**: Large artifact streaming with range requests
- **WebSocket Notifications**: Real-time lake change notifications

### Integration Readiness
- **OpenAPI Specification**: Schema generation for expanded API
- **Client SDK Generation**: Auto-generated client libraries
- **Metrics & Telemetry**: Prometheus-compatible metrics export
- **Observability**: Structured logging and distributed tracing

## Consequences & Trade-offs

### Positive Outcomes
- **Rapid Implementation**: Minimal surface area enables fast development cycles
- **Operational Excellence**: Focus on reliability, monitoring, and service discovery
- **Security by Default**: Localhost-only binding prevents accidental exposure
- **Foundation for Growth**: Clean architecture supports incremental expansion
- **Zero Dependencies**: Standard library implementation reduces security surface

### Limitations Accepted
- **Limited Data Access**: No actual artifact serving initially
- **Synchronous Only**: May require revision for high-throughput scenarios
- **No Caching**: Direct file system access may impact performance
- **No Authentication**: Unsuitable for multi-user or remote access scenarios

### Operational Benefits
- **Fast Startup**: Minimal initialization overhead
- **Predictable Behavior**: Simple request/response model
- **Easy Debugging**: Clear error messages and operational metadata
- **PowerShell Integration**: Machine-readable startup output
- **Service Discovery**: Standardized integration for external tools

## Compliance & Standards Alignment

This ADR aligns with established rpax architecture decisions:

- **ADR-002**: 4-layer architecture compliance (Access API layer)
- **ADR-004**: Configuration system integration and JSON Schema validation
- **ADR-017**: Lake nomenclature and artifact access patterns
- **Security Standards**: Localhost-only default, read-only access model
- **HTTP Standards**: RESTful conventions, standard status codes
- **JSON Standards**: Consistent response format, UTF-8 encoding

## Implementation Timeline

### Phase 1: Foundation (Immediate)
1. HTTP server setup with configuration integration
2. Health and status endpoints implementation
3. Service discovery file generation
4. Error handling and logging integration

### Phase 2: Validation & Testing
1. Lake validation and startup behavior
2. Integration testing with existing CLI
3. PowerShell integration validation
4. Documentation and usage examples

### Phase 3: Operational Readiness
1. Memory usage monitoring and optimization
2. Graceful shutdown and cleanup procedures
3. Production packaging and deployment
4. Performance testing and tuning