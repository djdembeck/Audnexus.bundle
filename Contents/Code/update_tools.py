# Import internal tools
from logging import Logging

# Setup logger
log = Logging()


class AlbumUpdateTool:
    UPDATE_URL = 'https://api.audnex.us/books/'

    def __init__(self, force, lang, media, metadata):
        self.date = None
        self.force = force
        self.genres = None
        self.lang = lang
        self.media = media
        self.metadata = metadata
        self.rating = None
        self.series = ''
        self.series2 = ''
        self.subtitle = ''
        self.thumb = ''
        self.volume = ''
        self.volume2 = ''

    def parse_api_response(self, response):
        """
            Parses keys from API into helper variables if they exist.
        """
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
        prefixed_string = ('Book ' + string)
        return prefixed_string

    # Writes metadata information to log.
    def writeInfo(self):
        log.separator(
            msg=(
                'FINALIZED: ' + self.metadata.title +
                ', ID: ' + self.metadata.id
            ),
            log_level="info"
        )

        # Log basic metadata
        data_to_log = [
            {'ASIN': self.metadata.id},
            {'Album poster URL': self.thumb},
            {'Album publisher': self.metadata.studio},
            {'Album release date': str(self.metadata.originally_available_at)},
            {'Album sort title': self.metadata.title_sort},
            {'Album summary': self.metadata.summary},
            {'Album title': self.metadata.title},
        ]
        log.metadata(data_to_log, log_level="info")

        # Log basic metadata stored in arrays
        multi_arr = [
            {'Genres': self.metadata.genres},
            {'Moods(Authors)': self.metadata.moods},
            {'Styles(Narrators)': self.metadata.styles},
        ]
        log.metadata_arrs(multi_arr, log_level="info")

        log.separator(log_level="info")


class ArtistUpdateTool:
    UPDATE_URL = 'https://api.audnex.us/authors/'

    def __init__(self, force, lang, media, metadata):
        self.date = None
        self.force = force
        self.genres = None
        self.lang = lang
        self.media = media
        self.metadata = metadata
        self.thumb = ''

    def parse_api_response(self, response):
        """
            Parses keys from API into helper variables if they exist.
        """
        if 'description' in response:
            self.description = response['description']
        if 'genres' in response:
            self.genres = response['genres']
        if 'name' in response:
            self.name = response['name']
        if 'image' in response:
            self.thumb = response['image']

    # Writes metadata information to log.
    def writeInfo(self):
        log.separator(
            msg=(
                'FINALIZED: ' + self.metadata.title +
                ', ID: ' + self.metadata.id
            ),
            log_level="info"
        )

        # Log basic metadata
        data_to_log = [
            {'ASIN': self.metadata.id},
            {'Author bio': self.metadata.summary},
            {'Author name': self.metadata.title},
            {'Author poster URL': self.thumb},
            {'Author sort name': self.metadata.title_sort},
        ]
        log.metadata(data_to_log, log_level="info")

        # Log basic metadata stored in arrays
        multi_arr = [
            {'Genres': self.metadata.genres},
        ]
        log.metadata_arrs(multi_arr, log_level="info")

        log.separator(log_level="info")


class TagTool:
    def __init__(self, helper, Prefs, re):
        self.helper = helper
        self.prefs = Prefs
        self.re = re

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
            self.helper.metadata.moods.clear()
            # Loop through authors to check if it has contributor wording
            for author in self.helper.author:
                if not self.re.match(contributor_regex, author['name']):
                    self.helper.metadata.moods.add(author['name'].strip())

    def add_series_to_moods(self):
        """
            Adds book series' to moods, since collections are not supported
        """
        if self.helper.series:
            self.helper.metadata.moods.add("Series: " + self.helper.series)
        if self.helper.series2:
            self.helper.metadata.moods.add("Series: " + self.helper.series2)
