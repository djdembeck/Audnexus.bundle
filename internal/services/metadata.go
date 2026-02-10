package services

import (
	"context"

	"github.com/djdembeck/audnexus-provider/internal/api"
	"github.com/djdembeck/audnexus-provider/internal/config"
	"github.com/djdembeck/audnexus-provider/internal/models"
	"github.com/djdembeck/audnexus-provider/internal/utils"
)

// MetadataService handles fetching full metadata for authors and books
type MetadataService struct {
	client *api.Client
	cfg    *config.Config
}

// NewMetadataService creates a new MetadataService
func NewMetadataService(client *api.Client, cfg *config.Config) *MetadataService {
	return &MetadataService{client: client, cfg: cfg}
}

// GetAuthorMetadata fetches full metadata for an author by ASIN
func (s *MetadataService) GetAuthorMetadata(ctx context.Context, asin string) (*models.Metadata, error) {
	author, err := s.client.GetAuthorByASIN(ctx, asin, s.cfg.Region)
	if err != nil {
		return nil, err
	}

	metadata := &models.Metadata{
		RatingKey: "author_" + author.ASIN,
		GUID:      "audnexus://author/" + author.ASIN,
		Type:      "artist",
		Title:     author.Name,
		Summary:   author.Description,
		Thumb:     author.Image,
		Genres:    author.Genres,
		Similar:   author.Similar,
	}

	if s.cfg.SortAuthorByLastName {
		metadata.Title = utils.SortName(author.Name)
	}

	return metadata, nil
}

// GetBookMetadata fetches full metadata for a book by ASIN
func (s *MetadataService) GetBookMetadata(ctx context.Context, asin string) (*models.Metadata, error) {
	book, err := s.client.GetBookByASIN(ctx, asin, s.cfg.Region)
	if err != nil {
		return nil, err
	}

	metadata := &models.Metadata{
		RatingKey: "album_" + book.ASIN,
		GUID:      "audnexus://album/" + book.ASIN,
		Type:      "album",
		Title:     book.Title,
		Summary:   book.Description,
		Year:      book.ReleaseDate.Year(),
		Thumb:     book.Image,
		Rating:    book.Rating,
		Studio:    book.Publisher,
	}

	if s.cfg.SimplifyTitle {
		metadata.Title = utils.SimplifyTitle(book.Title)
	}

	if s.cfg.StoreAuthorAsMood {
		metadata.Moods = book.Authors
	}

	metadata.Styles = book.Narrators

	for _, series := range book.Series {
		metadata.Moods = append(metadata.Moods, "Series:"+series.Name)
	}

	if s.cfg.SortAuthorByLastName && len(book.Authors) > 0 {
		metadata.Moods = []string{utils.SortName(book.Authors[0])}
	}

	return metadata, nil
}
