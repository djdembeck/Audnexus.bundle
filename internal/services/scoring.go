package services

import (
	"github.com/agnivade/levenshtein"
	"github.com/djdembeck/audnexus-provider/internal/models"
	"github.com/djdembeck/audnexus-provider/internal/utils"
)

const goodScoreThreshold = 98

type ScoreResult struct {
	Result models.Metadata
	Score  int
}

func ScoreAuthor(query string, author models.Author) int {
	normalizedQuery := utils.NormalizeString(query)
	normalizedName := utils.NormalizeString(author.Name)

	if normalizedQuery == normalizedName {
		return 100
	}

	distance := levenshtein.ComputeDistance(normalizedQuery, normalizedName)
	maxLen := len(normalizedQuery)
	if len(normalizedName) > maxLen {
		maxLen = len(normalizedName)
	}

	if maxLen == 0 {
		return 0
	}

	return 100 - (distance * 100 / maxLen)
}

func ScoreBook(queryTitle, queryAuthor string, book models.Book) int {
	normalizedQuery := utils.NormalizeString(queryTitle)
	normalizedTitle := utils.NormalizeString(book.Title)

	titleDistance := levenshtein.ComputeDistance(normalizedQuery, normalizedTitle)
	maxTitleLen := len(normalizedQuery)
	if len(normalizedTitle) > maxTitleLen {
		maxTitleLen = len(normalizedTitle)
	}

	titleScore := 100
	if maxTitleLen > 0 {
		titleScore = 100 - (titleDistance * 100 / maxTitleLen)
	}

	authorBonus := 0
	if queryAuthor != "" && len(book.Authors) > 0 {
		normalizedQueryAuthor := utils.NormalizeString(queryAuthor)
		for _, author := range book.Authors {
			normalizedBookAuthor := utils.NormalizeString(author)
			authorDist := levenshtein.ComputeDistance(normalizedQueryAuthor, normalizedBookAuthor)
			maxAuthorLen := len(normalizedQueryAuthor)
			if len(normalizedBookAuthor) > maxAuthorLen {
				maxAuthorLen = len(normalizedBookAuthor)
			}
			if maxAuthorLen > 0 {
				authorScore := 100 - (authorDist * 100 / maxAuthorLen)
				if authorScore > authorBonus {
					authorBonus = authorScore
				}
			}
		}
		authorBonus = authorBonus / 4
	}

	langBonus := 2

	totalScore := titleScore + authorBonus + langBonus
	if totalScore > 100 {
		totalScore = 100
	}

	return totalScore
}

func IsGoodScore(score int) bool {
	return score >= goodScoreThreshold
}
