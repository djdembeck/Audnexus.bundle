from datetime import date
import re
# Import internal tools
from logging import Logging
import urllib

# Setup logger
log = Logging()

SEARCH_URL = 'https://api.audible.com/1.0/catalog/products'
SEARCH_PARAMS = '?response_groups=contributors,product_desc,product_attrs'


class SearchTool:
    def __init__(self, lang, manual, media, results):
        self.lang = lang
        self.manual = manual
        self.media = media
        self.results = results

    def build_url(self):
        """
            Generates the URL string with search paramaters for API call.
        """
        album_param = '&title=' + urllib.quote(self.normalizedName)
        # Fix match/manual search doesn't provide author
        if self.media.artist:
            artist_param = '&author=' + urllib.quote(self.media.artist)
        else:
            # Use keyword search to supplement missing author
            album_param = '&keywords=' + urllib.quote(self.normalizedName)
            artist_param = ''

        final_url = SEARCH_URL + SEARCH_PARAMS + album_param + artist_param

        return final_url

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

    def parse_api_response(self, api_response):
        """
            Collects keys used for each item from API response, for Plex search results.
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
