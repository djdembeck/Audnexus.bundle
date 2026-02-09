package api

import (
	"context"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"net/url"
	"testing"
	"time"

	"github.com/djdembeck/audnexus-provider/internal/models"
)

func TestNewClient(t *testing.T) {
	client := NewClient(30)
	if client == nil {
		t.Fatal("expected non-nil client")
	}
	if client.timeout != 30*time.Second {
		t.Errorf("expected timeout of 30s, got %v", client.timeout)
	}
}

func TestSearchAuthors(t *testing.T) {
	expectedAuthors := []models.Author{
		{
			ASIN:        "B0000001",
			Name:        "Test Author",
			Description: "A test author",
			Image:       "https://example.com/image.jpg",
			Genres:      []string{"Fiction"},
			Similar:     []string{"B0000002"},
			Region:      "us",
		},
	}

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/authors" {
			t.Errorf("expected path /authors, got %s", r.URL.Path)
		}
		if r.URL.Query().Get("name") != "Test Author" {
			t.Errorf("expected name=Test Author, got %s", r.URL.Query().Get("name"))
		}
		if r.URL.Query().Get("region") != "us" {
			t.Errorf("expected region=us, got %s", r.URL.Query().Get("region"))
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(expectedAuthors)
	}))
	defer server.Close()

	client := NewClientWithBaseURL(30, server.URL)

	ctx := context.Background()
	params := url.Values{
		"name":   {"Test Author"},
		"region": {"us"},
	}

	body, err := client.doRequest(ctx, "GET", "/authors", params)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var authors []models.Author
	if err := json.Unmarshal(body, &authors); err != nil {
		t.Fatalf("failed to unmarshal: %v", err)
	}

	if len(authors) != 1 {
		t.Errorf("expected 1 author, got %d", len(authors))
	}
	if authors[0].ASIN != "B0000001" {
		t.Errorf("expected ASIN B0000001, got %s", authors[0].ASIN)
	}
}

func TestSearchBooks(t *testing.T) {
	expectedBooks := []models.Book{
		{
			ASIN:        "B0000001",
			Title:       "Test Book",
			Subtitle:    "A Test Subtitle",
			Description: "A test book",
			Image:       "https://example.com/cover.jpg",
			Rating:      4.5,
			RatingCount: 100,
			ReleaseDate: time.Date(2024, 1, 1, 0, 0, 0, 0, time.UTC),
			Region:      "us",
			Publisher:   "Test Publisher",
			Authors:     []string{"Test Author"},
			Narrators:   []string{"Test Narrator"},
			Series:      []models.Series{{ASIN: "S0001", Name: "Test Series", Position: "1"}},
			Genres:      []string{"Fiction"},
		},
	}

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/books" {
			t.Errorf("expected path /books, got %s", r.URL.Path)
		}
		if r.URL.Query().Get("title") != "Test Book" {
			t.Errorf("expected title=Test Book, got %s", r.URL.Query().Get("title"))
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(expectedBooks)
	}))
	defer server.Close()

	client := NewClientWithBaseURL(30, server.URL)
	ctx := context.Background()
	params := url.Values{
		"title":  {"Test Book"},
		"region": {"us"},
	}

	body, err := client.doRequest(ctx, "GET", "/books", params)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var books []models.Book
	if err := json.Unmarshal(body, &books); err != nil {
		t.Fatalf("failed to unmarshal: %v", err)
	}

	if len(books) != 1 {
		t.Errorf("expected 1 book, got %d", len(books))
	}
	if books[0].ASIN != "B0000001" {
		t.Errorf("expected ASIN B0000001, got %s", books[0].ASIN)
	}
}

func TestGetAuthorByASIN(t *testing.T) {
	expectedAuthor := models.Author{
		ASIN:        "B0000001",
		Name:        "Test Author",
		Description: "A test author",
		Image:       "https://example.com/image.jpg",
		Genres:      []string{"Fiction"},
		Similar:     []string{"B0000002"},
		Region:      "us",
	}

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/authors/B0000001" {
			t.Errorf("expected path /authors/B0000001, got %s", r.URL.Path)
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(expectedAuthor)
	}))
	defer server.Close()

	client := NewClientWithBaseURL(30, server.URL)
	ctx := context.Background()
	params := url.Values{"region": {"us"}}

	body, err := client.doRequest(ctx, "GET", "/authors/B0000001", params)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var author models.Author
	if err := json.Unmarshal(body, &author); err != nil {
		t.Fatalf("failed to unmarshal: %v", err)
	}

	if author.ASIN != "B0000001" {
		t.Errorf("expected ASIN B0000001, got %s", author.ASIN)
	}
}

func TestGetBookByASIN(t *testing.T) {
	expectedBook := models.Book{
		ASIN:        "B0000001",
		Title:       "Test Book",
		Description: "A test book",
		Region:      "us",
	}

	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/books/B0000001" {
			t.Errorf("expected path /books/B0000001, got %s", r.URL.Path)
		}

		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(expectedBook)
	}))
	defer server.Close()

	client := NewClientWithBaseURL(30, server.URL)
	ctx := context.Background()
	params := url.Values{"region": {"us"}}

	body, err := client.doRequest(ctx, "GET", "/books/B0000001", params)
	if err != nil {
		t.Fatalf("unexpected error: %v", err)
	}

	var book models.Book
	if err := json.Unmarshal(body, &book); err != nil {
		t.Fatalf("failed to unmarshal: %v", err)
	}

	if book.ASIN != "B0000001" {
		t.Errorf("expected ASIN B0000001, got %s", book.ASIN)
	}
}

func TestClientErrorHandling(t *testing.T) {
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusBadRequest)
		w.Write([]byte(`{"error": "invalid request"}`))
	}))
	defer server.Close()

	client := NewClientWithBaseURL(30, server.URL)
	ctx := context.Background()
	params := url.Values{"name": {"test"}}

	_, err := client.doRequest(ctx, "GET", "/authors", params)
	if err == nil {
		t.Error("expected error for 400 status code")
	}
}

func TestServerErrorRetries(t *testing.T) {
	attempts := 0
	server := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		attempts++
		w.WriteHeader(http.StatusInternalServerError)
	}))
	defer server.Close()

	client := NewClientWithBaseURL(30, server.URL)
	ctx := context.Background()
	params := url.Values{"name": {"test"}}

	_, err := client.doRequest(ctx, "GET", "/authors", params)
	if err == nil {
		t.Error("expected error after retries")
	}
	if attempts != maxRetries {
		t.Errorf("expected %d attempts, got %d", maxRetries, attempts)
	}
}
