package main

import (
	"flag"
	"fmt"
	"os"
	"strconv"

	"github.com/djdembeck/audnexus-provider/internal/config"
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

	// Load configuration
	cfg, err := config.Load()
	if err != nil {
		logger.Fatalf("Failed to load configuration: %v", err)
	}

	logger.Infof("audnexus-provider starting...")
	logger.Infof("Region: %s", cfg.Region)
	logger.Infof("Log Level: %s", cfg.LogLevel)
	logger.Infof("Cache TTL: %d seconds", cfg.CacheTTL)
	logger.Infof("Audnexus Timeout: %d seconds", cfg.AudnexusTimeout)

	// Set log level from config
	switch cfg.LogLevel {
	case "DEBUG":
		logger.SetLevel(logrus.DebugLevel)
	case "INFO":
		logger.SetLevel(logrus.InfoLevel)
	case "WARN":
		logger.SetLevel(logrus.WarnLevel)
	case "ERROR":
		logger.SetLevel(logrus.ErrorLevel)
	}

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
	logger.Infof("Listening on :%d", cfg.Port)

	addr := ":" + strconv.Itoa(cfg.Port)
	if err := router.Run(addr); err != nil {
		logger.Fatalf("Failed to start server: %v", err)
	}
}

func loggerMiddleware() gin.HandlerFunc {
	return func(c *gin.Context) {
		logger.Infof("%s %s %s", c.Request.Method, c.Request.URL.Path, c.ClientIP())
		c.Next()
	}
}
