# Import internal tools
from logging import Logging
from region_tools import RegionTool
import re
import struct
import urllib
import os

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

        # Determine which metadata to log
        if self.content_type == 'books':
            data_to_log.extend(
                [
                    {'Book poster URL': self.thumb},
                    {'Book publisher': self.metadata.studio},
                    {'Book release date': str(
                        self.metadata.originally_available_at)},
                    {'Book sort title': self.metadata.title_sort},
                    {'Book summary': self.metadata.summary},
                    {'Book title': self.metadata.title},
                ]
            )
        elif self.content_type == 'authors':
            data_to_log.extend(
                [
                    {'Author bio': self.metadata.summary},
                    {'Author name': self.metadata.title},
                    {'Author poster URL': self.thumb},
                    {'Author sort name': self.metadata.title_sort},
                ]
            )

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
    def set_date(self):
        """
            Sets the date.
        """
        if self.date is not None:
            if not self.metadata.originally_available_at or self.force:
                self.metadata.originally_available_at = self.date

    def set_rating(self):
        """
            Sets the rating.
        """
        # We always want to refresh the rating
        if self.rating:
            self.metadata.rating = float(self.rating) * 2

    def set_summary(self):
        """
            Sets the summary.
        """
        if not self.metadata.summary or self.force:
            self.metadata.summary = self.synopsis

    def set_studio(self):
        """
            Sets the studio.
        """
        if not self.metadata.studio or self.force:
            self.metadata.studio = self.studio

    def set_sort_title(self):
        """
            Sets the sort title.
        """
        # Add series/volume to sort title where possible.
        series_with_volume = ''
        if self.series and self.volume:
            series_with_volume = self.series + ', ' + self.volume
        # Only include subtitle in sort if not in a series
        if not self.volume:
            self.title = self.metadata.title
        if not self.metadata.title_sort or self.force:
            self.metadata.title_sort = ' - '.join(
                filter(
                    None, [(series_with_volume), self.title]
                )
            )

    def set_tags(self):
        """
            Set tags of artist
        """
        # Create tagger.
        tagger = TagTool(self, self.prefs)
        # Genres.
        tagger.add_genres()
        # Narrators.
        tagger.add_narrators_to_styles()
        # Authors.
        if self.prefs['store_author_as_mood']:
            tagger.add_authors_to_moods()
        # Series.
        tagger.add_series_to_moods()

    def set_title(self):
        """
            Sets the title.
        """
        # If the `simplify_title` option is selected, don't append subtitle
        # and remove extra endings on the title
        if self.prefs['simplify_title']:
            album_title = self.simplify_title()
        elif self.subtitle:
            album_title = self.title + ': ' + self.subtitle
        else:
            album_title = self.title
        if not self.metadata.title or self.force:
            self.metadata.title = album_title

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
    def get_square_image(self, image_url):
        """
            Get square author photos from Audible

            Crop each portrait photo to a square centered at the top,
            and crop each landscape photo to a square at the horizontal center
        """
        try:
            image_file_dl = urllib.urlopen(image_url)
            image_file_dl_contents = image_file_dl.read()
            image_file_dl.close()

            image_file = os.tmpfile()
            image_file.write(image_file_dl_contents)

            image_file.seek(0)

            head = image_file.read(24)
            if len(head) != 24:
                image_file.close()
                return image_url

            image_file.seek(0)  # Read 0xff next
            size = 2
            ftype = 0
            while not 0xc0 <= ftype <= 0xcf:
                image_file.seek(size, 1)
                byte = image_file.read(1)
                while ord(byte) == 0xff:
                    byte = image_file.read(1)
                ftype = ord(byte)
                size = struct.unpack('>H', image_file.read(2))[0] - 2
            # We are at a SOFn block
            image_file.seek(1, 1)  # Skip `precision' byte.
            height, width = struct.unpack('>HH', image_file.read(4))

            image_file.close()

            if (height > width):
                # Return a portrait image centered at the top
                w_str = str(width)
                square_image_url = image_url.replace(
                    '.jpg',
                    '.__01_SX'+w_str+'_CR0,0,'+w_str+','+w_str+'__.jpg'
                )
                return square_image_url

            if (width > height):
                # Return a landscape image centered at the horizontal middle
                h_str = str(height)
                padding = str((width - height) / 2)
                square_image_url = image_url.replace(
                    '.jpg',
                    '.__01_SY'+h_str+'_CR'+padding+',0,'+h_str+','+h_str+'__.jpg'
                )
                return square_image_url

            return image_url

        except Exception as err:
            log.separator(
                msg=(
                    'Error getting square image for ' + self.media.title
                ),
                log_level="error"
            )
            log.error(err)
        return image_url


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
            squared_image = self.get_square_image(response['image'])
            log.debug('Square image: ' + squared_image)
            self.thumb = squared_image

    def set_description(self):
        """
            Set description of artist
        """
        if not self.metadata.summary or self.force:
            self.metadata.summary = self.description

    def set_sort_title(self):
        """
            Set sort title of artist
        """
        if not self.metadata.title_sort or self.force:
            if self.prefs['sort_author_by_last_name'] and not (
                # Handle single word names
                re.match(r'\A[\w-]+\Z', self.name)
            ):
                split_author_surname = re.match(
                    '^(.+?).([^\s,]+)(,?.(?:[JS]r\.?|III?|IV))?$',
                    self.name,
                )
                self.metadata.title_sort = ', '.join(
                    filter(
                        None,
                        [
                            (split_author_surname.group(2) + ', ' +
                                split_author_surname.group(1)),
                            split_author_surname.group(3)
                        ]
                    )
                )
            else:
                self.metadata.title_sort = self.metadata.title

    def set_tags(self):
        """
            Set tags of artist
        """
        # Create tagger.
        tagger = TagTool(self, self.prefs)
        # Genres.
        tagger.add_genres()

    def set_title(self):
        """
            Set title of artist
        """
        if not self.metadata.title or self.force:
            self.metadata.title = self.name


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
