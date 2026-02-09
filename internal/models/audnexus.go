package models

import "time"

// Author represents an author from Audnexus API
type Author struct {
	ASIN        string   `json:"asin"`
	Name        string   `json:"name"`
	Description string   `json:"description"`
	Image       string   `json:"image"`
	Genres      []string `json:"genres"`
	Similar     []string `json:"similar"`
	Region      string   `json:"region"`
}

// Book represents a book from Audnexus API
type Book struct {
	ASIN        string    `json:"asin"`
	Title       string    `json:"title"`
	Subtitle    string    `json:"subtitle"`
	Description string    `json:"description"`
	Image       string    `json:"image"`
	Rating      float64   `json:"rating"`
	RatingCount int       `json:"ratingCount"`
	ReleaseDate time.Time `json:"releaseDate"`
	Region      string    `json:"region"`
	Publisher   string    `json:"publisher"`
	Authors     []string  `json:"authors"`
	Narrators   []string  `json:"narrators"`
	Series      []Series  `json:"series"`
	Genres      []string  `json:"genres"`
}

// Series represents a series from Audnexus API
type Series struct {
	ASIN     string `json:"asin"`
	Name     string `json:"name"`
	Position string `json:"position"`
}
