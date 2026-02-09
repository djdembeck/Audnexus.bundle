package handlers

import (
	"github.com/djdembeck/audnexus-provider/internal/models"
	"github.com/gin-gonic/gin"
)

func RegisterProviderRoutes(r *gin.Engine) {
	r.GET("/health", healthHandler)
	r.GET("/audnexus", providerHandler)
}

func healthHandler(c *gin.Context) {
	c.JSON(200, gin.H{"status": "healthy"})
}

func providerHandler(c *gin.Context) {
	provider := models.MediaProvider{
		Identifier: "audnexus",
		Title:      "Audnexus",
		Types:      []string{"artist", "album"},
		Features: []models.Feature{
			{Type: "match", Name: "audnexus", Enabled: true},
			{Type: "metadata", Name: "audnexus", Enabled: true},
		},
	}
	c.JSON(200, provider)
}
