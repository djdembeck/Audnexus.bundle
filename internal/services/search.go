package services

import (
	"context"
	"sort"

	"github.com/djdembeck/audnexus-provider/internal/api"
	"github.com/djdembeck/audnexus-provider/internal/config"
	"github.com/djdembeck/audnexus-provider/internal/models"
	"github.com/djdembeck/audnexus-provider/internal/utils"
)

type SearchService struct {
	client *api.Client
	cfg    *config.Config
}

func NewSearchService(client *api.Client, cfg *config.Config) *SearchService {
	return &SearchService{client: client, cfg: cfg}
}

func (s *SearchService) SearchAuthors(ctx context.Context, query string) ([]ScoreResult, error) {
	// ASIN quick match
	if asin := utils.ExtractASIN(query); asin != "" {
		author, err := s.client.GetAuthorByASIN(ctx, asin, s.cfg.Region)
		if err == nil {
			return []ScoreResult{{
				Result: models.Metadata{
					RatingKey: "author_" + author.ASIN,
					GUID:      "audnexus://author/" + author.ASIN,
					Type:      "artist",
					Title:     author.Name,
				},
				Score: 100,
			}}, nil
		}
	}

	authors, err := s.client.SearchAuthors(ctx, query, s.cfg.Region)
	if err != nil {
		return nil, err
	}

	var results []ScoreResult
	for _, author := range authors {
		score := ScoreAuthor(query, author)
		results = append(results, ScoreResult{
			Result: models.Metadata{
				RatingKey: "author_" + author.ASIN,
				GUID:      "audnexus://author/" + author.ASIN,
				Type:      "artist",
				Title:     author.Name,
			},
			Score: score,
		})
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].Score > results[j].Score
	})

	return results, nil
}

func (s *SearchService) SearchBooks(ctx context.Context, title, author string) ([]ScoreResult, error) {
	// ASIN quick match
	if asin := utils.ExtractASIN(title); asin != "" {
		book, err := s.client.GetBookByASIN(ctx, asin, s.cfg.Region)
		if err == nil {
			return []ScoreResult{{Result: s.bookToMetadata(*book), Score: 100}}, nil
		}
	}

	books, err := s.client.SearchBooks(ctx, title, s.cfg.Region)
	if err != nil {
		return nil, err
	}

	var results []ScoreResult
	for i, book := range books {
		if utils.IsPreOrder(book.ReleaseDate) {
			continue
		}

		score := ScoreBook(title, author, book)
		score -= i // Position penalty
		if score < 0 {
			score = 0
		}

		results = append(results, ScoreResult{
			Result: s.bookToMetadata(book),
			Score:  score,
		})
	}

	sort.Slice(results, func(i, j int) bool {
		return results[i].Score > results[j].Score
	})

	return results, nil
}

func (s *SearchService) bookToMetadata(book models.Book) models.Metadata {
	metadata := models.Metadata{
		RatingKey: "album_" + book.ASIN,
		GUID:      "audnexus://album/" + book.ASIN,
		Type:      "album",
		Title:     book.Title,
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

	return metadata
}
