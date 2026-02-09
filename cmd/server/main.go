package main

import (
	"flag"
	"fmt"
	"os"

	"github.com/gin-gonic/gin"
	"github.com/sirupsen/logrus"
)

var (
	help    bool
	version bool
	logger  = logrus.New()
)

func init() {
	flag.BoolVar(&help, "help", false, "Show help message")
	flag.BoolVar(&version, "version", false, "Show version information")
}

func main() {
	flag.Parse()

	if help {
		fmt.Println("audnexus-provider - Audnexus Provider Service")
		fmt.Println()
		fmt.Println("Usage: audnexus-provider [flags]")
		fmt.Println()
		fmt.Println("Flags:")
		flag.PrintDefaults()
		os.Exit(0)
	}

	if version {
		fmt.Println("audnexus-provider version 1.0.0")
		os.Exit(0)
	}

	logger.Info("audnexus-provider starting...")

	// Set Gin to release mode in production
	gin.SetMode(gin.ReleaseMode)

	router := gin.New()
	router.Use(gin.Recovery())
	router.Use(loggerMiddleware())

	// Health check endpoint
	router.GET("/health", func(c *gin.Context) {
		c.JSON(200, gin.H{
			"status": "healthy",
		})
	})

	logger.Info("Server initialization complete")
	logger.Info("Listening on :8080")

	if err := router.Run(":8080"); err != nil {
		logger.Fatalf("Failed to start server: %v", err)
	}
}

func loggerMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		logger.Infof("%s %s %s", c.Request.Method, c.Request.URL.Path, c.ClientIP())
		c.Next()
	}
}
