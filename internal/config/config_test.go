package config

import (
	"os"
	"testing"
)

func TestLoadDefaultValues(t *testing.T) {
	// Clear all env vars we're testing
	envVars := []string{"REGION", "KEEP_EXISTING_GENRES", "STORE_AUTHOR_AS_MOOD",
		"SORT_AUTHOR_BY_LAST_NAME", "SIMPLIFY_TITLE", "LOG_LEVEL",
		"PORT", "CACHE_TTL", "AUDNEXUS_TIMEOUT"}
	for _, v := range envVars {
		os.Unsetenv(v)
	}

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() returned error: %v", err)
	}

	// Test defaults
	if cfg.Region != "us" {
		t.Errorf("Region = %q, want %q", cfg.Region, "us")
	}
	if cfg.KeepExistingGenres != false {
		t.Errorf("KeepExistingGenres = %v, want %v", cfg.KeepExistingGenres, false)
	}
	if cfg.StoreAuthorAsMood != true {
		t.Errorf("StoreAuthorAsMood = %v, want %v", cfg.StoreAuthorAsMood, true)
	}
	if cfg.SortAuthorByLastName != true {
		t.Errorf("SortAuthorByLastName = %v, want %v", cfg.SortAuthorByLastName, true)
	}
	if cfg.SimplifyTitle != false {
		t.Errorf("SimplifyTitle = %v, want %v", cfg.SimplifyTitle, false)
	}
	if cfg.LogLevel != "INFO" {
		t.Errorf("LogLevel = %q, want %q", cfg.LogLevel, "INFO")
	}
	if cfg.Port != 8080 {
		t.Errorf("Port = %d, want %d", cfg.Port, 8080)
	}
	if cfg.CacheTTL != 604800 {
		t.Errorf("CacheTTL = %d, want %d", cfg.CacheTTL, 604800)
	}
	if cfg.AudnexusTimeout != 90 {
		t.Errorf("AudnexusTimeout = %d, want %d", cfg.AudnexusTimeout, 90)
	}
}

func TestLoadWithEnvironmentVariables(t *testing.T) {
	// Set custom env vars
	os.Setenv("REGION", "de")
	os.Setenv("KEEP_EXISTING_GENRES", "true")
	os.Setenv("STORE_AUTHOR_AS_MOOD", "false")
	os.Setenv("SORT_AUTHOR_BY_LAST_NAME", "false")
	os.Setenv("SIMPLIFY_TITLE", "true")
	os.Setenv("LOG_LEVEL", "DEBUG")
	os.Setenv("PORT", "3000")
	os.Setenv("CACHE_TTL", "3600")
	os.Setenv("AUDNEXUS_TIMEOUT", "30")
	defer func() {
		// Cleanup
		for _, v := range []string{"REGION", "KEEP_EXISTING_GENRES", "STORE_AUTHOR_AS_MOOD",
			"SORT_AUTHOR_BY_LAST_NAME", "SIMPLIFY_TITLE", "LOG_LEVEL",
			"PORT", "CACHE_TTL", "AUDNEXUS_TIMEOUT"} {
			os.Unsetenv(v)
		}
	}()

	cfg, err := Load()
	if err != nil {
		t.Fatalf("Load() returned error: %v", err)
	}

	if cfg.Region != "de" {
		t.Errorf("Region = %q, want %q", cfg.Region, "de")
	}
	if cfg.KeepExistingGenres != true {
		t.Errorf("KeepExistingGenres = %v, want %v", cfg.KeepExistingGenres, true)
	}
	if cfg.StoreAuthorAsMood != false {
		t.Errorf("StoreAuthorAsMood = %v, want %v", cfg.StoreAuthorAsMood, false)
	}
	if cfg.SortAuthorByLastName != false {
		t.Errorf("SortAuthorByLastName = %v, want %v", cfg.SortAuthorByLastName, false)
	}
	if cfg.SimplifyTitle != true {
		t.Errorf("SimplifyTitle = %v, want %v", cfg.SimplifyTitle, true)
	}
	if cfg.LogLevel != "DEBUG" {
		t.Errorf("LogLevel = %q, want %q", cfg.LogLevel, "DEBUG")
	}
	if cfg.Port != 3000 {
		t.Errorf("Port = %d, want %d", cfg.Port, 3000)
	}
	if cfg.CacheTTL != 3600 {
		t.Errorf("CacheTTL = %d, want %d", cfg.CacheTTL, 3600)
	}
	if cfg.AudnexusTimeout != 30 {
		t.Errorf("AudnexusTimeout = %d, want %d", cfg.AudnexusTimeout, 30)
	}
}

func TestLoadInvalidRegion(t *testing.T) {
	os.Setenv("REGION", "invalid")
	defer os.Unsetenv("REGION")

	_, err := Load()
	if err == nil {
		t.Error("Load() should return error for invalid REGION")
	}
}

func TestLoadInvalidLogLevel(t *testing.T) {
	os.Setenv("LOG_LEVEL", "TRACE")
	defer os.Unsetenv("LOG_LEVEL")

	_, err := Load()
	if err == nil {
		t.Error("Load() should return error for invalid LOG_LEVEL")
	}
}

func TestBoolParsing(t *testing.T) {
	tests := []struct {
		input string
		want  bool
	}{
		{"true", true},
		{"TRUE", true},
		{"True", true},
		{"1", true},
		{"yes", true},
		{"YES", true},
		{"false", false},
		{"FALSE", false},
		{"0", false},
		{"no", false},
		{"", false},
	}

	for _, tt := range tests {
		os.Setenv("TEST_BOOL", tt.input)
		got := getEnvBool("TEST_BOOL", false)
		if got != tt.want {
			t.Errorf("getEnvBool(%q) = %v, want %v", tt.input, got, tt.want)
		}
		os.Unsetenv("TEST_BOOL")
	}
}

func TestIntParsing(t *testing.T) {
	os.Setenv("TEST_INT", "42")
	defer os.Unsetenv("TEST_INT")

	got := getEnvInt("TEST_INT", 0)
	if got != 42 {
		t.Errorf("getEnvInt() = %d, want %d", got, 42)
	}
}

func TestIntParsingInvalid(t *testing.T) {
	os.Setenv("TEST_INT", "invalid")
	defer os.Unsetenv("TEST_INT")

	got := getEnvInt("TEST_INT", 99)
	if got != 99 {
		t.Errorf("getEnvInt() with invalid value = %d, want %d", got, 99)
	}
}

func TestContains(t *testing.T) {
	slice := []string{"au", "ca", "de", "us", "uk"}

	if !contains(slice, "us") {
		t.Error("contains(slice, 'us') should return true")
	}
	if contains(slice, "xx") {
		t.Error("contains(slice, 'xx') should return false")
	}
}

func TestAllValidRegions(t *testing.T) {
	validRegions := []string{"au", "ca", "de", "es", "fr", "in", "it", "jp", "us", "uk"}

	for _, region := range validRegions {
		os.Setenv("REGION", region)
		defer os.Unsetenv("REGION")

		cfg, err := Load()
		if err != nil {
			t.Errorf("Load() failed for REGION=%q: %v", region, err)
		}
		if cfg.Region != region {
			t.Errorf("Region = %q, want %q", cfg.Region, region)
		}
	}
}

func TestAllValidLogLevels(t *testing.T) {
	validLogLevels := []string{"DEBUG", "INFO", "WARN", "ERROR"}

	for _, level := range validLogLevels {
		os.Setenv("LOG_LEVEL", level)
		defer os.Unsetenv("LOG_LEVEL")

		cfg, err := Load()
		if err != nil {
			t.Errorf("Load() failed for LOG_LEVEL=%q: %v", level, err)
		}
		if cfg.LogLevel != level {
			t.Errorf("LogLevel = %q, want %q", cfg.LogLevel, level)
		}
	}
}
