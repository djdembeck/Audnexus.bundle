# Import internal tools
from logging import Logging
from region_tools import RegionTool
import re

# Setup logger
log = Logging()


class UpdateTool:
    def __init__(self, content_type, force, lang, media, metadata, prefs):
        self.content_type = content_type
        self.force = force
        self.lang = lang
        self.media = media
        self.metadata = metadata
        self.prefs = prefs
        self.region = self.extract_region_from_id()

    def build_url(self):
        """
            Builds the URL for the API request.
        """
        # Get the current region
        self.region_override = self.region if self.region else self.prefs['region']
        # Set the region helper
        region_helper = RegionTool(
            region=self.region_override, content_type=self.content_type, id=self.extract_asin_from_id())

        update_url = region_helper.get_id_url()
        log.debug('Update URL: ' + update_url)
        return update_url

    def collect_metadata_to_log(self):
        # Start an array with common metadata
        data_to_log = [{'ASIN': self.metadata.id}]

        # Book metadata
        book_data_to_log = [
            {'Book poster URL': self.thumb},
            {'Book publisher': self.metadata.studio},
            {'Book release date': str(self.metadata.originally_available_at)},
            {'Book sort title': self.metadata.title_sort},
            {'Book summary': self.metadata.summary},
            {'Book title': self.metadata.title},
        ]

        # Author metadata
        author_data_to_log = [
            {'Author bio': self.metadata.summary},
            {'Author name': self.metadata.title},
            {'Author poster URL': self.thumb},
            {'Author sort name': self.metadata.title_sort},
        ]

        # Determine which metadata to log
        if self.content_type == 'book':
            data_to_log.extend(book_data_to_log)
        elif self.content_type == 'author':
            data_to_log.extend(author_data_to_log)

        return data_to_log

    def collect_metadata_arrs_to_log(self):
        # Start an array with common metadata
        multi_arr = [{'Genres': self.metadata.genres}]

        # Book metadata
        book_multi_arr = [
            {'Moods (Authors)': self.metadata.moods},
            {'Styles (Narrators)': self.metadata.styles},
        ]

        # Determine which metadata to log
        if self.content_type == 'book':
            multi_arr.extend(book_multi_arr)

        return multi_arr

    def extract_asin_from_id(self):
        """
            Extracts the ASIN from the ID.
        """
        # Get the ASIN from the ID
        asin = self.metadata.id.split('_')[0]
        log.debug('Extracted ASIN from ID: ' + asin)
        return asin

    def extract_region_from_id(self):
        """
            Extracts the region from the ASIN and sets the region.
        """
        # Get the region from the ASIN
        try:
            region = self.metadata.id.split('_')[1]
            log.debug('Extracted region from ASIN: ' + region)
        except IndexError:
            log.info('No region found in ID, using default region.')
            region = 'us'
            # Save the region to the ID
            self.metadata.id = self.metadata.id + '_' + region
        # Set region and ASIN
        return region

    # Writes metadata information to log.
    def log_update_metadata(self):
        # Send a separator to the log
        log.separator(
            msg=(
                'FINALIZED: ' + self.metadata.title +
                ', ID: ' + self.metadata.id
            ),
            log_level="info"
        )

        # Collect metadata to log
        data_to_log = self.collect_metadata_to_log()
        log.metadata(data_to_log, log_level="info")

        # Collect metadata arrays to log
        multi_arr = self.collect_metadata_arrs_to_log()
        log.metadata_arrs(multi_arr, log_level="info")

        log.separator(log_level="info")


class AlbumUpdateTool(UpdateTool):
    def parse_api_response(self, response):
        """
            Parses keys from API into helper variables if they exist.
        """
        # Set empty variables
        self.date = None
        self.genres = None
        self.rating = None
        self.series = ''
        self.series2 = ''
        self.subtitle = ''
        self.thumb = ''
        self.volume = ''
        self.volume2 = ''

        if 'authors' in response:
            self.author = response['authors']
        if 'releaseDate' in response:
            self.date = response['releaseDate']
        if 'genres' in response:
            self.genres = response['genres']
        if 'narrators' in response:
            self.narrator = response['narrators']
        if 'rating' in response:
            self.rating = response['rating']
        if 'seriesPrimary' in response:
            self.series = response['seriesPrimary']['name']
            if 'position' in response['seriesPrimary']:
                self.volume = self.volume_prefix(
                    response['seriesPrimary']['position']
                )
        if 'seriesSecondary' in response:
            self.series2 = response['seriesSecondary']['name']
            if 'position' in response['seriesSecondary']:
                self.volume2 = self.volume_prefix(
                    response['seriesSecondary']['position']
                )
        if 'publisherName' in response:
            self.studio = response['publisherName']
        if 'summary' in response:
            self.synopsis = response['summary']
        if 'image' in response:
            self.thumb = response['image']
        if 'subtitle' in response:
            self.subtitle = response['subtitle']
        if 'title' in response:
            self.title = response['title']

    def volume_prefix(self, string):
        book_regex = '(Book ?(\d*\.)?\d+[+-]?[\d]?)'
        if not re.match(book_regex, string):
            prefixed_string = ('Book ' + string)
            return prefixed_string
        return string

    # Remove extra description text from the title
    def simplify_title(self):
        # If the title ends with a series part, remove it
        # works for "Book 1" and "Book One"
        album_title = re.sub(
            r", book [\w\s-]+\s*$", "", self.title, flags=re.IGNORECASE)
        # If the title ends with "unabridged"/"abridged", with or without parenthesis
        # remove them; case insensitive
        album_title = re.sub(r" *\(?(un)?abridged\)?$", "",
                             album_title, flags=re.IGNORECASE)
        # Trim any leading/trailing spaces just in case
        album_title = album_title.strip()

        return album_title


class ArtistUpdateTool(UpdateTool):
    def parse_api_response(self, response):
        """
            Parses keys from API into helper variables if they exist.
        """
        # Set empty variables
        self.date = None
        self.genres = None
        self.thumb = ''

        if 'description' in response:
            self.description = response['description']
        if 'genres' in response:
            self.genres = response['genres']
        if 'name' in response:
            self.name = response['name']
        if 'image' in response:
            self.thumb = response['image']


class TagTool:
    def __init__(self, helper, Prefs):
        self.helper = helper
        self.prefs = Prefs

    def add_genres(self):
        """
            Add genre(s) to Plex where available and depending on preference.
        """
        if not self.prefs['keep_existing_genres'] and self.helper.genres:
            if not self.helper.metadata.genres or self.helper.force:
                self.helper.metadata.genres.clear()
                for genre in self.helper.genres:
                    if genre['name']:
                        self.helper.metadata.genres.add(genre['name'])

    def add_narrators_to_styles(self):
        """
            Adds narrators to styles.
        """
        if not self.helper.metadata.styles or self.helper.force:
            self.helper.metadata.styles.clear()
            for narrator in self.helper.narrator:
                self.helper.metadata.styles.add(narrator['name'].strip())

    def add_authors_to_moods(self):
        """
            Adds authors to moods, except for cases in contibutors list.
        """
        contributor_regex = '.+?(?= -)'
        if not self.helper.metadata.moods or self.helper.force:
            # Loop through authors to check if it has contributor wording
            for author in self.helper.author:
                if not re.match(contributor_regex, author['name']):
                    self.helper.metadata.moods.add(author['name'].strip())

    def add_series_to_moods(self):
        """
            Adds book series' to moods, since collections are not supported
        """
        if self.helper.series:
            self.helper.metadata.moods.add("Series: " + self.helper.series)
        if self.helper.series2:
            self.helper.metadata.moods.add("Series: " + self.helper.series2)
