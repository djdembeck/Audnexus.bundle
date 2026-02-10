# Audnexus Metadata Provider Migration Plan (Go Implementation)

## TL;DR

> **Objective**: Complete rewrite of Audnexus.bundle from legacy Plex Framework 2 plugin to new HTTP-based Metadata Providers API in Go.
> 
> **Deliverables**:
> - Single binary `audnexus-provider` (no Docker required)
> - RESTful HTTP service with 3 endpoints
> - Full feature parity with legacy plugin
> - Cross-compiled binaries for all platforms
> - Environment-based configuration
> 
> **Estimated Effort**: Large (complete architectural migration)
> **Parallel Execution**: YES - 3 waves
> **Critical Path**: Project Setup → Core API → Integration → Deployment

---

## Context

### Original Request
Migrate Audnexus.bundle (audiobook metadata agent for Plex) from legacy Python plugin API to Plex's new Metadata Providers HTTP API.

### Interview Summary

**Key Decisions**:
- **Strategy**: Proactive migration before 2026 deprecation deadline
- **Scope**: Complete rewrite, all features on day one
- **Compatibility**: New system only (no backwards compatibility)
- **Language/Framework**: **Go (switched from Python based on deployment simplicity)**
- **Configuration**: Environment variables only
- **Caching**: In-memory with TTL (no Redis needed for single binary)
- **Deployment**: Single binary (no Docker required!)
- **Testing**: Manual testing
- **Project Structure**: Separate repository (`audnexus-provider`)
- **Port**: 8080

**Research Findings**:

**Current Plugin (Legacy Framework 2)**:
- Two agent classes: `AudiobookArtist` (Agent.Artist) and `AudiobookAlbum` (Agent.Album)
- 10 supported regions (US, UK, DE, FR, IT, ES, JP, AU, CA, IN)
- ASIN-based quick matching from filenames
- Levenshtein distance fuzzy search scoring
- Tag mappings: Authors→Moods, Narrators→Styles, Series→Moods
- 6 user preferences via DefaultPrefs.json
- External APIs: audnex.us (primary), Audible API (fallback)

**New System (Metadata Providers)**:
- HTTP-based external service (not embedded)
- Required endpoints: `GET /{provider}`, `POST /matches`, `GET /metadata/{id}`
- JSON MediaContainer responses
- No preference UI yet (Plex limitation)
- Music/audiobook support not officially documented but proceeding anyway

**Go-Specific Advantages**:
- Single static binary (no runtime dependencies)
- Built-in HTTP server (no framework needed)
- Excellent concurrency for parallel API calls
- Cross-compilation for all platforms
- Small binary size (~10-20MB)

---

## Work Objectives

### Core Objective
Create a production-ready Go binary that serves as an HTTP metadata provider, delivering identical audiobook metadata functionality to the legacy Plex plugin.

### Concrete Deliverables
1. **Go Binary** (`audnexus-provider`)
   - Single static executable
   - Built-in HTTP server (Gin or stdlib)
   - `/audnexus` - MediaProvider capabilities endpoint
   - `/audnexus/library/metadata/matches` - Search/matching endpoint
   - `/audnexus/library/metadata/{id}` - Metadata retrieval endpoint
2. **Build System**
   - Go modules (`go.mod`)
   - Makefile for cross-compilation
   - GitHub Actions for automated releases
   - Pre-built binaries for Linux, macOS, Windows (amd64 + arm64)
3. **Feature Parity**
   - Author/Artist metadata (bio, image, genres, similar)
   - Book/Album metadata (title, summary, rating, date, publisher)
   - All 10 region support
   - ASIN quick matching
   - Fuzzy search with Levenshtein scoring
   - Localized separators
   - Tag mappings (authors, narrators, series)
   - Pre-order filtering
4. **Configuration**
   - Environment variables for all 6 legacy preferences
   - Port configuration
   - Logging configuration

### Branching Strategy

**New Go Implementation Workflow**:
```
main (current: legacy Python)
│
├─> feature/go-migration        ← NEW: All Go development happens here
│   ├─> Task 1: Project Setup
│   ├─> Task 2: Dependencies
│   ├─> Task 3-9: Implementation
│   └─> PR to main when complete
│
└─> archive/legacy-python       ← NEW: Archive branch for old code
    (created from main before merging Go code)
```

**Workflow**:
1. Create `feature/go-migration` branch from current `main`
2. All 9 tasks commit to `feature/go-migration`
3. Before merging Go code to main:
   - Create `archive/legacy-python` branch from current main
   - Update README on `archive/legacy-python` with deprecation notice
4. Merge `feature/go-migration` to `main`
5. Tag v2.0.0 on main (Go implementation)
6. Tag v1.x.x-final on `archive/legacy-python` (final Python version)

**Why This Approach**:
- Preserves legacy Python code in archive branch
- Allows bug fixes to legacy version if needed
- Clean separation of implementations
- Users can pin to legacy branch if needed

### Archive Plan for Legacy Bundle

**Task 0: Archive Legacy Python Code (Before Go Migration)**

**What to do**:
- Create `archive/legacy-python` branch from current `main`
- Update `README.md` on archive branch:
  - Add deprecation notice
  - State: "This branch contains the legacy Python implementation for Plex Framework 2"
  - Link to new Go implementation
  - Note: "Plex is removing Framework 2 support in 2026"
- Add `ARCHIVE.md` documenting:
  - This is the final Python version
  - No further development planned
  - Known issues/limitations
- Tag as `v1.x.x-final` (last Python release)
- Set as protected branch

**Must NOT do**:
- Don't delete any Python code
- Don't modify functionality
- Don't merge archive branch to main

**Acceptance Criteria**:
- [ ] `archive/legacy-python` branch exists
- [ ] Branch has updated README with deprecation notice
- [ ] `ARCHIVE.md` exists with documentation
- [ ] Tag `v1.x.x-final` created
- [ ] Branch is protected

**Commit**: YES (direct to archive branch)
- Message: `docs: archive legacy Python implementation`
- Files: README.md, ARCHIVE.md

### Definition of Done
- [ ] Binary runs without external dependencies
- [ ] All endpoints return valid Plex MediaContainer JSON
- [ ] Manual testing confirms metadata retrieval works
- [ ] All 10 regions tested
- [ ] ASIN quick match tested
- [ ] Feature parity checklist completed
- [ ] Cross-compiled binaries available for download

### Must Have
- Go binary with built-in HTTP server
- Single binary deployment (no Docker/Python required)
- Environment variable configuration
- All 10 regions supported
- ASIN quick matching
- Levenshtein distance scoring
- Tag mappings (authors→moods, narrators→styles, series→moods)
- Proper error handling and logging
- Retry logic with exponential backoff
- Cross-compilation for all major platforms

### Must NOT Have (Guardrails)
- **NO** backwards compatibility with legacy plugin
- **NO** config file (env vars only per user decision)
- **NO** Docker required (single binary per Go decision)
- **NO** Redis (in-memory cache with TTL sufficient for single binary)
- **NO** embedded deployment (external service only)
- **NO** scanner hooking (not supported in new API)
- **NO** preference UI (Plex limitation, use env vars)
- **NO** automatic unit tests (manual testing per user)

---

## Verification Strategy

### Test Infrastructure
- **Testing**: Manual testing only (per user decision)
- **QA Method**: Agent-executed scenarios using curl and direct HTTP requests
- **Evidence**: Response captures saved to `.sisyphus/evidence/`

### Agent-Executed QA Scenarios

**Scenario 1: Binary Starts Successfully**
```
Tool: Bash
Preconditions: Binary built and available
Steps:
  1. ./audnexus-provider &
  2. sleep 2
  3. curl -s http://localhost:8080/health
  4. Assert: Response is {"status":"healthy"}
  5. kill %1
Expected Result: Binary starts and responds to health check
Evidence: .sisyphus/evidence/task-4-start.txt
```

**Scenario 2: Provider Discovery Endpoint**
```
Tool: Bash (curl)
Preconditions: Binary running on localhost:8080
Steps:
  1. curl -s http://localhost:8080/audnexus
  2. Assert: HTTP 200 status
  3. Assert: Response contains "MediaProvider"
  4. Assert: Response contains "identifier"
  5. Assert: Response contains "Feature" array with "match" and "metadata"
  6. Save response to .sisyphus/evidence/provider-discovery.json
Expected Result: Valid MediaProvider definition returned
```

**Scenario 3: Author Search (Fuzzy)**
```
Tool: Bash (curl)
Preconditions: Binary running
Steps:
  1. curl -s -X POST http://localhost:8080/audnexus/library/metadata/matches \
       -H "Content-Type: application/json" \
       -d '{"type":"artist","title":"Stephen King","lang":"en"}'
  2. Assert: HTTP 200 status
  3. Assert: Response contains "MediaContainer"
  4. Assert: Response contains at least 1 Metadata item
  5. Assert: Metadata contains "ratingKey", "guid", "title"
  6. Assert: "Stephen King" appears in results
  7. Save response to .sisyphus/evidence/author-search.json
Expected Result: Search returns matching authors with scores
```

**Scenario 4: Book Search with ASIN Quick Match**
```
Tool: Bash (curl)
Preconditions: Binary running
Steps:
  1. curl -s -X POST http://localhost:8080/audnexus/library/metadata/matches \
       -H "Content-Type: application/json" \
       -d '{"type":"album","title":"B01234ABCD","lang":"en"}'
  2. Assert: HTTP 200 status
  3. Assert: Response contains exactly 1 result
  4. Assert: Result score is 100 (perfect match)
  5. Assert: ratingKey contains "B01234ABCD"
  6. Save response to .sisyphus/evidence/asin-match.json
Expected Result: ASIN bypasses search and returns direct match
```

**Scenario 5: Author Metadata Retrieval**
```
Tool: Bash (curl)
Preconditions: Binary running, have valid author ratingKey
Steps:
  1. curl -s http://localhost:8080/audnexus/library/metadata/author_B01234ABCD
  2. Assert: HTTP 200 status
  3. Assert: Response contains full author metadata
  4. Assert: Contains "summary" (bio)
  5. Assert: Contains "thumb" (image URL)
  6. Assert: Contains "genres" array
  7. Save response to .sisyphus/evidence/author-metadata.json
Expected Result: Complete author metadata returned
```

**Scenario 6: Book Metadata Retrieval with Tags**
```
Tool: Bash (curl)
Preconditions: Binary running, have valid book ratingKey
Steps:
  1. curl -s http://localhost:8080/audnexus/library/metadata/album_B01234ABCD
  2. Assert: HTTP 200 status
  3. Assert: Response contains title, summary, rating, year
  4. Assert: Contains "moods" (authors)
  5. Assert: Contains "styles" (narrators)
  6. Assert: Contains "studio" (publisher)
  7. Save response to .sisyphus/evidence/book-metadata.json
Expected Result: Complete book metadata with all tags
```

**Scenario 7: Multi-Region Support (German)**
```
Tool: Bash (curl)
Preconditions: Binary running with REGION=de env var
Steps:
  1. REGION=de ./audnexus-provider &
  2. sleep 2
  3. curl -s -X POST http://localhost:8080/audnexus/library/metadata/matches \
       -H "Content-Type: application/json" \
       -H "Accept-Language: de" \
       -d '{"type":"album","title":"Harry Potter","lang":"de"}'
  4. Assert: HTTP 200 status
  5. Assert: Results are from German Audible catalog
  6. kill %1
Expected Result: German region returns German results
Evidence: .sisyphus/evidence/region-de.json
```

**Scenario 8: In-Memory Caching Works**
```
Tool: Bash (curl)
Preconditions: Binary running
Steps:
  1. time curl -s http://localhost:8080/audnexus/library/metadata/album_B01234ABCD
  2. Note first response time (should be >500ms for API call)
  3. time curl -s http://localhost:8080/audnexus/library/metadata/album_B01234ABCD
  4. Assert: Second response time <100ms (cached)
  5. Assert: Both responses are identical
Expected Result: Second request is faster due to in-memory cache
Evidence: .sisyphus/evidence/cache-test.txt
```

**Scenario 9: Cross-Platform Binary Works**
```
Tool: Bash
Preconditions: Built binaries for different platforms
Steps:
  1. ls -lh dist/
  2. Assert: audnexus-provider-linux-amd64 exists
  3. Assert: audnexus-provider-darwin-amd64 exists
  4. Assert: audnexus-provider-windows-amd64.exe exists
  5. Assert: audnexus-provider-linux-arm64 exists
  6. Assert: All binaries are executable (or .exe for Windows)
  7. file dist/audnexus-provider-linux-amd64
  8. Assert: Output shows "ELF 64-bit"
Expected Result: Binaries exist for all major platforms
Evidence: .sisyphus/evidence/binaries.txt
```

---

## Execution Strategy

### Git Branching Workflow

```
Pre-Migration (Current State):
main → [legacy Python code]

Step 1 - Archive:
git checkout -b archive/legacy-python
git push origin archive/legacy-python
# Update README, create ARCHIVE.md
git tag v1.x.x-final
git push origin v1.x.x-final

Step 2 - Create Feature Branch:
git checkout -b feature/go-migration main

Step 3 - All Go Development:
feature/go-migration → Tasks 1-9 commits

Step 4 - Merge to Main:
feature/go-migration → PR → main
# (archive/legacy-python preserved separately)
```

### Parallel Execution Waves

```
Pre-Work:
└── Task 0: Archive Legacy Python Code (on archive/legacy-python branch)

Wave 1 (Foundation - on feature/go-migration branch):
├── Task 1: Project Setup & Repository Structure
├── Task 2: Go Modules & Dependencies
└── Task 3: Configuration & Environment

Wave 2 (Core Implementation - on feature/go-migration branch):
├── Task 4: HTTP Server & Routing
├── Task 5: Audnexus API Client
└── Task 6: Search & Scoring Logic

Wave 3 (Integration & Polish - on feature/go-migration branch):
├── Task 7: Provider Endpoints
├── Task 8: Metadata Endpoints
└── Task 9: Build System & Documentation

Final Step (Merge to main):
└── PR from feature/go-migration → main
```

### Dependency Matrix

| Task | Depends On | Blocks | Can Parallelize With | Branch |
|------|------------|--------|---------------------|--------|
| 0 | None | 1-9 | None | archive/legacy-python |
| 1 | 0 | 2, 3 | None | feature/go-migration |
| 2 | 1 | 4, 5, 6 | 3 | feature/go-migration |
| 3 | 1 | 4 | 2 | feature/go-migration |
| 4 | 2, 3 | 7, 8 | 5, 6 | feature/go-migration |
| 5 | 2 | 6, 7, 8 | 4, 6 | feature/go-migration |
| 6 | 2, 5 | 7, 8 | 4, 5 | feature/go-migration |
| 7 | 4, 5, 6 | 9 | 8 | feature/go-migration |
| 8 | 4, 5, 6 | 9 | 7 | feature/go-migration |
| 9 | 7, 8 | None | None | feature/go-migration |

### Agent Dispatch Summary

| Wave | Tasks | Branch | Recommended Approach |
|------|-------|--------|---------------------|
| Pre | 0 | archive/legacy-python | Sequential git operations |
| 1 | 1, 2, 3 | feature/go-migration | Sequential (dependencies) |
| 2 | 4, 5, 6 | feature/go-migration | Task 4 can start when 3 done; 5 and 6 parallel |
| 3 | 7, 8, 9 | feature/go-migration | 7 and 8 parallel; 9 final integration |
| Post | Merge | main | PR review and merge |

---

## TODOs

> **NOTE**: Task 0 must be completed BEFORE merging any Go code to main. Tasks 1-9 are implemented on `feature/go-migration` branch.

- [x] 0. Archive Legacy Python Code (Pre-Migration)

  **What to do**:
  - Create `archive/legacy-python` branch from current `main`:
    ```bash
    git checkout main
    git pull origin main
    git checkout -b archive/legacy-python
    git push origin archive/legacy-python
    ```
  - Update `README.md` on archive branch with deprecation notice:
    - Add banner: "⚠️ ARCHIVED: Legacy Python Implementation"
    - State: "This branch contains the final Python implementation for Plex Framework 2"
    - Note Plex's 2026 deprecation timeline
    - Link to new Go implementation (when available)
    - Add "No further development planned" notice
  - Create `ARCHIVE.md` documenting:
    - Archive date
    - Reason for archival (Plex Framework 2 deprecation)
    - Final version tag: `v1.x.x-final`
    - Known issues/limitations at time of archival
    - Migration path to new Go implementation
  - Commit changes to `archive/legacy-python` branch
  - Create and push tag `v1.x.x-final` on archive branch
  - Set branch protection rules for `archive/legacy-python`:
    - Require pull request reviews
    - Restrict push access
  - Create `feature/go-migration` branch from `main` for all new development

  **Must NOT do**:
  - Don't delete any Python code
  - Don't modify functionality
  - Don't merge archive branch to main
  - Don't start Go work on main branch

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: ["git-master"]
  - Reason: Git branch management and documentation

  **Parallelization**:
  - **Can Run In Parallel**: NO (must complete before Go work)
  - **Blocks**: Tasks 1-9 (Go implementation)

  **References**:
  - Current README: `README.md` (reference for content to preserve)

  **Acceptance Criteria**:
  - [ ] `archive/legacy-python` branch exists on GitHub
  - [ ] Branch has updated README with deprecation notice
  - [ ] `ARCHIVE.md` created and committed
  - [ ] Tag `v1.x.x-final` created and pushed
  - [ ] Branch protection enabled
  - [ ] `feature/go-migration` branch created for Go work

  **Agent-Executed QA Scenario**:
  ```
  Scenario: Archive branch created correctly
    Tool: Bash (git)
    Steps:
      1. git fetch origin
      2. git branch -r | grep archive/legacy-python
      3. Assert: Shows origin/archive/legacy-python
      4. git tag -l | grep v1.*-final
      5. Assert: Shows v1.x.x-final tag
      6. git log archive/legacy-python --oneline -1
      7. Assert: Shows ARCHIVE.md commit
    Evidence: .sisyphus/evidence/task-0-archive.txt
  ```

  **Commit**: YES (direct to archive/legacy-python branch)
  - Message: `docs: archive legacy Python implementation`
  - Files: README.md, ARCHIVE.md

- [x] 1. Project Setup & Repository Structure (on feature/go-migration branch)

  **What to do**:
  - Create new repository `audnexus-provider`
  - Set up Go project structure:
    ```
    audnexus-provider/
    ├── cmd/
    │   └── server/
    │       └── main.go          # Entry point
    ├── internal/
    │   ├── config/
    │   │   └── config.go        # Environment configuration
    │   ├── api/
    │   │   ├── audnexus.go      # Audnexus API client
    │   │   └── audible.go       # Audible fallback client
    │   ├── handlers/
    │   │   ├── provider.go      # GET /audnexus
    │   │   ├── matches.go       # POST /matches
    │   │   └── metadata.go      # GET /metadata/{id}
    │   ├── models/
    │   │   ├── plex.go          # Plex MediaContainer models
    │   │   └── audnexus.go      # Audnexus API response models
    │   ├── services/
    │   │   ├── search.go        # Search orchestration
    │   │   ├── scoring.go       # Levenshtein distance scoring
    │   │   └── metadata.go      # Metadata compilation
    │   ├── utils/
    │   │   ├── cache.go         # In-memory cache with TTL
    │   │   ├── logger.go        # Structured logging
    │   │   └── helpers.go       # String utils, ASIN extraction
    │   └── cache/
    │       └── cache.go         # Thread-safe cache implementation
    ├── go.mod
    ├── go.sum
    ├── Makefile                 # Build automation
    ├── README.md
    ├── LICENSE
    └── .gitignore
    ```
  - Initialize Go module: `go mod init github.com/djdembeck/audnexus-provider`
  - Create `.gitignore` for Go projects

  **Must NOT do**:
  - Don't use Go workspaces (just modules)
  - Don't create vendor directory
  - Don't add code beyond structure

  **Recommended Agent Profile**:
  - **Category**: `quick` (simple setup task)
  - **Skills**: None needed
  - Reason: Standard Go project initialization

  **Parallelization**:
  - **Can Run In Parallel**: NO (foundation task)
  - **Blocks**: Tasks 2, 3

  **References**:
  - Go project layout: https://github.com/golang-standards/project-layout
  - Current plugin: `Contents/Code/__init__.py` (understand features to migrate)

  **Acceptance Criteria**:
  - [ ] Repository created and initialized
  - [ ] Directory structure matches plan
  - [ ] `go.mod` exists with module name
  - [ ] `.gitignore` contains Go-specific entries
  - [ ] `README.md` has basic setup instructions

  **Agent-Executed QA Scenario**:
  ```
  Scenario: Project structure valid
    Tool: Bash
    Steps:
      1. ls -la audnexus-provider/
      2. Assert: cmd/, internal/, go.mod exist
      3. Assert: go mod tidy runs without errors
      4. go build ./...
      5. Assert: Builds successfully (no code yet, just structure)
    Evidence: .sisyphus/evidence/task-1-structure.txt
  ```

  **Commit**: YES
  - Message: `chore: initial project structure`
  - Files: All new project files

- [x] 2. Go Modules & Dependencies

  **What to do**:
  - Add core dependencies to `go.mod`:
    - `github.com/gin-gonic/gin` - HTTP web framework (or use stdlib `net/http`)
    - `github.com/cespare/xxhash/v2` - Fast hashing for cache keys
    - `github.com/sirupsen/logrus` or `go.uber.org/zap` - Structured logging
  - Create `Makefile` with targets:
    - `make build` - Build binary for current platform
    - `make build-all` - Cross-compile for all platforms
    - `make run` - Run with hot reload (air or fresh)
    - `make test` - Run tests
    - `make clean` - Clean build artifacts
  - Add cross-compilation script or use `goreleaser` config
  - Run `go mod tidy` to fetch dependencies

  **Must NOT do**:
  - Don't use unnecessary frameworks (keep it minimal)
  - Don't add dependencies not used

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: None needed
  - Reason: Standard dependency management

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 1, after Task 1 starts)
  - **Blocks**: Tasks 4, 5, 6

  **References**:
  - Gin framework: https://gin-gonic.com/docs/
  - Go modules: https://go.dev/ref/mod
  - Goreleaser: https://goreleaser.com/

  **Acceptance Criteria**:
  - [ ] `go.mod` contains all dependencies
  - [ ] `Makefile` has build, build-all, run, test, clean targets
  - [ ] `go mod tidy` completes without errors
  - [ ] `make build` creates binary
  - [ ] Binary runs: `./audnexus-provider --help` shows usage

  **Agent-Executed QA Scenario**:
  ```
  Scenario: Dependencies and build work
    Tool: Bash
    Steps:
      1. go mod tidy
      2. Assert: No errors, go.sum created/updated
      3. make build
      4. Assert: Binary created at ./audnexus-provider
      5. ./audnexus-provider --help
      6. Assert: Shows help message with flags
    Evidence: .sisyphus/evidence/task-2-deps.txt
  ```

  **Commit**: YES
  - Message: `chore: add dependencies and build system`
  - Files: go.mod, go.sum, Makefile, .goreleaser.yml (optional)

- [x] 3. Configuration & Environment

  **What to do**:
  - Create `internal/config/config.go`:
    - Use `github.com/kelseyhightower/envconfig` or stdlib `os` package
    - Map all 6 legacy preferences to env vars:
      - `REGION` (default: us) - enum: au, ca, de, es, fr, in, it, jp, us, uk
      - `KEEP_EXISTING_GENRES` (default: false) - bool
      - `STORE_AUTHOR_AS_MOOD` (default: true) - bool
      - `SORT_AUTHOR_BY_LAST_NAME` (default: true) - bool
      - `SIMPLIFY_TITLE` (default: false) - bool
      - `LOG_LEVEL` (default: WARN) - enum: DEBUG, INFO, WARN, ERROR
    - Add service config:
      - `PORT` (default: 8080) - int
      - `CACHE_TTL` (default: 604800 = 1 week) - int (seconds)
      - `AUDNEXUS_TIMEOUT` (default: 90) - int (seconds)
    - Add validation for region codes
    - Add validation for log levels
  - Create Config struct with methods
  - Add `.env.example` documenting all variables

  **Must NOT do**:
  - Don't use config files (JSON/YAML) - env vars only per decision
  - Don't hardcode defaults (use constants)
  - Don't add logic beyond configuration

  **Recommended Agent Profile**:
  - **Category**: `quick`
  - **Skills**: None needed
  - Reason: Simple configuration mapping

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 1, 2)
  - **Blocks**: Task 4

  **References**:
  - Current preferences: `Contents/DefaultPrefs.json`
  - envconfig: https://github.com/kelseyhightower/envconfig

  **Acceptance Criteria**:
  - [ ] `internal/config/config.go` exists
  - [ ] Config struct with all 6 legacy preferences
  - [ ] Service config (PORT, CACHE_TTL, etc.)
  - [ ] `.env.example` documents all variables
  - [ ] Validation works (invalid region returns error)
  - [ ] Defaults match legacy plugin defaults
  - [ ] `go test ./internal/config` passes

  **Agent-Executed QA Scenario**:
  ```
  Scenario: Configuration loads correctly
    Tool: Bash
    Steps:
      1. export REGION=de
      2. export LOG_LEVEL=DEBUG
      3. go run cmd/server/main.go &
      4. sleep 1
      5. Check logs show DEBUG level and region=de
      6. kill %1
      7. unset REGION
      8. go run cmd/server/main.go &
      9. sleep 1
      10. Assert: Uses default REGION=us
    Evidence: .sisyphus/evidence/task-3-config.txt
  ```

  **Commit**: YES
  - Message: `feat: add environment configuration`
  - Files: internal/config/config.go, .env.example

- [x] 4. HTTP Server & Routing

  **What to do**:
  - Create `cmd/server/main.go`:
    - Initialize config
    - Set up structured logging
    - Create HTTP server (Gin or stdlib)
    - Register routes from handlers
    - Add graceful shutdown
  - Create `internal/handlers/provider.go`:
    - `GET /health` - Health check
    - `GET /audnexus` - MediaProvider definition
  - Create `internal/models/plex.go`:
    - MediaProvider struct
    - MediaContainer struct
    - Metadata struct
    - Feature struct
  - Create `internal/utils/logger.go`:
    - Structured logging (JSON format)
    - Log levels (DEBUG, INFO, WARN, ERROR)
  - Create `internal/cache/cache.go`:
    - Thread-safe in-memory cache
    - TTL support
    - Getter/Setter methods
  - Wire everything together in main.go

  **Must NOT do**:
  - Don't implement business logic yet
  - Don't add external API calls yet
  - Don't add scoring logic yet

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Skills**: None needed
  - Reason: Standard Go HTTP setup

  **Parallelization**:
  - **Can Run In Parallel**: NO (after Task 3)
  - **Blocks**: Tasks 7, 8

  **References**:
  - Gin docs: https://gin-gonic.com/docs/
  - Graceful shutdown: https://gobyexample.com/graceful-shutdown
  - Plex example: https://github.com/plexinc/tmdb-example-provider (for response format)

  **Acceptance Criteria**:
  - [ ] `cmd/server/main.go` creates HTTP server
  - [ ] `/health` endpoint returns `{"status":"healthy"}`
  - [ ] `/audnexus` endpoint returns MediaProvider JSON
  - [ ] Structured logging configured and outputs JSON
  - [ ] Graceful shutdown handles SIGTERM/SIGINT
  - [ ] In-memory cache initialized
  - [ ] Server starts: `go run cmd/server/main.go`

  **Agent-Executed QA Scenario**:
  ```
  Scenario: HTTP server starts and responds
    Tool: Bash
    Steps:
      1. go run cmd/server/main.go &
      2. sleep 2
      3. curl -s http://localhost:8080/health
      4. Assert: Response is {"status":"healthy"}
      5. curl -s http://localhost:8080/audnexus
      6. Assert: Contains MediaProvider with identifier
      7. kill %1
    Evidence: .sisyphus/evidence/task-4-server.txt
  ```

  **Commit**: YES
  - Message: `feat: add HTTP server and routing`
  - Files: cmd/server/main.go, internal/handlers/provider.go, internal/models/plex.go, internal/utils/logger.go, internal/cache/cache.go

- [x] 5. Audnexus API Client

  **What to do**:
  - Create `internal/api/audnexus.go`:
    - HTTP client with timeout (from config)
    - Methods:
      - `SearchAuthors(name, region string) ([]Author, error)`
      - `SearchBooks(title, region string) ([]Book, error)`
      - `GetAuthorByASIN(asin, region string) (*Author, error)`
      - `GetBookByASIN(asin, region string) (*Book, error)`
      - `GetAuthorByID(id, region string) (*Author, error)`
      - `GetBookByID(id, region string) (*Book, error)`
    - Retry logic with exponential backoff (4 retries)
    - Request/response logging
    - User-Agent header
    - Gzip decompression support
  - Create `internal/models/audnexus.go`:
    - Author struct
    - Book struct
    - JSON unmarshaling
  - Add error handling for 4xx/5xx responses
  - Use `context.Context` for cancellation

  **Must NOT do**:
  - Don't add caching yet (will be separate layer)
  - Don't add scoring logic yet
  - Don't add fallback to Audible API yet (Task 6)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-low`
  - **Skills**: None needed
  - Reason: HTTP client implementation

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Task 3)
  - **Blocks**: Task 6

  **References**:
  - Current implementation: `Contents/Code/__init__.py` lines 160-175, 202-210
  - Go HTTP client: https://pkg.go.dev/net/http
  - Context: https://go.dev/blog/context

  **Acceptance Criteria**:
  - [ ] `internal/api/audnexus.go` exists
  - [ ] All 6 API methods implemented
  - [ ] Retry logic with exponential backoff
  - [ ] Timeout configurable via env var
  - [ ] User-Agent header set correctly
  - [ ] Error handling for 4xx/5xx
  - [ ] Uses context.Context

  **Agent-Executed QA Scenario**:
  ```
  Scenario: Audnexus client works
    Tool: Bash (go test)
    Steps:
      1. Create test: go test -v ./internal/api -run TestSearchAuthors
      2. Assert: Returns author results
      3. Assert: No errors
      4. Check logs show API calls
    Evidence: .sisyphus/evidence/task-5-client.txt
  ```

  **Commit**: YES
  - Message: `feat: add Audnexus API client`
  - Files: internal/api/audnexus.go, internal/models/audnexus.go

- [x] 6. Search & Scoring Logic

  **What to do**:
  - Create `internal/services/search.go`:
    - Search orchestration logic
    - Handle ASIN extraction from strings
    - Call appropriate API methods
  - Create `internal/services/scoring.go`:
    - Levenshtein distance algorithm (use `github.com/agnivade/levenshtein`)
    - ScoreAuthor function: name similarity, position penalty
    - ScoreBook function: title + author similarity, language bonus
    - Configurable good score threshold (98)
  - Create `internal/utils/helpers.go`:
    - ASIN extraction (regex pattern)
    - String normalization (strip diacritics using `golang.org/x/text`)
    - Name to initials conversion
    - Pre-order date checking
    - Title simplification (remove subtitle, series, (un)abridged)
    - Author name sorting (Last, First)
  - Create `internal/services/metadata.go`:
    - Metadata compilation logic
    - Tag mapping (authors→moods, narrators→styles, series→moods)
  - Add comprehensive tests

  **Must NOT do**:
  - Don't implement endpoints yet
  - Don't add Audible fallback yet (separate task)

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
  - **Skills**: None needed
  - Reason: Complex scoring algorithm replication

  **Parallelization**:
  - **Can Run In Parallel**: YES (with Task 4, after Task 5)
  - **Blocks**: Tasks 7, 8

  **References**:
  - Current scoring: `Contents/Code/__init__.py` lines 176-200, 394-428
  - Current search tools: `Contents/Code/search_tools.py`
  - Current update tools: `Contents/Code/update_tools.py`
  - Levenshtein: `github.com/agnivade/levenshtein`

  **Acceptance Criteria**:
  - [ ] `ScoreAuthor` and `ScoreBook` functions work
  - [ ] Levenshtein distance calculation accurate
  - [ ] ASIN extraction regex works on various formats
  - [ ] Title simplification logic matches legacy
  - [ ] Tag mapping produces correct output
  - [ ] Pre-order detection filters future dates
  - [ ] `go test ./internal/services` passes
  - [ ] `go test ./internal/utils` passes

  **Agent-Executed QA Scenario**:
  ```
  Scenario: Scoring algorithm works correctly
    Tool: Bash (go test)
    Steps:
      1. go test -v ./internal/services -run TestScoreAuthor
      2. Assert: Exact match returns score 100
      3. go test -v ./internal/utils -run TestExtractASIN
      4. Assert: Extracts ASIN from "Author/Book B01234ABCD/Book.m4b"
      5. go test -v ./internal/services -run TestLevenshtein
      6. Assert: Distance("kitten", "sitting") = 3
    Evidence: .sisyphus/evidence/task-6-scoring.txt
  ```

  **Commit**: YES
  - Message: `feat: add search, scoring, and helper utilities`
  - Files: internal/services/search.go, internal/services/scoring.go, internal/utils/helpers.go, internal/services/metadata.go

- [x] 7. Provider Endpoints

  **What to do**:
  - Update `internal/handlers/provider.go`:
    - `GET /audnexus` already done in Task 4
  - Create `internal/handlers/matches.go`:
    - `POST /audnexus/library/metadata/matches`
    - Request body: type, title, year, language, manual flag
    - Handle artist search (type="artist")
    - Handle album search (type="album")
    - Support ASIN quick match (score=100)
    - Apply scoring and sorting
    - Return MediaContainer with Metadata array
    - Include ratingKey, guid, title, score, year
  - Add localized separators for display names
  - Add caching layer (cache search results)
  - Wire into main.go

  **Must NOT do**:
  - Don't implement metadata endpoint yet (Task 8)

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
  - **Skills**: None needed
  - Reason: Complex endpoint with many features

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Tasks 4, 5, 6)
  - **Blocks**: Task 9

  **References**:
  - Legacy search: `Contents/Code/__init__.py` lines 56-137, 250-360
  - Plex example: https://github.com/plexinc/tmdb-example-provider
  - MediaProvider spec: https://developer.plex.tv/pms/#section/API-Info/Metadata-Providers

  **Acceptance Criteria**:
  - [ ] `POST /audnexus/library/metadata/matches` accepts search requests
  - [ ] Artist search returns scored results
  - [ ] Album search returns scored results with localized separators
  - [ ] ASIN quick match bypasses search (score=100)
  - [ ] Empty search returns empty MediaContainer
  - [ ] Invalid type returns 400 error
  - [ ] Search results cached
  - [ ] `go test ./internal/handlers` passes

  **Agent-Executed QA Scenario**:
  ```
  Scenario: Provider endpoints work
    Tool: Bash (curl)
    Steps:
      1. go run cmd/server/main.go &
      2. sleep 2
      3. curl -s http://localhost:8080/audnexus
      4. Assert: Contains MediaProvider
      5. curl -s -X POST http://localhost:8080/audnexus/library/metadata/matches \
           -H "Content-Type: application/json" \
           -d '{"type":"artist","title":"Stephen King","lang":"en"}'
      6. Assert: Contains MediaContainer with Metadata
      7. curl -s -X POST ... -d '{"type":"album","title":"B01234ABCD","lang":"en"}' | jq '.MediaContainer.Metadata[0].score'
      8. Assert: Score is 100
      9. kill %1
    Evidence: .sisyphus/evidence/task-7-endpoints.json
  ```

  **Commit**: YES
  - Message: `feat: add provider and matches endpoints`
  - Files: internal/handlers/matches.go (updated), internal/handlers/provider.go

- [x] 8. Metadata Endpoints

  **What to do**:
  - Create `internal/handlers/metadata.go`:
    - `GET /audnexus/library/metadata/{ratingKey}`
    - Parse ratingKey to determine type (artist/album) and ID
    - For artist (type="artist"):
      - Fetch author details from Audnexus API
      - Set metadata: title, titleSort, summary, thumb (URL), genres, similar
      - Apply sort preference (Last, First)
    - For album (type="album"):
      - Fetch book details from Audnexus API
      - Set metadata: title, titleSort, summary, thumb (URL), rating, year, studio
      - Set moods (authors), styles (narrators), series→moods
      - Apply title simplification if configured
      - Apply pre-order filtering
    - Return MediaContainer with single Metadata item
  - Handle 404 for unknown IDs
  - Handle API errors gracefully
  - Add caching layer (cache metadata)
  - Wire into main.go

  **Must NOT do**:
  - Don't proxy/cache images (return direct URLs)
  - Don't store metadata locally

  **Recommended Agent Profile**:
  - **Category**: `ultrabrain`
  - **Skills**: None needed
  - Reason: Complex metadata compilation

  **Parallelization**:
  - **Can Run In Parallel**: YES (after Tasks 4, 5, 6)
  - **Blocks**: Task 9

  **References**:
  - Legacy update: `Contents/Code/__init__.py` lines 139-232, 362-472
  - Legacy update tools: `Contents/Code/update_tools.py`

  **Acceptance Criteria**:
  - [ ] `GET /audnexus/library/metadata/{ratingKey}` returns metadata
  - [ ] Artist metadata includes bio, image URL, genres, similar
  - [ ] Book metadata includes summary, rating, date, publisher
  - [ ] Tag mappings correct (authors→moods, narrators→styles)
  - [ ] Preferences applied (sort order, title simplification)
  - [ ] 404 returned for unknown ratingKey
  - [ ] Image URLs are direct Audible CDN links
  - [ ] Metadata cached
  - [ ] `go test ./internal/handlers` passes

  **Agent-Executed QA Scenario**:
  ```
  Scenario: Metadata endpoints return full metadata
    Tool: Bash (curl)
    Steps:
      1. go run cmd/server/main.go &
      2. sleep 2
      3. curl -s http://localhost:8080/audnexus/library/metadata/artist_B01234ABCD
      4. Assert: Contains MediaContainer with Metadata
      5. Assert: Has title, summary, thumb, genres
      6. curl -s http://localhost:8080/audnexus/library/metadata/album_B05678EFGH
      7. Assert: Has title, summary, rating, year, studio
      8. Assert: Contains moods, styles
      9. curl -s http://localhost:8080/audnexus/library/metadata/artist_INVALID
      10. Assert: HTTP 404 status
      11. kill %1
    Evidence: .sisyphus/evidence/task-8-metadata.json
  ```

  **Commit**: YES
  - Message: `feat: add metadata retrieval endpoint`
  - Files: internal/handlers/metadata.go

- [x] 9. Build System & Documentation

  **What to do**:
  - Update `Makefile` for cross-compilation:
    - `make build-all` builds for:
      - linux/amd64
      - linux/arm64
      - darwin/amd64
      - darwin/arm64 (M1/M2 Macs)
      - windows/amd64
    - `make release` creates GitHub release
  - Create `.goreleaser.yml` for automated releases:
    - Binary naming: `audnexus-provider-{{.Os}}-{{.Arch}}`
    - Archive format: `.tar.gz` (Unix), `.zip` (Windows)
    - Include README and LICENSE
  - Create comprehensive `README.md`:
    - Installation (download binary vs build from source)
    - Configuration (env vars table)
    - Usage with Plex (step-by-step)
    - Platform-specific instructions
    - Troubleshooting
    - Migration notes for existing users
  - Create `CHANGELOG.md` with initial release notes
  - Add GitHub Actions workflow:
    - `.github/workflows/build.yml` - Build on PR
    - `.github/workflows/release.yml` - Release on tag
  - Add `.gitignore` for Go + release artifacts
  - Test end-to-end:
    - Build binary
    - Run binary
    - Test all endpoints
    - Test all 10 regions
    - Verify caching works
  - Tag initial release (v1.0.0)

  **Must NOT do**:
  - Don't add features beyond parity
  - Don't change architecture
  - Don't add Docker (not needed for Go binary)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
  - **Skills**: None needed
  - Reason: Integration and documentation

  **Parallelization**:
  - **Can Run In Parallel**: NO (after Tasks 7, 8)
  - **Blocks**: None (final task)

  **References**:
  - Goreleaser: https://goreleaser.com/
  - Original README: `README.md` (reference for content)

  **Acceptance Criteria**:
  - [ ] `make build-all` creates binaries for all platforms
  - [ ] Binaries run without external dependencies
  - [ ] All 10 regions tested
  - [ ] ASIN quick match tested
  - [ ] Search scoring matches legacy behavior
  - [ ] Tag mappings verified
  - [ ] README.md is comprehensive
  - [ ] All env vars documented
  - [ ] GitHub Actions workflows work
  - [ ] Git tag v1.0.0 created

  **Agent-Executed QA Scenario**:
  ```
  Scenario: Full integration test
    Tool: Bash
    Steps:
      1. make build-all
      2. Assert: All binaries exist in dist/
      3. ./dist/audnexus-provider-linux-amd64 &
      4. sleep 2
      5. ./scripts/test-all.sh (comprehensive test suite)
      6. Test each region: REGION=de, REGION=uk, etc.
      7. Verify caching: time curl ... (second request faster)
      8. kill %1
    Evidence: .sisyphus/evidence/task-9-integration.txt
  ```

  **Commit**: YES
  - Message: `feat: add build system and documentation`
  - Files: Makefile, .goreleaser.yml, README.md, CHANGELOG.md, .github/workflows/*
  - Tag: `v1.0.0`

---

## Commit Strategy

| After Task | Branch | Message | Files | Verification |
|------------|--------|---------|-------|--------------|
| 0 | archive/legacy-python | `docs: archive legacy Python implementation` | README.md, ARCHIVE.md | git tag v1.x.x-final |
| 1 | feature/go-migration | `chore: initial project structure` | All scaffold files | go build ./... |
| 2 | feature/go-migration | `chore: add dependencies and build system` | go.mod, Makefile | make build |
| 3 | feature/go-migration | `feat: add environment configuration` | internal/config/ | go test ./internal/config |
| 4 | feature/go-migration | `feat: add HTTP server and routing` | cmd/server/, internal/handlers/provider.go | curl /health |
| 5 | feature/go-migration | `feat: add Audnexus API client` | internal/api/ | go test ./internal/api |
| 6 | feature/go-migration | `feat: add search, scoring, and helper utilities` | internal/services/, internal/utils/ | go test ./internal/... |
| 7 | feature/go-migration | `feat: add provider and matches endpoints` | internal/handlers/matches.go | curl endpoints |
| 8 | feature/go-migration | `feat: add metadata retrieval endpoint` | internal/handlers/metadata.go | curl metadata |
| 9 | feature/go-migration | `feat: add build system and documentation` | Makefile, README.md, .github/ | make build-all |
| Final | main | `feat: migrate to Go implementation` | Merge PR | Full integration test |

---

## Success Criteria

### Verification Commands
```bash
# 1. Build binary
make build

# 2. Start service
./audnexus-provider &

# 3. Test health
curl http://localhost:8080/health
# Expected: {"status":"healthy"}

# 4. Test provider discovery
curl http://localhost:8080/audnexus
# Expected: MediaProvider JSON with features

# 5. Test author search
curl -X POST http://localhost:8080/audnexus/library/metadata/matches \
  -H "Content-Type: application/json" \
  -d '{"type":"artist","title":"Stephen King","lang":"en"}'
# Expected: MediaContainer with Metadata array

# 6. Test book search with ASIN
curl -X POST http://localhost:8080/audnexus/library/metadata/matches \
  -H "Content-Type: application/json" \
  -d '{"type":"album","title":"B01234ABCD","lang":"en"}'
# Expected: Single result with score 100

# 7. Test metadata retrieval
curl http://localhost:8080/audnexus/library/metadata/artist_B01234ABCD
# Expected: Full artist metadata

# 8. Build all platforms
make build-all
# Expected: Binaries for linux/amd64, linux/arm64, darwin/amd64, darwin/arm64, windows/amd64

# 9. Stop service
kill %1
```

### Final Checklist
- [ ] All "Must Have" items implemented
- [ ] All "Must NOT Have" items absent
- [ ] Single binary runs without dependencies
- [ ] All 10 regions supported
- [ ] ASIN quick matching works
- [ ] Fuzzy search scoring matches legacy
- [ ] Tag mappings correct
- [ ] Cross-compiled binaries available
- [ ] Environment variables documented
- [ ] Manual testing completed
- [ ] v1.0.0 tag created

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Plex doesn't support music/audiobook providers | High | Critical | Document as known limitation; monitor Plex updates |
| Audnexus API changes | Low | High | Version API client; add abstraction layer |
| Cross-compilation issues | Medium | Low | Use goreleaser; test on target platforms |
| Feature parity gaps | Medium | Medium | Comprehensive QA scenarios; manual testing |
| Performance issues with external API | Medium | Medium | In-memory caching; retry logic; timeout handling |

---

## Post-Migration Notes

### For Users
1. **New Deployment**: Download single binary instead of copying bundle
2. **Configuration**: Set env vars instead of using Plex UI preferences
3. **URL**: Configure in Plex as `http://localhost:8080/audnexus`
4. **No Scanner Hooking**: Plex handles file scanning; metadata only

### For Maintainers
1. **Separate Repo**: New codebase at `audnexus-provider` in Go
2. **Modern Stack**: Go with single binary deployment
3. **External Service**: Runs outside PMS process
4. **HTTP API**: RESTful instead of Python class inheritance
5. **Easy Distribution**: Pre-built binaries via GitHub Releases

---

*Plan generated: 2026-02-09*  
*Target: Plex Metadata Providers API*  
*Language: Go*  
*Status: Ready for execution*
