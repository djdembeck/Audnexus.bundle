# audnexus-provider

Go-based HTTP metadata provider for Plex, delivering audiobook metadata from the Audnexus API.

## Overview

This is a complete rewrite of the Audnexus.bundle Plex plugin as an HTTP-based metadata provider. It provides rich author and audiobook metadata to Plex Media Server via a RESTful API.

## Features

- **HTTP-based provider**: Runs as a standalone service (not embedded in Plex)
- **All 10 Audible regions supported**: au, ca, de, es, fr, in, it, jp, us, uk
- **ASIN quick matching**: Direct lookups by ASIN for perfect matches
- **Fuzzy search with Levenshtein scoring**: Intelligent title/author matching
- **In-memory caching**: Reduces API calls with configurable TTL
- **Cross-platform**: Pre-built binaries for Linux, macOS, Windows (amd64 + arm64)
- **Graceful shutdown**: Handles SIGTERM/SIGINT properly
- **Structured logging**: Configurable log levels (DEBUG, INFO, WARN, ERROR)

## Installation

### Download Binary (Recommended)

Download the latest release for your platform from the [Releases](https://github.com/djdembeck/audnexus-provider/releases) page.

### Build from Source

```bash
# Clone the repository
git clone https://github.com/djdembeck/Audnexus.bundle.git
cd Audnexus.bundle

# Build for current platform
make build

# Or build for all platforms
make build-all
```

## Configuration

Configuration is done via environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `REGION` | us | Audible region (au, ca, de, es, fr, in, it, jp, us, uk) |
| `KEEP_EXISTING_GENRES` | false | Keep existing genres instead of replacing |
| `STORE_AUTHOR_AS_MOOD` | true | Store author name as mood tag |
| `SORT_AUTHOR_BY_LAST_NAME` | true | Sort author names by last name |
| `SIMPLIFY_TITLE` | false | Simplify book titles (remove subtitles) |
| `LOG_LEVEL` | INFO | Log level (DEBUG, INFO, WARN, ERROR) |
| `PORT` | 8080 | HTTP server port |
| `CACHE_TTL` | 604800 | Cache TTL in seconds (default: 1 week) |
| `AUDNEXUS_TIMEOUT` | 90 | API timeout in seconds |

Create a `.env` file or set variables directly:

```bash
export REGION=us
export LOG_LEVEL=INFO
export PORT=8080
./audnexus-provider
```

## Usage with Plex

1. **Start the provider**:
   ```bash
   ./audnexus-provider
   ```

2. **In Plex**, go to Settings > Agents > Music > Audnexus

3. **Configure the agent URL**: `http://localhost:8080/audnexus`

4. **Create or refresh** your audiobook library

## API Endpoints

### Provider Discovery
```
GET /audnexus
```
Returns provider capabilities.

### Search
```
POST /audnexus/library/metadata/matches
Content-Type: application/json

{
  "type": "artist",  // or "album"
  "title": "Stephen King",
  "year": "2020"
}
```

### Metadata Retrieval
```
GET /audnexus/library/metadata/author_B01234ABCD
GET /audnexus/library/metadata/album_B01234ABCD
```

## Development

```bash
# Run tests
go test ./...

# Run with hot reload
make run

# Clean build artifacts
make clean
```

## License

GPL v3.0 - See LICENSE file