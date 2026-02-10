# Draft: Plex Plugin Migration Plan

## Project Context
- **Repository**: Audnexus.bundle - Plex plugin for Audible metadata
- **Migration Goal**: Move from legacy Plex plugin API to new Metadata Providers HTTP API
- **Date Started**: 2026-02-09

## User Decisions Confirmed

### Approach
- **Strategy**: Create HTTP API metadata provider now, targeting music/audiobook libraries
- **Timeline**: Proactive (before 2026 deprecation deadline)
- **Scope**: Complete rewrite, all features on day one
- **Compatibility**: New system only (no backwards compatibility)
- **Testing**: Manual testing
- **Risk Tolerance**: Complete rewrite all at once

## Research Summary

### Current Plugin Architecture (Legacy Framework 2)

**Agent Classes**:
- `AudiobookArtist` (Agent.Artist): Author metadata provider
  - `search()`: Search authors by name or ASIN
  - `update()`: Update author bio, image, genres, similar authors
- `AudiobookAlbum` (Agent.Album): Book metadata provider
  - `search()`: Search books by title/author or ASIN
  - `update()`: Update book metadata (title, summary, rating, etc.)

**Key Features**:
1. **ASIN Quick Match**: Bypass search when ASIN provided in filename or manual search
2. **Multi-Region Support**: US, UK, DE, FR, IT, ES, JP, AU, CA, IN
3. **Scoring Algorithm**: Levenshtein distance for fuzzy matching on titles/authors
4. **Localized Separators**: Language-specific display formats ("by", "w/", "von", "mit", etc.)
5. **Tag Mappings**:
   - Authors → Mood tags
   - Narrators → Style tags
   - Series → Mood tags (with "Series:" prefix)
6. **Pre-order Detection**: Filters out future releases
7. **HTTP Caching**: 1-week cache with gzip encoding
8. **Retry Logic**: 4 retries with exponential backoff

**User Preferences** (6 settings):
- `region`: Default search region (enum: au, ca, de, es, fr, in, it, jp, us, uk)
- `keep_existing_genres`: Boolean - preserve existing genres
- `store_author_as_mood`: Boolean - append authors as Mood tags
- `sort_author_by_last_name`: Boolean - sort as "Last, First"
- `simplify_title`: Boolean - remove subtitles, series info, (un)abridged
- `logging_level`: Verbosity (DEBUG, INFO, WARN, ERROR)

**External APIs**:
- Primary: `api.audnex.us` (Audnexus aggregator)
- Fallback: `api.audible.{TLD}` (Audible catalog search)
- Images: Audible CDN (images-na.ssl-images-amazon.com)

### New System Requirements (Metadata Providers)

**Architecture**:
- HTTP-based external service (language agnostic)
- RESTful API with JSON responses
- Deployed as Docker container, binary, or hosted service

**Required Endpoints**:
1. `GET /{provider}` - MediaProvider definition (capabilities, features)
2. `POST /{provider}/library/metadata/matches` - Search/matching
3. `GET /{provider}/library/metadata/{id}` - Metadata retrieval

**Response Format**:
- MediaContainer JSON with standardized metadata fields
- RatingKey: URL-safe unique identifier
- GUID: Format `scheme://type/ratingKey`

**Key Changes**:
- No Python bundle structure
- No `Agent.Artist/Album` inheritance
- No `Proxy.Media` for images (direct URLs)
- No `DefaultPrefs.json` (preferences handled differently)
- No embedded deployment (external service)

### Migration Challenges & Adaptations

**Challenge 1: User Preferences**
- **Issue**: New system doesn't have provider preferences UI yet (per Plex announcement)
- **Options**:
  a) Hardcode defaults initially
  b) Use environment variables for configuration
  c) Wait for Plex to implement preferences (no timeline)
  d) Create companion config file

**Challenge 2: Music/Audiobook Support**
- **Issue**: Plex officially says only Movie/TV supported, but user wants to proceed
- **Approach**: Attempt to implement with music library types, test with Plex beta
- **Risk**: May not work until Plex adds official support

**Challenge 3: Image Handling**
- **Current**: Uses `Proxy.Media()` to proxy/cache images
- **New**: Return direct image URLs in metadata response
- **Adaptation**: Plex will fetch images directly from URLs provided

**Challenge 4: HTTP Caching**
- **Current**: Uses `HTTP.CacheTime` and `HTTP.ClearCache()`
- **New**: External service handles its own caching
- **Adaptation**: Implement caching layer in new service (Redis, in-memory, etc.)

**Challenge 5: Language Support**
- **Current**: Uses `Locale.Language.English` and language codes
- **New**: HTTP headers (`Accept-Language`) or query parameters
- **Adaptation**: Pass language through request headers

**Challenge 6: Error Handling & Logging**
- **Current**: Uses Plex's `Log.Debug()`, `Log.Error()`, etc.
- **New**: Service handles its own logging
- **Adaptation**: Structured logging (JSON) to stdout/stderr

## Technical Recommendations

### Language/Framework Options

**Option A: Python (FastAPI/Flask)**
- Pros: Can reuse some logic concepts, familiar to current maintainers
- Cons: Still requires complete rewrite, no code reuse possible

**Option B: Node.js/TypeScript (Express/Fastify)**
- Pros: Plex's official example uses TypeScript, large ecosystem
- Cons: Different language from current codebase

**Option C: Go**
- Pros: Single binary deployment, excellent performance, built-in HTTP server
- Cons: Steeper learning curve, less ecosystem for this use case

**Recommendation**: Python with FastAPI
- Fastest development time given existing Python knowledge
- Excellent async support for API calls
- Automatic OpenAPI documentation
- Type hints support

### Project Structure (New)

```
audnexus-provider/
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
├── config/
│   ├── __init__.py
│   └── settings.py          # Environment-based config
├── api/
│   ├── __init__.py
│   ├── main.py              # FastAPI app entry point
│   ├── models.py            # Pydantic models for requests/responses
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── provider.py      # GET /{provider}
│   │   ├── matches.py       # POST /matches
│   │   └── metadata.py      # GET /metadata/{id}
│   └── dependencies.py      # Shared dependencies
├── services/
│   ├── __init__.py
│   ├── audnexus.py          # Audnexus API client
│   ├── audible.py           # Audible API client (fallback)
│   ├── search.py            # Search logic
│   ├── scoring.py           # Levenshtein distance scoring
│   └── metadata.py          # Metadata compilation
├── utils/
│   ├── __init__.py
│   ├── cache.py             # Caching layer
│   ├── logging.py           # Structured logging
│   └── helpers.py           # String utils, ASIN extraction
└── tests/
    └── ...
```

### Deployment Strategy

**Primary**: Docker container
- Easy for users to run
- Consistent environment
- Can bundle with docker-compose

**Secondary**: Standalone binary (optional future enhancement)
- PyInstaller or similar
- For users who don't want Docker

## Open Implementation Questions

1. **How to handle user preferences without Plex UI?**
   - Environment variables?
   - Config file mounted as volume?
   - Both?

2. **Should we maintain backwards compatibility with audnex.us API?**
   - Yes, it's the same API
   - May need updates if API changes

3. **Caching strategy?**
   - In-memory (simple, fast, lost on restart)
   - Redis (persistent, shared across instances)
   - Filesystem (simple, survives restarts)

4. **Rate limiting?**
   - Audnexus API rate limits?
   - Plex's request patterns?

5. **Authentication?**
   - Plex doesn't support auth yet for providers
   - Should we add API key support for direct access?

## Next Steps

1. Finalize technical decisions (preferences handling, caching)
2. Generate detailed work plan with TODOs
3. Begin implementation phase
