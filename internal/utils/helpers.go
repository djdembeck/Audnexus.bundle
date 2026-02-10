package utils

import (
	"regexp"
	"strings"
	"time"
	"unicode"

	"golang.org/x/text/transform"
	"golang.org/x/text/unicode/norm"
)

var asinRegex = regexp.MustCompile(`[A-Z0-9]{10}`)

func ExtractASIN(s string) string {
	matches := asinRegex.FindString(s)
	return matches
}

func NormalizeString(s string) string {
	t := transform.Chain(norm.NFD, transform.RemoveFunc(isMn), norm.NFC)
	result, _, _ := transform.String(t, s)
	return strings.ToLower(result)
}

func isMn(r rune) bool {
	return unicode.Is(unicode.Mn, r)
}

func ToInitials(name string) string {
	parts := strings.Fields(name)
	if len(parts) <= 1 {
		return name
	}
	return string(parts[0][0]) + "." + parts[len(parts)-1]
}

func SimplifyTitle(title string) string {
	result := regexp.MustCompile(`\s*\((Unabridged|Abridged)\)`).ReplaceAllString(title, "")
	result = regexp.MustCompile(`,?\s*Book\s+\d+.*$`).ReplaceAllString(result, "")
	result = regexp.MustCompile(`:\s*.+$`).ReplaceAllString(result, "")
	return strings.TrimSpace(result)
}

func SortName(name string) string {
	parts := strings.Fields(name)
	if len(parts) <= 1 {
		return name
	}
	return parts[len(parts)-1] + ", " + strings.Join(parts[:len(parts)-1], " ")
}

func IsPreOrder(releaseDate time.Time) bool {
	return releaseDate.After(time.Now())
}
