package config

import (
	"fmt"
	"os"
	"strconv"
	"strings"
)

// Valid region codes
var validRegions = []string{"au", "ca", "de", "es", "fr", "in", "it", "jp", "us", "uk"}

// Valid log levels
var validLogLevels = []string{"DEBUG", "INFO", "WARN", "ERROR"}

// Config holds all configuration for the Audnexus service
type Config struct {
	// Legacy preferences
	Region               string
	KeepExistingGenres   bool
	StoreAuthorAsMood    bool
	SortAuthorByLastName bool
	SimplifyTitle        bool
	LogLevel             string

	// Service config
	Port            int
	CacheTTL        int
	AudnexusTimeout int
}

// Load reads configuration from environment variables
func Load() (*Config, error) {
	cfg := &Config{
		Region:               getEnv("REGION", "us"),
		KeepExistingGenres:   getEnvBool("KEEP_EXISTING_GENRES", false),
		StoreAuthorAsMood:    getEnvBool("STORE_AUTHOR_AS_MOOD", true),
		SortAuthorByLastName: getEnvBool("SORT_AUTHOR_BY_LAST_NAME", true),
		SimplifyTitle:        getEnvBool("SIMPLIFY_TITLE", false),
		LogLevel:             getEnv("LOG_LEVEL", "INFO"),
		Port:                 getEnvInt("PORT", 8080),
		CacheTTL:             getEnvInt("CACHE_TTL", 604800),
		AudnexusTimeout:      getEnvInt("AUDNEXUS_TIMEOUT", 90),
	}

	// Validate region
	if !contains(validRegions, cfg.Region) {
		return nil, fmt.Errorf("invalid REGION: %s (valid: %s)", cfg.Region, strings.Join(validRegions, ", "))
	}

	// Validate log level
	if !contains(validLogLevels, cfg.LogLevel) {
		return nil, fmt.Errorf("invalid LOG_LEVEL: %s (valid: %s)", cfg.LogLevel, strings.Join(validLogLevels, ", "))
	}

	return cfg, nil
}

// getEnv reads a string environment variable with a default value
func getEnv(key, defaultValue string) string {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	return value
}

// getEnvBool reads a boolean environment variable with a default value
func getEnvBool(key string, defaultValue bool) bool {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	// Parse boolean - accept "true", "1", "yes" (case insensitive)
	lower := strings.ToLower(value)
	return lower == "true" || lower == "1" || lower == "yes"
}

// getEnvInt reads an integer environment variable with a default value
func getEnvInt(key string, defaultValue int) int {
	value := os.Getenv(key)
	if value == "" {
		return defaultValue
	}
	parsed, err := strconv.Atoi(value)
	if err != nil {
		return defaultValue
	}
	return parsed
}

// contains checks if a slice contains a specific string
func contains(slice []string, item string) bool {
	for _, s := range slice {
		if s == item {
			return true
		}
	}
	return false
}
