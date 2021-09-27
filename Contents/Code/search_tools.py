from datetime import date
import re
# Import internal tools
from logging import Logging

# Setup logger
log = Logging()


class SearchTool:
    def __init__(self, lang, manual, media, results):
        self.lang = lang
        self.manual = manual
        self.media = media
        self.results = results

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
            log.info('Album Title is NULL on an automatic search.  Returning')
            return
        if self.media.album == '[Unknown Album]' and not self.manual:
            log.info(
                'Album Title is [Unknown Album]'
                ' on an automatic search.  Returning'
            )
            return

        if self.manual:
            log.separator(msg="NOTE", log_level="info")
            log.info(
                'You clicked \'fix match\'. '
                'This may have returned no useful results because '
                'it\'s searching using the title of the first track.'
            )
            log.info(
                'There\'s not currently a way around this initial failure. '
                'But clicking \'Search Options\' and '
                'entering the title works just fine.'
            )
            log.info(
                'This message will appear during the initial '
                'search and the actual manual search.'
            )
            # If this is a custom search,
            # use the user-entered name instead of the scanner hint.
            if self.media.name:
                log.info(
                    'Custom album search for: ' + self.media.name
                )
                self.media.album = self.media.name

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
