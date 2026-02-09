# audnexus-provider

Go-based provider service for Audnexus data, migrating from Python to Go.

## Project Structure

```
cmd/server/          # Entry point for the server
internal/
  api/              # API client implementations
  cache/            # Caching utilities
  config/           # Configuration management
  handlers/         # HTTP handlers
  models/           # Data models
  services/         # Business logic
  utils/            # Utility functions
```

## Setup

```bash
# Install dependencies
go mod tidy

# Build the server
go build -o bin/server ./cmd/server

# Run the server
./bin/server
```

## Development

- Ensure Go 1.21+ is installed
- Use `go mod tidy` to manage dependencies
- Run `go fmt ./...` before committing