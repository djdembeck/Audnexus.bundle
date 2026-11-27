# Import internal tools
from logging import Logging
from region_tools import (
    RegionTool,
    get_api_url,
    is_approved_artwork_url,
)
import json
import re
import struct
import urllib
import os
try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

# Setup logger
log = Logging()

try:
    STRING_TYPES = (basestring,)
except NameError:
    STRING_TYPES = (str,)


def store_similar_enabled(prefs):
    """
        Returns whether similar-book moods are enabled.
    """
    try:
        return prefs['store_similar_as_moods']
    except (KeyError, TypeError):
        return False

# Keep the poster picker useful instead of mirroring the entire history.
MAX_HISTORY_POSTERS = 10
MAX_SIMILAR_BOOKS = 10

# Policy values for the poster update policy, after alias normalization.
# The latest policy refreshes the available covers; the first-poster pick
# still follows the poster order pref, so the label says refresh, not use.
POSTER_POLICY_KEEP = 'Keep saved posters'
POSTER_POLICY_LATEST = 'Always refresh covers from upstream'

def normalize_poster_policy(policy):
    """
        Maps legacy poster update policy values to the current ones.
    """
    poster_policy_aliases = {
        'Always use latest upstream cover': POSTER_POLICY_LATEST,
        'Always use latest/upstream cover': POSTER_POLICY_LATEST,
        'Keep saved and do not update': POSTER_POLICY_KEEP,
    }
    return poster_policy_aliases.get(policy, policy)


def similar_storage_key(metadata, content_type):
    """
        Dict key for the similar titles an item stored. The full
        normalized agent id (ASIN plus region suffix) is the stable
        per-item identity, so a regional match keeps its own record,
        and the content type separates albums from artists.
    """
    try:
        item_id = metadata.id
    except AttributeError:
        return None
    if not item_id:
        return None
    return 'similar_titles_' + content_type + '_' + item_id


def store_similar_titles(helper, names):
    """
        Remembers the similar titles this item stored in the plugin
        Dict, so a later refresh with a fresh metadata object can
        still reconcile exactly what this item wrote. Prefs is
        read-only, so this bookkeeping cannot live there.
    """
    key = similar_storage_key(helper.metadata, helper.content_type)
    if not key:
        return
    try:
        helper.plugin_dict[key] = json.dumps(list(names))
    except (KeyError, TypeError):
        log.warn('Failed to store similar titles for ' + key)


def clear_stored_similar(helper):
    """
        Removes agent-owned similar entries this item stored previously.
        User-added entries are kept. The key is deleted after reading it
        so a one-time store does not leak into a later response.
    """
    key = similar_storage_key(helper.metadata, helper.content_type)
    if not key:
        return
    try:
        stored_raw = helper.plugin_dict[key]
    except (KeyError, TypeError):
        return
    try:
        del helper.plugin_dict[key]
    except (KeyError, TypeError):
        log.warn('Failed to clear stored similar titles for ' + key)
        return
    try:
        stored = json.loads(stored_raw)
    except (TypeError, ValueError):
        return
    if not isinstance(stored, list):
        return
    for name in stored:
        if not isinstance(name, STRING_TYPES):
            continue
        try:
            helper.metadata.similar.remove(name)
        except (AttributeError, ValueError):
            pass
        try:
            helper.metadata.moods.remove('Similar: ' + name)
        except (AttributeError, ValueError):
            pass


class UpdateTool:
    def __init__(self, content_type, force, lang, media, metadata, prefs,
                 plugin_dict):
        self.content_type = content_type
        self.force = force
        self.lang = lang
        self.media = media
        self.metadata = metadata
        self.prefs = prefs
        # Writable store for agent bookkeeping; Prefs is read-only.
        self.plugin_dict = plugin_dict
        self.api_url = get_api_url(self.prefs)
        self.region = self.extract_region_from_id()
        self.tags = []
        self.similar = []
        self.similar_ok = False
        self.artwork_urls = []
        self.artwork_fallbacks = {}
        self.artwork_sizes = {}
        self.artwork_ok = False
        self.poster_order = 'Most recent cover'
        try:
            self.poster_order = self.prefs['poster_order']
        except KeyError:
            pass
        poster_aliases = {
            'Most recent first': 'Most recent cover',
            'Most recent cover first': 'Most recent cover',
            'Oldest first': 'Oldest historical cover',
            'Oldest cover first': 'Oldest historical cover',
            'Largest first': 'Largest resolution cover',
            'Largest resolution first': 'Largest resolution cover',
        }
        self.poster_order = poster_aliases.get(
            self.poster_order, self.poster_order)
        self.poster_update_policy = POSTER_POLICY_KEEP
        try:
            self.poster_update_policy = self.prefs['poster_update_policy']
        except KeyError:
            pass
        self.poster_update_policy = normalize_poster_policy(
            self.poster_update_policy)
        self.current_artwork_size = 0

    def build_url(self):
        """
            Builds the URL for the API request.
        """
        # Get the current region
        self.region_override = self.get_preferred_region()
        # Set the region helper
        region_helper = RegionTool(
            region=self.region_override,
            content_type=self.content_type,
            id=self.extract_asin_from_id(),
            base_url=self.api_url)

        update_url = region_helper.get_id_url()
        log.debug('Update URL: ' + update_url)
        return update_url

    def build_artwork_url(self):
        """
            Builds the retained-artwork URL for a book.
        """
        if self.content_type != 'books':
            return None
        base_url, _, query = self.build_url().partition('?')
        return base_url + '/artwork?' + query

    def build_similar_url(self):
        """
            Builds the expanded similar-books URL for a book.
        """
        if self.content_type != 'books':
            return None
        base_url, _, query = self.build_url().partition('?')
        return base_url + '/similar?' + query + '&expand=books'

    def cleanup_html(self):
        """
            Cleans up HTML in either the description or synopsis.
        """
        html_tags = '<[^<]+?>'

        # Clean up HTML in the description
        if self.content_type == 'authors':
            # First handle special cases
            self.description = self.replace_html_special(self.description)
            self.description = re.sub(
                html_tags, '', self.description)
        # Clean up HTML in the synopsis
        if self.content_type == 'books':
            # First handle special cases
            self.synopsis = self.replace_html_special(self.synopsis)
            self.synopsis = re.sub(
                html_tags, '', self.synopsis)

    def replace_html_special(self, input_html):
        """
            Replaces HTML lists with a bullet point.
            Replaces HTML paragraphs with a newline.
            Replaces HTML line breaks with a newline.
        """
        return (
            input_html.replace("<ul>", "")
            .replace("</ul>", "\n")
            .replace("<ol>", "")
            .replace("</ol>", "\n")
            .replace("<li>", " • ")
            .replace("</li>", "\n")
            .replace("<br />", "")
            .replace("<p>", "")
            .replace("</p>", "\n")
            .strip()
        )

    def collect_metadata_to_log(self):
        """
            Collects the metadata to log.
        """
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
                    {'Similar Authors': ', '.join([author['name']
                                                   for author in self.similar] if self.similar else [])},
                ]
            )

        return data_to_log

    def collect_metadata_arrs_to_log(self):
        """
            Collects the metadata arrays to log.
        """
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
            region = self.get_preferred_region()
            # Save the region to the ID
            self.metadata.id = self.metadata.id + '_' + region
        # Set region and ASIN
        return region

    def get_preferred_region(self):
        """
            Get the preferred region from class or preferences.
        """
        try:
            region = self.region
        except AttributeError:
            region = self.prefs['region']
        log.info('Preferred region: ' + region)
        return region

    def log_update_metadata(self):
        """
            Writes metadata information to log.
        """
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
        self.set_empty_variables()

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
        if 'tags' in response:
            self.tags = response['tags']
        if 'similar' in response:
            self.similar = response['similar']
        if 'subtitle' in response:
            self.subtitle = response['subtitle']
        if 'title' in response:
            self.title = response['title']

    def parse_artwork_response(self, response):
        """
            Collects retained cover images, newest first.
        """
        self.artwork_ok = False
        self.artwork_urls = []
        self.artwork_fallbacks = {}
        self.artwork_sizes = {}
        self.current_artwork_size = 0
        if not isinstance(response, dict):
            return
        items = response.get('items')
        if not isinstance(items, list):
            return
        self.artwork_ok = True

        current_image_id = self.get_amazon_image_id(self.thumb)
        seen_urls = set()
        seen_image_ids = set()
        parsed_items = 0
        for item in items:
            if not isinstance(item, dict):
                continue
            legacy = item.get('legacy')
            if not isinstance(legacy, dict):
                legacy = {}
            stored_url = legacy.get('storedUrl')
            if not isinstance(stored_url, STRING_TYPES):
                stored_url = None
            renditions = item.get('renditions')
            if not isinstance(renditions, list):
                renditions = []
            rendition_urls = self.pick_rendition_urls(renditions)
            stored_ok = bool(stored_url and is_approved_artwork_url(
                stored_url, self.api_url))
            if not stored_ok and not rendition_urls:
                continue
            parsed_items += 1
            fallback_url = None
            if stored_ok:
                url = stored_url
                for candidate in rendition_urls:
                    if candidate == self.thumb:
                        continue
                    if candidate in seen_urls:
                        continue
                    if (current_image_id and
                            self.get_amazon_image_id(candidate) ==
                            current_image_id):
                        continue
                    fallback_url = candidate
                    break
            else:
                url = None
                explicit_image_id = item.get('imageId')
                if (not isinstance(explicit_image_id, STRING_TYPES) or
                        not explicit_image_id):
                    explicit_image_id = None
                for candidate in rendition_urls:
                    if candidate == self.thumb:
                        continue
                    if candidate in seen_urls:
                        continue
                    if (current_image_id and
                            self.get_amazon_image_id(candidate) ==
                            current_image_id):
                        continue
                    url = candidate
                    break
                if not url and explicit_image_id and current_image_id:
                    for candidate in rendition_urls:
                        if candidate == self.thumb:
                            continue
                        if candidate in seen_urls:
                            continue
                        if (self.get_amazon_image_id(candidate) ==
                                current_image_id and
                                explicit_image_id != current_image_id):
                            url = candidate
                            break
                if not url:
                    continue
            if url in seen_urls or url == self.thumb:
                continue
            item_image_id = item.get('imageId')
            if (not isinstance(item_image_id, STRING_TYPES) or
                    not item_image_id):
                item_image_id = self.get_amazon_image_id(url)
            url_image_id = self.get_amazon_image_id(url)
            if (current_image_id and
                    item_image_id == current_image_id and
                    url_image_id == current_image_id):
                current_size = 0
                for rendition in renditions:
                    if not isinstance(rendition, dict):
                        continue
                    try:
                        candidate_size = int(
                            rendition.get('rendition'))
                    except (TypeError, ValueError):
                        continue
                    if candidate_size > current_size:
                        current_size = candidate_size
                if current_size > self.current_artwork_size:
                    self.current_artwork_size = current_size
                continue
            if item_image_id and item_image_id in seen_image_ids:
                continue
            if (stored_ok and fallback_url and
                    fallback_url != stored_url):
                self.artwork_fallbacks[stored_url] = fallback_url
            artwork_size = 0
            for rendition in renditions:
                if not isinstance(rendition, dict):
                    continue
                if rendition.get('sourceUrl') == url:
                    try:
                        artwork_size = int(rendition.get('rendition'))
                    except (TypeError, ValueError):
                        artwork_size = 0
                    break
            if not artwork_size and stored_ok:
                stored_name = urlparse(url).path.rsplit('/', 1)[-1]
                stored_rendition = re.search(r'_SL(\d+)', stored_name)
                if stored_rendition:
                    artwork_size = int(stored_rendition.group(1))
            if item_image_id:
                seen_image_ids.add(item_image_id)
            seen_urls.add(url)
            self.artwork_sizes[url] = artwork_size
            self.artwork_urls.append(url)
            if (self.poster_order == 'Most recent cover' and
                    len(self.artwork_urls) >= MAX_HISTORY_POSTERS):
                break
        if items and not parsed_items:
            self.artwork_ok = False
            self.artwork_urls = []
            self.artwork_fallbacks = {}

    def pick_rendition_urls(self, renditions):
        """
            Returns approved rendition URLs in preference order.
        """
        approved = []
        approved_set = set()
        for preferred in ('1024', '500'):
            for rendition in renditions:
                if not isinstance(rendition, dict):
                    continue
                source = rendition.get('sourceUrl')
                if (rendition.get('rendition') == preferred and
                        isinstance(source, STRING_TYPES) and source and
                        source not in approved_set and
                        is_approved_artwork_url(source, self.api_url)):
                    approved.append(source)
                    approved_set.add(source)
        for rendition in renditions:
            if not isinstance(rendition, dict):
                continue
            source = rendition.get('sourceUrl')
            if (isinstance(source, STRING_TYPES) and source and
                    source not in approved_set and
                    is_approved_artwork_url(source, self.api_url)):
                approved.append(source)
                approved_set.add(source)
        return approved

    def parse_similar_response(self, response):
        """
            Collects similar book titles from the dedicated endpoint.
            Leaves inline recommendations in place when the response is
            missing or malformed.
        """
        self.similar_ok = False
        if not isinstance(response, dict):
            return
        books = response.get('books')
        if not isinstance(books, list):
            return
        similar = []
        for book in books[:MAX_SIMILAR_BOOKS]:
            if not isinstance(book, dict):
                continue
            title = book.get('title')
            if not isinstance(title, STRING_TYPES):
                continue
            title = title.strip()
            if title:
                similar.append({'name': title})
        if books and not similar:
            # A nonempty list with no usable titles is malformed; keep the
            # inline fallback instead of replacing it with an empty list.
            return
        self.similar = similar
        self.similar_ok = True

    def get_amazon_image_id(self, url):
        """
            Extracts the stable Amazon image ID from a cover URL.
        """
        if not url or '/images/I/' not in url:
            return None
        return url.split('/images/I/', 1)[1].split('.', 1)[0].split('/', 1)[0]

    def set_metadata_date(self):
        """
            Sets the date.
        """
        if self.date is not None:
            if not self.metadata.originally_available_at or self.force:
                self.metadata.originally_available_at = self.date

    def set_empty_variables(self):
        """
            Sets empty variables.
        """
        self.artwork_fallbacks = {}
        self.artwork_ok = False
        self.artwork_urls = []
        self.date = None
        self.genres = None
        self.rating = None
        self.series = ''
        self.series2 = ''
        self.similar = None
        self.similar_ok = False
        self.subtitle = ''
        self.tags = None
        self.thumb = ''
        self.volume = ''
        self.volume2 = ''

    def set_metadata_rating(self):
        """
            Sets the rating.
        """
        # We always want to refresh the rating
        if self.rating:
            self.metadata.rating = float(self.rating) * 2

    def set_metadata_summary(self):
        """
            Sets the summary.
        """
        if not self.metadata.summary or self.force:
            self.cleanup_html()
            self.metadata.summary = self.synopsis

    def set_metadata_studio(self):
        """
            Sets the studio.
        """
        if not self.metadata.studio or self.force:
            self.metadata.studio = self.studio

    def set_metadata_sort_title(self):
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

    def set_metadata_tags(self):
        """
            Set tags of artist
        """
        # Create tagger.
        tagger = TagTool(self, self.prefs)

        # Clears moods if force (refresh) is true.
        store_similar = store_similar_enabled(self.prefs)
        if self.force:
            tagger.clear_moods(
                keep_similar=(store_similar and
                              not self.similar_ok))
            tagger.clear_styles()
        elif not store_similar:
            # Clear old recommendations before adding other moods so a
            # normal tag named like one is not removed after it is added.
            tagger.clear_similar_moods()

        # Genres.
        tagger.add_genres()
        # Narrators.
        tagger.add_narrators_to_styles()
        # Authors.
        if self.prefs['store_author_as_mood']:
            tagger.add_authors_to_moods()
        # Series.
        tagger.add_series_to_moods()
        # Tags (topics, awards, editorial, moods).
        if self.prefs['store_tags_as_moods']:
            tagger.add_tags_to_moods()
        # Similar books. Replace only when the dedicated response was valid;
        # a failed fetch keeps the agent entries stored before.
        if self.similar_ok:
            clear_stored_similar(self)
        if store_similar:
            tagger.add_similar_moods(
                replace=self.similar_ok)

    def set_metadata_title(self):
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

    def simplify_title(self):
        """
            Remove extra description text from the title
        """
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

    def volume_prefix(self, string):
        """
            Prefixes volume number with 'Book' if it doesn't exist.
        """
        book_regex = '(Book ?(\d*\.)?\d+[+-]?[\d]?)'
        if not re.match(book_regex, string):
            prefixed_string = ('Book ' + string)
            return prefixed_string
        return string


class ArtistUpdateTool(UpdateTool):
    def get_square_image(self, image_url):
        """
            Get square author photos from Audible

            Crop each portrait photo to a square centered at the top,
            and crop each landscape photo to a square at the horizontal center
        """
        if not image_url:
            return ''
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

        except Exception:
            log.separator(
                msg=(
                    'Error getting square image for ' + self.media.title
                ),
                log_level="error"
            )
            log.error('Failed to get square image')
        return image_url

    def parse_api_response(self, response):
        """
            Parses keys from API into helper variables if they exist.
        """
        self.set_empty_variables()

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
        if 'similar' in response:
            self.similar = response['similar']

    def set_metadata_description(self):
        """
            Set description of artist
        """
        if not self.metadata.summary or self.force:
            self.cleanup_html()
            self.metadata.summary = self.description

    def set_empty_variables(self):
        """
            Sets empty variables.
        """
        self.date = None
        self.genres = None
        self.similar = None
        self.thumb = ''

    def set_metadata_sort_title(self):
        """
            Set sort title of artist
        """
        if not self.metadata.title_sort or self.force:
            single_word_name = re.match(r'\A[\w-]+\Z', self.name)
            if self.prefs['sort_author_by_last_name'] and not single_word_name:
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

    def set_metadata_tags(self):
        """
            Set tags of artist
        """
        # Create tagger.
        tagger = TagTool(self, self.prefs)
        # Genres.
        tagger.add_genres()
        # Similar.
        # The response was valid when compile_metadata runs, so reconcile
        # agent-owned entries even when the new list is empty.
        clear_stored_similar(self)
        tagger.add_similar()

    def set_metadata_title(self):
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

    def add_tags_to_moods(self):
        """
            Adds Audnexus tags to Plex moods.
        """
        tags = self.helper.tags
        if not isinstance(tags, list):
            return
        prefixes = {
            'editorial': 'Editorial: ',
            'award': 'Award: ',
            'franchise': 'Franchise: ',
            'goodreads': 'Goodreads: ',
            'social': 'Social: ',
            'duration': 'Duration: ',
            'instareads': 'Instareads: ',
            'other': 'Tag: ',
        }
        for tag in tags:
            try:
                if isinstance(tag, dict):
                    name_value = tag.get('name')
                    tag_type = tag.get('type')
                else:
                    name_value = tag
                    tag_type = None
                if not isinstance(name_value, STRING_TYPES):
                    continue
                name = name_value.strip()
                if not name:
                    continue
                if not isinstance(tag_type, STRING_TYPES):
                    tag_type = None
                prefix = prefixes.get(tag_type, '')
                self.helper.metadata.moods.add(prefix + name)
            except Exception:
                continue

    def add_similar_moods(self, replace=False):
        """
            Adds similar books as agent-owned Similar: moods.
        """
        if replace:
            keep = []
            for mood in list(self.helper.metadata.moods):
                if (isinstance(mood, STRING_TYPES) and
                        mood.startswith('Similar: ')):
                    continue
                keep.append(mood)
            self.helper.metadata.moods.clear()
            for mood in keep:
                self.helper.metadata.moods.add(mood)
        if not self.helper.similar:
            return
        names = []
        for item in self.helper.similar:
            if isinstance(item, dict):
                name = item.get('name')
            else:
                name = item
            if not isinstance(name, STRING_TYPES):
                continue
            name = name.strip()
            if name:
                names.append(name)
                self.helper.metadata.moods.add('Similar: ' + name)
        if names:
            store_similar_titles(self.helper, names)

    def clear_similar_moods(self):
        """
            Removes agent-owned Similar: moods.
        """
        keep = []
        for mood in list(self.helper.metadata.moods):
            if (isinstance(mood, STRING_TYPES) and
                    mood.startswith('Similar: ')):
                continue
            keep.append(mood)
        self.helper.metadata.moods.clear()
        for mood in keep:
            self.helper.metadata.moods.add(mood)

    def add_similar(self):
        """
            Adds similar items, falling back to moods for album metadata.
        """
        if not self.helper.similar:
            return
        names = []
        for item in self.helper.similar:
            if isinstance(item, dict):
                name = item.get('name')
            else:
                name = item
            if isinstance(name, STRING_TYPES):
                name = name.strip()
                if name:
                    names.append(name)
        if not names:
            return
        try:
            for name in names:
                self.helper.metadata.similar.add(name)
        except AttributeError:
            for name in names:
                self.helper.metadata.moods.add('Similar: ' + name)
        store_similar_titles(self.helper, names)

    def clear_moods(self, keep_similar=False):
        """
            Clears moods, optionally keeping agent-owned Similar: moods.
        """
        if not keep_similar:
            self.helper.metadata.moods.clear()
            return
        similar = []
        for mood in list(self.helper.metadata.moods):
            if (isinstance(mood, STRING_TYPES) and
                    mood.startswith('Similar: ')):
                similar.append(mood)
        self.helper.metadata.moods.clear()
        for mood in similar:
            self.helper.metadata.moods.add(mood)

    def clear_styles(self):
        """
            Clears styles.
        """
        self.helper.metadata.styles.clear()
