# Plex Migration Learnings

## Task 6 Part 4: Metadata Service Creation

### What was created
- `internal/services/metadata.go` - MetadataService with GetAuthorMetadata and GetBookMetadata methods

### Key patterns observed
- MetadataService wraps api.Client and config.Config
- Maps Author/Book models to Plex Metadata format
- Applies config-based transformations (SortName, SimplifyTitle)
- Uses GUID format "audnexus://{type}/{asin}" for Plex identification

### Dependencies used
- `internal/api.Client` - GetAuthorByASIN, GetBookByASIN
- `internal/config.Config` - Region, SortAuthorByLastName, SimplifyTitle, StoreAuthorAsMood
- `internal/utils` - SortName, SimplifyTitle
- `internal/models.Metadata` - Plex metadata response format

### Field mappings
**Author → Metadata:**
- RatingKey: "author_" + ASIN
- GUID: "audnexus://author/" + ASIN
- Type: "artist"
- Title: Name (optionally sorted by last name)
- Summary: Description
- Thumb: Image
- Genres: Genres
- Similar: Similar

**Book → Metadata:**
- RatingKey: "album_" + ASIN
- GUID: "audnexus://album/" + ASIN
- Type: "album"
- Title: Title (optionally simplified)
- Summary: Description
- Year: ReleaseDate.Year()
- Thumb: Image
- Rating: Rating
- Studio: Publisher
- Moods: Authors (optionally sorted) + Series (prefixed with "Series:")
- Styles: Narrators