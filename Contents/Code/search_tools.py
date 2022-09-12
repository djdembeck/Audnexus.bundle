from datetime import date
import re
# Import internal tools
from logging import Logging
import urllib

# Setup logger
log = Logging()

asin_regex = '(?=.\\d)[A-Z\\d]{10}'


class AlbumSearchTool:
    SEARCH_URL = 'https://api.audible.com/1.0/catalog/products'
    SEARCH_PARAMS = (
        '?response_groups=contributors,product_desc,product_attrs'
        '&num_results=25&products_sort_by=Relevance'
    )

    def __init__(self, lang, manual, media, results):
        self.lang = lang
        self.manual = manual
        self.media = media
        self.results = results

    def build_url(self):
        """
            Generates the URL string with search paramaters for API call.
        """
        # If search is an ASIN, use that
        match_asin = search_asin(self.normalizedName)
        if match_asin:
            log.debug('Overriding album search with ASIN')
            album_param = '&keywords=' + urllib.quote(match_asin.group(0))
            final_url = (
                self.SEARCH_URL + self.SEARCH_PARAMS + album_param
            )
            return final_url

        album_param = '&title=' + urllib.quote(self.normalizedName)
        # Fix match/manual search doesn't provide author
        if self.media.artist:
            artist_param = '&author=' + urllib.quote(self.media.artist)
        else:
            # Use keyword search to supplement missing author
            album_param = '&keywords=' + urllib.quote(self.normalizedName)
            artist_param = ''

        final_url = (
            self.SEARCH_URL + self.SEARCH_PARAMS + album_param + artist_param
        )

        return final_url

    def check_for_asin(self):
        """
            Checks filename and search query for ASIN to quick match.
        """
        filename_search_asin = search_asin(self.media.filename)
        manual_search_asin = search_asin(self.media.album)
        if filename_search_asin:
            return filename_search_asin.group(0)
        elif manual_search_asin:
            return manual_search_asin.group(0)

    def check_if_preorder(self, book_date):
        current_date = (date.today())
        if book_date > current_date:
            log.info("Excluding pre-order book")
            return True

    def get_id_from_url(self, item):
        url = item['url']
        log.debug('URL For Breakdown: %s', url)

        # Find ASIN before ? in URL
        asin = re.search(r'[0-9A-Z]{9}.+?(?=\?)', url).group(0)
        if asin:
            return asin

        log.warn('No Match: %s', url)
        return None

    def name_to_initials(self, input_name):
        # Shorten input_name by splitting on whitespaces
        # Only the surname stays as whole, the rest gets truncated
        # and merged with dots.
        # Example: 'Arthur Conan Doyle' -> 'A.C.Doyle'
        name_parts = clear_contributor_text(input_name).split()

        # Check if prename and surname exist, otherwise exit
        if len(name_parts) < 2:
            return input_name

        new_name = ""
        # Truncate prenames
        for part in name_parts[:-1]:
            new_name += part[0] + "." if part[1] != "." else part
        # Add surname
        new_name += name_parts[-1]

        return new_name

    def parse_api_response(self, api_response):
        """
            Collects keys used for each item from API response,
            for Plex search results.
        """
        search_results = []
        for item in api_response['products']:
            # Only append results which have valid keys
            if item.viewkeys() >= {
                "asin",
                "authors",
                "language",
                "narrators",
                "release_date",
                "title"
            }:
                search_results.append(
                    {
                        'asin': item['asin'],
                        'author': item['authors'],
                        'date': item['release_date'],
                        'language': item['language'],
                        'narrator': item['narrators'],
                        'title': item['title'],
                    }
                )
        return search_results

    def pre_search_logging(self):
        log.separator(msg='ALBUM SEARCH', log_level="info")
        # Log basic metadata
        data_to_log = [
            {'ID': self.media.parent_metadata.id},
            {'Title': self.media.title},
            {'Name': self.media.name},
            {'Album': self.media.album},
            {'Artist': self.media.artist},
        ]
        log.metadata(data_to_log)
        log.separator(log_level="info")

        # Handle a couple of edge cases where
        # album search will give bad results.
        if self.media.album is None and not self.manual:
            if self.media.title:
                log.warn('Using track title since album title is missing.')
                self.media.album = self.media.title
                return True
            log.info('Album Title is NULL on an automatic search.  Returning')
            return None
        if self.media.album == '[Unknown Album]' and not self.manual:
            log.info(
                'Album Title is [Unknown Album]'
                ' on an automatic search.  Returning'
            )
            return None

        if self.manual:
            # If this is a custom search,
            # use the user-entered name instead of the scanner hint.
            if self.media.name:
                log.info(
                    'Custom album search for: ' + self.media.name
                )
                self.media.album = self.media.name
        return True

    def strip_title(self, normalizedName):
        if not normalizedName:
            normalizedName = self.media.album
        log.debug(
            'normalizedName = %s', normalizedName
        )

        # Chop off "unabridged"
        normalizedName = re.sub(
            r"[\(\[].*?[\)\]]", "", normalizedName
        )
        log.debug(
            'chopping bracketed text = %s', normalizedName
        )
        normalizedName = normalizedName.strip()
        log.debug(
            'normalizedName stripped = %s', normalizedName
        )

        log.separator(
            msg=(
                "SEARCHING FOR " + '"' + normalizedName + '"'
            ),
            log_level="info"
        )
        # Give access of this variable to the class
        self.normalizedName = normalizedName

    def validate_author_name(self):
        """
            Checks a list of known bad author names.
            If matched, author name is set to None to prevent
            it being used in search query.
        """
        strings_to_check = [
            "[Unknown Artist]"
        ]
        for test_name in strings_to_check:
            if self.media.artist == test_name:
                self.media.artist = None
                log.info(
                    "Artist name seems to be bad, "
                    "not using it in search."
                )
                break


class ArtistSearchTool:
    SEARCH_URL = 'https://api.audnex.us/authors'

    def __init__(self, lang, manual, media, results):
        self.lang = lang
        self.manual = manual
        self.media = media
        self.results = results

    def build_url(self):
        """
            Generates the URL string with search paramaters for API call.
        """
        # If search is an ASIN, use that
        match_asin = search_asin(self.media.artist)
        if match_asin:
            log.debug('Overriding author search with ASIN')
            aritst_param = '' + urllib.quote(match_asin.group(0))
            final_url = (
                self.SEARCH_URL + '/' + aritst_param
            )
            return final_url

        modified_artist_name = self.cleanup_author_name(self.media.artist)
        artist_param = '?name=' + urllib.quote(modified_artist_name)

        final_url = (
            self.SEARCH_URL + artist_param
        )

        return final_url

    def cleanup_author_name(self, name):
        log.debug('Artist name before cleanup: ' + name)
        # Remove certain strings, such as titles
        str_to_remove = [
            'Dr.',
            'EdD',
            'Prof.',
            'Professor',
        ]
        str_to_remove_regex = re.compile(
            '|'.join(map(re.escape, str_to_remove))
        )
        name = str_to_remove_regex.sub('', name)
        # Remove periods between double initials
        initials_regex = "^((?:[A-Z]\.\s?)*[A-Z]\.(?!\S)).(\w+)"
        initials_matched = re.search(initials_regex, name)
        if initials_matched:
            log.debug('Found initials to clean')
            cleaned_initials = (
                initials_matched.group(1)
                .replace(' ', '')
                .replace('.', ' ')
            )
            name = cleaned_initials + ' ' + initials_matched.group(2)

        log.debug('Artist name after cleanup: ' + name)
        return name

    def parse_api_response(self, api_response):
        """
            Collects keys used for each item from API response,
            for Plex search results.
        """
        search_results = []
        for item in api_response:
            # Only append results which have valid keys
            if item.viewkeys() >= {
                "asin",
                "name",
            }:
                search_results.append(
                    {
                        'asin': item['asin'],
                        'name': item['name'],
                    }
                )
        return search_results

    def validate_author_name(self):
        """
            Checks for combined authors and a list of known bad author names.
            If matched, author name is set to None to prevent
            it being used in search query.
        """
        # Sometimes artist isn't set but title is
        if not self.media.artist:
            if self.media.title:
                self.media.artist = self.media.title
            else:
                log.error("No artist to validate")
                return

        author_array = self.media.artist.split(', ')
        # Handle multi-artist
        if len(author_array) > 1:
            # Go through list of artists until we find a non contributor
            for i, r in enumerate(author_array):
                if clear_contributor_text(r) != r:
                    log.debug('Author #' + str(i+1) + ' is a contributor')
                    # If all authors are contributors use the first
                    if i == len(author_array) - 1:
                        log.debug(
                            'All authors are contributors, using the first one'
                        )
                        self.media.artist = clear_contributor_text(
                            author_array[0]
                        )
                        return
                    continue
                log.info(
                    'Merging multi-author "' +
                    self.media.artist +
                    '" into top-level author "' +
                    r + '"'
                )
                self.media.artist = r
                return
        else:
            if (
                clear_contributor_text(self.media.artist)
                !=
                self.media.artist
            ):
                log.debug('Stripped contributor tag from author')
                self.media.artist = clear_contributor_text(
                    self.media.artist
                )

        strings_to_check = [
            "[Unknown Artist]"
        ]
        for test_name in strings_to_check:
            if self.media.artist == test_name:
                self.media.artist = None
                log.info(
                    "Artist name seems to be bad, "
                    "not using it in search."
                )
                break


class ScoreTool:
    # Starting value for score before deductions are taken.
    INITIAL_SCORE = 100
    # Any score lower than this will be ignored.
    IGNORE_SCORE = 45

    def __init__(
        self,
        helper,
        index,
        info,
        locale,
        levenshtein_distance,
        result_dict,
        year=None
    ):
        self.calculate_score = levenshtein_distance
        self.helper = helper
        self.index = index
        self.info = info
        self.english_locale = locale
        self.result_dict = result_dict
        self.year = year

    def reduce_string(self, string):
        normalized = string \
            .lower() \
            .replace('-', '') \
            .replace(' ', '') \
            .replace('.', '') \
            .replace(',', '')
        return normalized

    def run_score_author(self):
        self.asin = self.result_dict['asin']
        self.author = self.result_dict['name']
        self.authors_concat = self.author
        self.date = None
        self.language = None
        self.narrator = None
        self.title = None
        return self.score_result()

    def run_score_book(self):
        self.asin = self.result_dict['asin']
        self.authors_concat = ', '.join(
            author['name'] for author in self.result_dict['author']
        )
        self.author = self.result_dict['author'][0]['name']
        self.date = self.result_dict['date']
        self.language = self.result_dict['language'].title()
        self.narrator = self.result_dict['narrator'][0]['name']
        self.title = self.result_dict['title']
        return self.score_result()

    def sum_scores(self, numberlist):
        # Because builtin sum() isn't available
        return reduce(
            lambda x, y: x + y, numberlist, 0
        )

    def score_result(self):
        # Array to hold score points for processing
        all_scores = []

        # Album name score
        if self.title:
            title_score = self.score_album(self.title)
            if title_score:
                all_scores.append(title_score)
        # Author name score
        if self.authors_concat:
            author_score = self.score_author(self.authors_concat)
            if author_score:
                all_scores.append(author_score)
        # Library language score
        if self.language:
            lang_score = self.score_language(self.language)
            if lang_score:
                all_scores.append(lang_score)

        # Subtract difference from initial score
        # Subtract index to use Audible relevance as weight
        score = self.INITIAL_SCORE - self.sum_scores(all_scores) - self.index

        log.info("Result #" + str(self.index + 1))
        # Log basic metadata
        data_to_log = []
        plex_score_dict = {}
        if self.asin:
            plex_score_dict['id'] = self.asin
            data_to_log.append({'ASIN is': self.asin})
        if self.author:
            plex_score_dict['author'] = self.author
            data_to_log.append({'Author is': self.author})
        if self.date:
            plex_score_dict['date'] = self.date
            data_to_log.append({'Date is': self.date})
        if self.narrator:
            plex_score_dict['narrator'] = self.narrator
            data_to_log.append({'Narrator is': self.narrator})
        if score:
            plex_score_dict['score'] = score
            data_to_log.append({'Score is': str(score)})
        if self.title:
            plex_score_dict['title'] = self.title
            data_to_log.append({'Title is': self.title})
        if self.year:
            plex_score_dict['year'] = self.year

        log.metadata(data_to_log, log_level="info")

        if score >= self.IGNORE_SCORE:
            self.info.append(plex_score_dict)
        else:
            log.info(
                '# Score is below ignore boundary (%s)... Skipping!',
                self.IGNORE_SCORE
            )

    def score_album(self, title):
        """
            Compare the input album similarity to the search result album.
            Score is calculated with LevenshteinDistance
        """
        scorebase1 = self.helper.media.album
        if not scorebase1:
            log.error('No album title found in file metadata')
            return 50
        scorebase2 = title.encode('utf-8')
        album_score = self.calculate_score(
            self.reduce_string(scorebase1),
            self.reduce_string(scorebase2)
        ) * 2
        log.debug("Score deduction from album: " + str(album_score))
        return album_score

    def score_author(self, author):
        """
            Compare the input author similarity to the search result author.
            Score is calculated with LevenshteinDistance
        """
        if self.helper.media.artist:
            scorebase3 = self.helper.media.artist
            if not scorebase3:
                log.warn('No artist found in file metadata')
                return 20
            scorebase4 = author
            author_score = self.calculate_score(
                self.reduce_string(scorebase3),
                self.reduce_string(scorebase4)
            ) * 10
            log.debug("Score deduction from author: " + str(author_score))
            return author_score

    def score_language(self, language):
        """
            Compare the library language to search results
            and knock off 2 points if they don't match.
        """
        lang_dict = {
            self.english_locale: 'English',
            'de': 'Deutsch',
            'fr': 'Français',
            'it': 'Italiano'
        }

        if language != lang_dict[self.helper.lang]:
            log.debug(
                'Audible language: %s; Library language: %s',
                language,
                lang_dict[self.helper.lang]
            )
            log.debug("Book is not library language, deduct 2 points")
            return 2
        return 0


# Shared functions
def clear_contributor_text(string):
    contributor_regex = '.+?(?= -)'
    if re.match(contributor_regex, string):
        return re.match(contributor_regex, string).group(0)
    return string


def search_asin(input):
    if input:
        return re.search(asin_regex, input)
