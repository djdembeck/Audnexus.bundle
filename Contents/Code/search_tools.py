from datetime import date
import re
# Import internal tools
from logging import Logging
from region_tools import RegionTool
import urllib

# Setup logger
log = Logging()

asin_regex = '(?=.\\d)[A-Z\\d]{10}'
region_regex = '(?<=\[)[A-Za-z]{2}(?=\])'


class SearchTool:
    def __init__(self, content_type, lang, manual, media, prefs, results):
        self.content_type = content_type
        self.lang = lang
        self.manual = manual
        self.media = media
        self.prefs = prefs
        self.results = results

    def build_url(self, query):
        """
            Generates the URL string with search paramaters for API call.
        """
        # Pre-process title. If ASIN is found, return the URL
        pre_process = self.pre_process_title()
        if pre_process:
            return pre_process

        # Setup region helper to get search URL
        region_helper = RegionTool(
            content_type=self.content_type, query=query, region=self.region_override)

        search_url = region_helper.get_api_search_url(
        ) if self.content_type == 'books' else region_helper.get_search_url()
        self.log_search_url(search_url)
        return search_url

    def check_for_asin(self):
        """
            Checks filename and search query for ASIN to quick match.
        """
        filename_search_asin = self.search_asin(self.media.filename)
        # Default to album and use artist if no album
        manual_asin = self.media.album if self.media.album else self.media.artist
        manual_search_asin = self.search_asin(manual_asin)

        if filename_search_asin:
            log.info('ASIN found in filename')
            self.check_for_region(self.media.filename)
            return filename_search_asin.group(0) + '_' + self.region_override
        elif manual_search_asin:
            log.info('ASIN found in manual search')
            self.check_for_region(manual_asin)
            return manual_search_asin.group(0) + '_' + self.region_override

    # Check for region override
    def check_for_region(self, search_title):
        """
            Overrides the search with a region.
        """
        match_region = self.search_region(search_title)
        if match_region:
            log.info('Region found in title')
            self.region_override = match_region.group(0)
        else:
            self.region_override = self.prefs['region']
        log.info('Region Override: %s', self.region_override)

    def clear_contributor_text(self, string):
        contributor_regex = '.+?(?= -)'
        if re.match(contributor_regex, string):
            return re.match(contributor_regex, string).group(0)
        return string

    def log_search_url(self, search_url):
        """
            Logs the search URL.
        """
        log.debug('Search URL: %s', search_url)

    def override_with_asin(self, match_asin, region=None):
        """
            Overrides the search with an ASIN.
        """
        log.debug('Overriding' + ' ' + self.content_type +
                  ' ' + 'search with ASIN')
        asin = match_asin.group(0)
        # Param uses keyword for book and nothing for author
        type_param = '&keywords=' if self.content_type == 'books' else ''
        # Wrap the param for url use
        url_param = type_param + urllib.quote(asin)

        # Setup region helper to get search URL
        self.region_override = region if region else self.prefs['region']
        region_helper = RegionTool(
            content_type=self.content_type, query=url_param, region=self.region_override)

        # Books use api search authors use audnexus search
        if self.content_type == 'books':
            search_url = region_helper.get_api_search_url()
        else:
            # Set ID to ASIN
            region_helper.id = asin
            search_url = region_helper.get_id_url()

        self.log_search_url(search_url)
        return search_url

    def pre_process_title(self):
        """
            Pre-processes the title to remove any contributor text.
        """
        log.debug('Pre-processing title')
        # Setup some basic things
        search_title = self.media.album if self.content_type == 'books' else self.media.artist
        asin_search_title = self.media.artist

        # Region override
        self.check_for_region(search_title)

        # Normalize name
        if self.content_type == 'books':
            asin_search_title = self.normalizedName

        # ASIN override
        match_asin = self.search_asin(asin_search_title)
        if match_asin:
            log.debug('ASIN found in title')
            return self.override_with_asin(match_asin, self.region_override)

    def search_asin(self, input):
        """
            Searches for ASIN in a string.
        """
        if input:
            return re.search(asin_regex, urllib.unquote(input).decode('utf8'))

    def search_region(self, input):
        """
            Searches for region in a string.
        """
        if input:
            return re.search(region_regex, urllib.unquote(input).decode('utf8'))

    def validate_author_name(self):
        """
            Checks a list of known bad author names.
            If matched, author name is set to None to prevent
            it being used in search query.
        """
        if self.content_type == 'authors':
            self.get_primary_author()

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


class AlbumSearchTool(SearchTool):
    def build_search_args(self):
        """
            Builds the search arguments for the API call.
        """
        # First, normalize the name
        self.normalize_name()
        # Album title query
        album_param = 'title=' + urllib.quote(self.normalizedName)

        # Fix match/manual search doesn't provide author
        if self.media.artist:
            artist_param = '&author=' + urllib.quote(self.media.artist)
        else:
            # Use keyword search to supplement missing author
            album_param = 'keywords=' + urllib.quote(self.normalizedName)
            artist_param = ''
        # Combine params
        query = (album_param + artist_param)
        return query

    def check_if_preorder(self, book_date):
        """
            Checks if the book is a preorder.
            If so, it is excluded from the search.
        """
        current_date = (date.today())
        if book_date > current_date:
            log.info("Excluding pre-order book")
            return True

    def name_to_initials(self, input_name):
        """
            Converts a name to initials.
            Shorten input_name by splitting on whitespaces
            Only the surname stays as whole, the rest gets truncated
            and merged with dots.
            Example: 'Arthur Conan Doyle' -> 'A.C.Doyle'
            Example: 'J K Rowling' -> 'J.K.Rowling'
            Example: 'J. R. R. Tolkien' -> 'J.R.R.Tolkien'
        """

        # Remove quotation marks
        input_name = input_name.replace('"', '')

        # Split name into parts
        name_parts = self.clear_contributor_text(input_name).split()

        # Check if prename and surname exist, otherwise exit
        if len(name_parts) < 2:
            return input_name

        new_name = ""
        # Truncate prenames
        for part in name_parts[:-1]:
            try:
                # Try to get first letter of prename and add dot
                new_name += part[0] + "." if part[1] != "." else part
            except IndexError:
                # If there is only one letter, add dot and return
                new_name += part + "." if part != "." else part
        # Add surname
        new_name += name_parts[-1]

        return new_name

    def normalize_name(self):
        """
            Normalizes the album name by removing
            unwanted characters and words.
        """
        # Get name from either album or title
        input_name = self.media.album if self.media.album else self.media.title
        log.debug('Input Name: %s', input_name)

        # Remove Diacritics
        name = String.StripDiacritics(input_name)
        # Remove brackets and text inside
        name = re.sub(r'\[[^"]*\]', '', name)
        # Remove unwanted characters
        name = re.sub(r'[^\w\s]', '', name)
        # Remove unwanted words
        name = re.sub(r'\b(official|audiobook|unabridged|abridged)\b',
                      '', name, flags=re.IGNORECASE)
        # Remove unwanted whitespaces
        name = re.sub(r'\s+', ' ', name)
        # Remove leading and trailing whitespaces
        name = name.strip()
        # Set class variable
        self.normalizedName = name
        log.debug('Normalized Name: %s', self.normalizedName)

        return name

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
                        'asin': item['asin'] + '_' + self.region_override,
                        'author': item['authors'],
                        'date': item['release_date'],
                        'language': item['language'],
                        'narrator': item['narrators'],
                        'region': self.region_override,
                        'title': item['title'],
                    }
                )
        return search_results

    def pre_search_logging(self):
        """
            Logs basic metadata before search.
        """
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


class ArtistSearchTool(SearchTool):
    def build_search_args(self):
        """
            Builds the search query for the API.
        """
        modified_artist_name = self.cleanup_author_name(self.media.artist)
        query = 'name=' + urllib.quote(modified_artist_name)
        # Set param
        return query

    def cleanup_author_name(self, name):
        """
            Cleans up the author name by removing
            unwanted characters and words.
        """
        log.debug('Artist name before cleanup: ' + name)

        # Remove brackets and text inside
        name = re.sub(r'\[[^"]*\]', '', name)
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

    def find_non_contributor(self, author_array):
        """
            Finds the first author in the list
            that is not a contributor.
        """
        # Go through list of artists until we find a non contributor
        for i, r in enumerate(author_array):
            if self.clear_contributor_text(r) != r:
                log.debug('Author #' + str(i+1) + ' is a contributor')
                # If all authors are contributors use the first
                if i == len(author_array) - 1:
                    log.debug(
                        'All authors are contributors, using the first one'
                    )
                    self.media.artist = self.clear_contributor_text(
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

    def handle_multi_artist(self):
        """
            Handles multi-artist lists.
        """
        author_array = self.media.artist.split(', ')
        if len(author_array) > 1:
            self.find_non_contributor(author_array)
        else:
            if (
                self.clear_contributor_text(self.media.artist)
                !=
                self.media.artist
            ):
                log.debug('Stripped contributor tag from author')
                self.media.artist = self.clear_contributor_text(
                    self.media.artist
                )

    def get_primary_author(self):
        """
            Checks for combined authors
            If matched, author name is set to None to prevent
            it being used in search query.
        """
        self.set_media_artist()

        # We need an author name to continue
        if not self.media.artist:
            return

        # Handle multi-artist
        self.handle_multi_artist()

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

    def set_media_artist(self):
        """
            Sometimes artist isn't set but title is.
        """
        if self.media.title:
            self.media.artist = self.media.title
        else:
            log.error("No artist to validate")


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
        """
            Reduces a string to lowercase and removes
            punctuation and spaces.
        """
        normalized = string \
            .lower() \
            .replace('-', '') \
            .replace(' ', '') \
            .replace('.', '') \
            .replace(',', '')
        return normalized

    def run_score_author(self):
        """
            Scores an author result.
        """
        self.asin = self.result_dict['asin']
        self.author = self.result_dict['name']
        self.authors_concat = self.author
        self.date = None
        self.language = None
        self.narrator = None
        self.region = None
        self.title = None
        return self.score_result()

    def run_score_book(self):
        """
            Scores a book result.
        """
        self.asin = self.result_dict['asin']
        self.authors_concat = ', '.join(
            author['name'] for author in self.result_dict['author']
        )
        self.author = self.result_dict['author'][0]['name']
        self.date = self.result_dict['date']
        self.language = self.result_dict['language'].title()
        self.narrator = self.result_dict['narrator'][0]['name']
        self.region = self.result_dict['region']
        self.title = self.result_dict['title']
        return self.score_result()

    def sum_scores(self, numberlist):
        """
            Sums a list of numbers.
        """
        # Because builtin sum() isn't available
        return reduce(
            lambda x, y: x + y, numberlist, 0
        )

    def score_create_result(self, score):
        """
            Creates a result dict for the score.
            Logs the score and the data used to calculate it.
        """
        data_to_log = []
        plex_score_dict = {}

        # Go through all the keys for the result and log as we go
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
        if self.region:
            plex_score_dict['region'] = self.region
            data_to_log.append({'Region is': self.region})
        if score:
            plex_score_dict['score'] = score
            data_to_log.append({'Score is': str(score)})
        if self.title:
            plex_score_dict['title'] = self.title
            data_to_log.append({'Title is': self.title})
        if self.year:
            plex_score_dict['year'] = self.year

        log.metadata(data_to_log, log_level="info")
        return plex_score_dict

    def score_result(self):
        """
            Scores a result.
        """
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

        # Create result dict
        plex_score_dict = self.score_create_result(score)

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
            scorebase4 = author
            author_score = self.calculate_score(
                self.reduce_string(scorebase3),
                self.reduce_string(scorebase4)
            ) * 10
            log.debug("Score deduction from author: " + str(author_score))
            return author_score

        log.warn('No artist found in file metadata')
        return 20

    def score_language(self, language):
        """
            Compare the library language to search results
            and knock off 2 points if they don't match.
        """
        lang_dict = {
            self.english_locale: 'English',
            'de': 'Deutsch',
            'es': 'Español',
            'fr': 'Français',
            'it': 'Italiano',
            'jp': '日本語',
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
