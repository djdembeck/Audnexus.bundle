package handlers

import (
	"net/http"
	"strings"
	"time"

	"github.com/djdembeck/audnexus-provider/internal/cache"
	"github.com/djdembeck/audnexus-provider/internal/config"
	"github.com/djdembeck/audnexus-provider/internal/models"
	"github.com/djdembeck/audnexus-provider/internal/services"
	"github.com/gin-gonic/gin"
)

type MetadataHandler struct {
	metadataService *services.MetadataService
	cache           *cache.Cache
	cfg             *config.Config
}

func NewMetadataHandler(metadataService *services.MetadataService, cache *cache.Cache, cfg *config.Config) *MetadataHandler {
	return &MetadataHandler{
		metadataService: metadataService,
		cache:           cache,
		cfg:             cfg,
	}
}

func (h *MetadataHandler) RegisterRoutes(r *gin.Engine) {
	r.GET("/audnexus/library/metadata/:ratingKey", h.handleMetadata)
}

func (h *MetadataHandler) handleMetadata(c *gin.Context) {
	ratingKey := c.Param("ratingKey")

	// Parse ratingKey (format: "author_ASIN" or "album_ASIN")
	parts := strings.SplitN(ratingKey, "_", 2)
	if len(parts) != 2 {
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid ratingKey format"})
		return
	}

	itemType := parts[0]
	asin := parts[1]

	// Check cache
	if cached, found := h.cache.Get(ratingKey); found {
		c.JSON(http.StatusOK, cached)
		return
	}

	ctx := c.Request.Context()
	var metadata *models.Metadata
	var err error

	switch itemType {
	case "author":
		metadata, err = h.metadataService.GetAuthorMetadata(ctx, asin)
	case "album":
		metadata, err = h.metadataService.GetBookMetadata(ctx, asin)
	default:
		c.JSON(http.StatusBadRequest, gin.H{"error": "invalid type"})
		return
	}

	if err != nil {
		c.JSON(http.StatusNotFound, gin.H{"error": "not found"})
		return
	}

	container := models.MediaContainer{
		Identifier: "audnexus",
		Size:       1,
		Metadata:   []models.Metadata{*metadata},
	}

	// Cache result
	h.cache.Set(ratingKey, container, time.Duration(h.cfg.CacheTTL)*time.Second)

	c.JSON(http.StatusOK, container)
}
