package api

import (
	"context"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"net/url"
	"time"

	"github.com/djdembeck/audnexus-provider/internal/models"
)

const (
	defaultBaseURL = "https://api.audnex.us"
	userAgent      = "audnexus-provider/1.0.0"
	maxRetries     = 4
)

// Client wraps an HTTP client for the Audnexus API
type Client struct {
	httpClient *http.Client
	timeout    time.Duration
	baseURL    string
}

// NewClient creates a new Audnexus API client
func NewClient(timeout int) *Client {
	return NewClientWithBaseURL(timeout, defaultBaseURL)
}

// NewClientWithBaseURL creates a new Audnexus API client with a custom baseURL (useful for testing)
func NewClientWithBaseURL(timeout int, baseURL string) *Client {
	return &Client{
		httpClient: &http.Client{
			Timeout: time.Duration(timeout) * time.Second,
		},
		timeout: time.Duration(timeout) * time.Second,
		baseURL: baseURL,
	}
}

// doRequest performs an HTTP request with retry logic and exponential backoff
func (c *Client) doRequest(ctx context.Context, method, endpoint string, params url.Values) ([]byte, error) {
	var lastErr error

	for attempt := 0; attempt < maxRetries; attempt++ {
		if attempt > 0 {
			backoff := time.Duration(1<<uint(attempt-1)) * time.Second
			time.Sleep(backoff)
		}

		reqURL := fmt.Sprintf("%s%s", c.baseURL, endpoint)
		if params != nil {
			reqURL = fmt.Sprintf("%s?%s", reqURL, params.Encode())
		}

		req, err := http.NewRequestWithContext(ctx, method, reqURL, nil)
		if err != nil {
			return nil, fmt.Errorf("failed to create request: %w", err)
		}

		req.Header.Set("User-Agent", userAgent)
		req.Header.Set("Accept", "application/json")

		resp, err := c.httpClient.Do(req)
		if err != nil {
			lastErr = err
			continue
		}
		defer resp.Body.Close()

		body, err := io.ReadAll(resp.Body)
		if err != nil {
			lastErr = err
			continue
		}

		if resp.StatusCode >= 400 {
			lastErr = fmt.Errorf("API error: %d - %s", resp.StatusCode, string(body))
			if resp.StatusCode >= 500 {
				continue
			}
			return nil, lastErr
		}

		return body, nil
	}

	return nil, fmt.Errorf("max retries exceeded: %w", lastErr)
}

// SearchAuthors searches for authors by name
func (c *Client) SearchAuthors(ctx context.Context, name, region string) ([]models.Author, error) {
	params := url.Values{
		"name":   {name},
		"region": {region},
	}

	body, err := c.doRequest(ctx, "GET", "/authors", params)
	if err != nil {
		return nil, err
	}

	var authors []models.Author
	if err := json.Unmarshal(body, &authors); err != nil {
		return nil, fmt.Errorf("failed to unmarshal authors: %w", err)
	}

	return authors, nil
}

// SearchBooks searches for books by title
func (c *Client) SearchBooks(ctx context.Context, title, region string) ([]models.Book, error) {
	params := url.Values{
		"title":  {title},
		"region": {region},
	}

	body, err := c.doRequest(ctx, "GET", "/books", params)
	if err != nil {
		return nil, err
	}

	var books []models.Book
	if err := json.Unmarshal(body, &books); err != nil {
		return nil, fmt.Errorf("failed to unmarshal books: %w", err)
	}

	return books, nil
}

// GetAuthorByASIN retrieves an author by ASIN
func (c *Client) GetAuthorByASIN(ctx context.Context, asin, region string) (*models.Author, error) {
	params := url.Values{
		"region": {region},
	}

	body, err := c.doRequest(ctx, "GET", fmt.Sprintf("/authors/%s", asin), params)
	if err != nil {
		return nil, err
	}

	var author models.Author
	if err := json.Unmarshal(body, &author); err != nil {
		return nil, fmt.Errorf("failed to unmarshal author: %w", err)
	}

	return &author, nil
}

// GetBookByASIN retrieves a book by ASIN
func (c *Client) GetBookByASIN(ctx context.Context, asin, region string) (*models.Book, error) {
	params := url.Values{
		"region": {region},
	}

	body, err := c.doRequest(ctx, "GET", fmt.Sprintf("/books/%s", asin), params)
	if err != nil {
		return nil, err
	}

	var book models.Book
	if err := json.Unmarshal(body, &book); err != nil {
		return nil, fmt.Errorf("failed to unmarshal book: %w", err)
	}

	return &book, nil
}

// GetAuthorByID retrieves an author by ID (alias for GetAuthorByASIN)
func (c *Client) GetAuthorByID(ctx context.Context, id, region string) (*models.Author, error) {
	return c.GetAuthorByASIN(ctx, id, region)
}

// GetBookByID retrieves a book by ID (alias for GetBookByASIN)
func (c *Client) GetBookByID(ctx context.Context, id, region string) (*models.Book, error) {
	return c.GetBookByASIN(ctx, id, region)
}
