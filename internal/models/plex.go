package models

// MediaProvider represents Plex provider capabilities
type MediaProvider struct {
	Identifier string    `json:"identifier"`
	Title      string    `json:"title"`
	Types      []string  `json:"types"`
	Features   []Feature `json:"features"`
}

type Feature struct {
	Type    string `json:"type"`
	Name    string `json:"name"`
	Enabled bool   `json:"enabled"`
}

// MediaContainer is the Plex response wrapper
type MediaContainer struct {
	Identifier string     `json:"identifier,omitempty"`
	Size       int        `json:"size"`
	MediaType  string     `json:"mediaType,omitempty"`
	Metadata   []Metadata `json:"Metadata,omitempty"`
}

type Metadata struct {
	RatingKey string   `json:"ratingKey"`
	GUID      string   `json:"guid"`
	Type      string   `json:"type"`
	Title     string   `json:"title"`
	Summary   string   `json:"summary,omitempty"`
	Year      int      `json:"year,omitempty"`
	Thumb     string   `json:"thumb,omitempty"`
	Rating    float64  `json:"rating,omitempty"`
	Genres    []string `json:"Genre,omitempty"`
	Moods     []string `json:"Mood,omitempty"`
	Styles    []string `json:"Style,omitempty"`
	Studio    string   `json:"studio,omitempty"`
	Similar   []string `json:"Similar,omitempty"`
}
