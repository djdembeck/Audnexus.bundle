package handlers

import (
	"net/http"
	"strings"

	"github.com/djdembeck/audnexus-provider/internal/cache"
	"github.com/djdembeck/audnexus-provider/internal/config"
	"github.com/djdembeck/audnexus-provider/internal/models"
	"github.com/djdembeck/audnexus-provider/internal/services"
	"github.com/gin-gonic/gin"
)

// MatchesHandler handles match/search requests
type MatchesHandler struct {
	searchService *services.SearchService
	cache         *cache.Cache
	cfg           *config.Config
}

// NewMatchesHandler creates a new MatchesHandler
func NewMatchesHandler(searchService *services.SearchService, c *cache.Cache, cfg *config.Config) *MatchesHandler {
	return &MatchesHandler{
		searchService: searchService,
		cache:         c,
		cfg:           cfg,
	}
}

// RegisterRoutes registers the matches routes
func (h *MatchesHandler) RegisterRoutes(r *gin.Engine) {
	r.POST("/audnexus/library/metadata/matches", h.handleMatches)
}

// handleMatches handles POST /matches requests
func (h *MatchesHandler) handleMatches(c *gin.Context) {
	var req struct {
		Title  string `json:"title"`
		Author string `json:"author"`
		Type   string `json:"type"`
	}

	if err := c.ShouldBindJSON(&req); err != nil {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid request body"})
		return
	}

	// Determine search type
	searchType := strings.ToLower(req.Type)
	if searchType == "" {
		searchType = "album"
	}

	var results []services.ScoreResult
	var err error

	switch searchType {
	case "artist":
		results, err = h.searchService.SearchAuthors(c.Request.Context(), req.Title)
	case "album", "track":
		results, err = h.searchService.SearchBooks(c.Request.Context(), req.Title, req.Author)
	default:
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid type: must be 'artist' or 'album'"})
		return
	}

	if err != nil {
		c.JSON(http.StatusInternalServerError, gin.H{"error": err.Error()})
		return
	}

	// Convert results to metadata
	metadata := make([]models.Metadata, 0, len(results))
	for _, r := range results {
		metadata = append(metadata, r.Result)
	}

	c.JSON(http.StatusOK, models.MediaContainer{
		Size:     len(metadata),
		Metadata: metadata,
	})
}
