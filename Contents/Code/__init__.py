# plex debugging
try:
    import plexhints  # noqa: F401
except ImportError:
    pass
else:  # the code is running outside of Plex
    from typing import Optional
    from plexhints import plexhints_setup, update_sys_path
    plexhints_setup()  # reads the plugin plist file and determine if plexhints should use elevated policy or not
    update_sys_path()  # when running outside plex, append the path
    from plexhints.agent_kit import Agent, Media  # agent kit
    from plexhints.locale_kit import Locale  # locale kit
    from plexhints.network_kit import HTTP  # network kit
    from plexhints.prefs_kit import Prefs  # prefs kit
    from plexhints.proxy_kit import Proxy  # proxy kit
    from plexhints.util_kit import String, Util  # util kit
    from plexhints.constant_kit import CACHE_1WEEK  # constant kit
    from plexhints.object_kit import MetadataSearchResult  # object kit

    class Datetime:
        """
            Fake Datetime class to avoid importing datetime module.
            This is a placeholder and should be replaced with the actual
        """
        pass


# Audnexus Agent
# coding: utf-8
import json
# Import internal tools
from region_tools import RegionTool
from _version import version
from audnexuslogging import Logging
from search_tools import AlbumSearchTool, ArtistSearchTool, ScoreTool
from time import sleep
from update_tools import AlbumUpdateTool, ArtistUpdateTool

VERSION_NO = version

# Score required to short-circuit matching and stop searching.
GOOD_SCORE = 98

# Setup logger
log = Logging()


def ValidatePrefs():
    # type: () -> None
    log.debug('ValidatePrefs function call')


def Start():
    # type: () -> True
    HTTP.ClearCache()
    HTTP.CacheTime = CACHE_1WEEK
    HTTP.Headers['User-agent'] = (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)' +
        ' Chrome/123.0.6312.86 Safari/537.36;' +
        # needs to be updated after the pull request is merged
        ' Plex-Audnexus/'+VERSION_NO+' (+https://github.com/binyaminyblatt/Audnexus.bundle/issues)'
    )
    HTTP.Headers['Accept-Encoding'] = 'gzip'
    log.separator(
        msg=(
            "Audnexus Agent With Backup API v" + str(VERSION_NO)
        ),
        log_level="info"
    )


class AudiobookArtist(Agent.Artist):
    name = 'Audnexus Agent With Backup API'
    languages = [
        Locale.Language.English,
        Locale.Language.German,  # 'de' is the locale code for German
        Locale.Language.Spanish,  # 'es' is the locale code for Spanish
        Locale.Language.French,  # 'fr' is the locale code for French
        Locale.Language.Italian,  # 'it' is the locale code for Italian
        Locale.Language.Japanese,  # 'ja' is the locale code for Japanese
    ]
    primary_provider = True
    accepts_from = ['com.plexapp.agents.localmedia']

    prev_search_provider = 0

    def search(self, results, media, lang, manual):
        # type: (object, Media.Artist, str, bool) -> None # type: ignore
        """
            Search for artist metadata.
        """
        # Instantiate search helper
        search_helper = ArtistSearchTool(
            'authors', lang, manual, media, Prefs, results)

        # Check if we can quick match based on asin
        quick_match_asin = search_helper.check_for_asin()

        if quick_match_asin:
            results.Append(
                MetadataSearchResult(
                    id=quick_match_asin,
                    lang=lang,
                    name=quick_match_asin,
                    score=100,
                    year=1969
                )
            )
            log.info(
                'Using quick match based on asin: '
                '%s' % quick_match_asin
            )
            return

        # Validate author name
        search_helper.validate_author_name()

        # Short circuit search if artist name is bad.
        if not search_helper.media.artist:
            return

        search_helper.media.artist = String.StripDiacritics(
            search_helper.media.artist
        )

        # Call search API
        result = self.call_search_api(search_helper)

        # Write search result status to log
        if not result:
            log.warn(
                'No results found for query "%s"',
                search_helper.media.artist
            )
            return
        log.debug(
            'Found %s result(s) for query "%s"',
            len(result),
            search_helper.media.artist
        )

        info = self.process_results(search_helper, result)

        # Output the final results.
        log.separator(log_level="debug")
        log.debug('Final result:')
        for i, r in enumerate(info):
            description = r['author']

            results.Append(
                MetadataSearchResult(
                    id=r['id'],
                    lang=lang,
                    name=description,
                    score=r['score']
                )
            )

            # """
            #     If there are more than one result,
            #     and this one has a score that is >= GOOD SCORE,
            #     then ignore the rest of the results
            # """
            if not manual and len(info) > 1 and r['score'] >= GOOD_SCORE:
                log.info(
                    '            *** The score for these results are great, '
                    'so we will use them, and ignore the rest. ***'
                )
                break

    def update(self, metadata, media, lang, force):
        # type: (object, Media.Artist, str, bool) -> None # type: ignore
        """
            Update artist metadata.
        """
        log.separator(
            msg=(
                "UPDATING: " + media.title + (
                    " ID: " + metadata.id
                )
            ),
            log_level="info"
        )

        # Instantiate update helper
        update_helper = ArtistUpdateTool(
            'authors', force, lang, media, metadata, Prefs)

        self.call_item_api(update_helper)

        self.compile_metadata(update_helper)

    def call_search_api(self, helper):
        # type: (ArtistSearchTool) -> list
        """
            Builds URL then calls API, returns the JSON to helper function.

            :param helper: ArtistSearchTool instance
            :return: list
        """
        query = helper.build_search_args()
        search_url = helper.build_url(query)
        request = str(make_request(search_url))
        response = json_decode(request)
        # When using asin match, put it into array
        if isinstance(response, list):
            arr_to_pass = response
        else:
            arr_to_pass = [response]
        results_list = helper.parse_api_response(arr_to_pass)
        return results_list

    def process_results(self, helper, result):
        # type: (ArtistSearchTool, list) -> list
        """
            Process the results from the API call.
        """
        # Walk the found items and gather extended information
        info = []

        log.separator(msg="Search results", log_level="info")
        for index, result_dict in enumerate(result):
            score_helper = ScoreTool(
                helper,
                index,
                info,
                Locale.Language.English,
                Util.LevenshteinDistance,
                result_dict,
            )
            score_helper.run_score_author()

            # Print separators for easy reading
            if index <= len(result):
                log.separator(log_level="info")

        info = sorted(info, key=lambda inf: inf['score'], reverse=True)
        return info

    def call_item_api(self, helper):
        # type: (ArtistUpdateTool) -> None
        """
            Calls Audnexus API to get author details,
            then calls helper to parse those details.
        """
        update_url = helper.build_url()
        backup_url = helper.build_url(backup=True)
        request = str(make_request(update_url, backup_url))
        response = json_decode(request)
        helper.parse_api_response(response)

    def compile_metadata(self, helper):
        # type: (ArtistUpdateTool) -> None
        """
            Compiles the metadata for the artist.
        """
        # Description.
        helper.set_metadata_description()
        # Tags.
        helper.set_metadata_tags()
        # Title.
        helper.set_metadata_title()
        # Sort Title.
        helper.set_metadata_sort_title()
        # Thumb.
        # Kept here because of Proxy
        if helper.thumb:
            if helper.thumb not in helper.metadata.posters or helper.force:
                helper.metadata.posters[helper.thumb] = Proxy.Media(
                    make_request(helper.thumb), sort_order=0
                )

        helper.log_update_metadata()


class AudiobookAlbum(Agent.Album):
    name = 'Audnexus Agent With Backup API'
    languages = [
        Locale.Language.English,
        Locale.Language.German,  # 'de' is the locale code for German
        Locale.Language.Spanish,  # 'es' is the locale code for Spanish
        Locale.Language.French,  # 'fr' is the locale code for French
        Locale.Language.Italian,  # 'it' is the locale code for Italian
        Locale.Language.Japanese,  # 'ja' is the locale code for Japanese
    ]
    primary_provider = True
    accepts_from = ['com.plexapp.agents.localmedia']

    prev_search_provider = 0

    def search(self, results, media, lang, manual):
        # type: (list, Media.Album, str, bool) -> None # type: ignore
        """
            Search for an album.
        """
        # Instantiate search helper
        search_helper = AlbumSearchTool(
            'books', lang, manual, media, Prefs, results)

        pre_check = search_helper.pre_search_logging()
        # Purposefully terminate search if it's bad
        if not pre_check:
            log.debug("Didn't pass pre-check")
            return

        # Check if we can quick match based on asin
        quick_match_asin = search_helper.check_for_asin()
        if quick_match_asin:
            results.Append(
                MetadataSearchResult(
                    id=quick_match_asin,
                    lang=lang,
                    name=quick_match_asin,
                    score=100,
                    year=1969
                )
            )
            try:
                # Pre-cache the data for the region tool to use
                # ths should be faster than making the API call
                # because it will use the cache to get the data
                # this dosn't take into account the region overrides
                # but it's a good start so we don't have to wait for the API call
                # to get the data
                region_helper = RegionTool(Prefs['region'], content_type='books', id=quick_match_asin)
                HTTP.PreCache(region_helper.backup_api.get_id_url(),
                              headers={'accept': 'application/json', 'User-Agent': HTTP.Headers['User-agent']},
                              cacheTime=CACHE_1WEEK, timeout=10, immediate=True)
                HTTP.PreCache(region_helper.get_id_url(),
                              headers={'accept': 'application/json', 'User-Agent': HTTP.Headers['User-agent']},
                              cacheTime=CACHE_1WEEK, timeout=10, immediate=True)
            except Exception:
                # This is a catch all for any errors that may occur
                # when trying to pre-cache the data
                # this is not a critical error and can be ignored
                # if it occurs
                pass
            log.info(
                'Using quick match based on asin: '
                '%s' % quick_match_asin
            )
            return

        # # Validate author name
        search_helper.validate_author_name()

        # Call search API
        result = self.call_search_api(search_helper)

        # Write search result status to log
        if not result:
            log.warn(
                'No results found for query "%s"',
                search_helper.normalizedName
            )
            return
        log.debug(
            'Found %s result(s) for query "%s"',
            len(result),
            search_helper.normalizedName
        )

        info = self.process_results(search_helper, result)

        # Nested dict for localized separators
        # 'T_A' is the separator between title and author
        # 'A_N' is the separator between author and narrator
        separator_dict = {
            Locale.Language.English: {'T_A': 'by', 'A_N': 'w/'},
            Locale.Language.German: {'T_A': 'von', 'A_N': 'mit'},
            Locale.Language.French: {'T_A': 'de', 'A_N': 'ac'},
            Locale.Language.Italian: {'T_A': 'di', 'A_N': 'con'}
        }
        local_separators = separator_dict[lang]
        log.debug(
            'Using localized separators "%s" and "%s"',
            local_separators['T_A'], local_separators['A_N']
        )

        # Output the final results.
        log.separator(log_level="debug")
        log.debug('Final result:')
        for i, r in enumerate(info):
            # Truncate long titles
            # Displayable chars is ~60 (see issue #32)
            # Inlcude tolerance to only truncate if >4 chars need to be cut
            title_trunc = (r['title'][:30] + '..') if len(
                r['title']) > 36 else r['title']

            # Shorten artist
            artist_initials = search_helper.name_to_initials(r['author'])
            # Shorten narrator
            narrator_initials = search_helper.name_to_initials(r['narrator'])

            description = '\"%s\" %s %s %s %s' % (
                title_trunc,
                local_separators['T_A'],
                artist_initials,
                local_separators['A_N'],
                narrator_initials
            )
            results.Append(
                MetadataSearchResult(
                    id=r['id'],
                    lang=lang,
                    name=description,
                    score=r['score'],
                    year=r['year']
                )
            )

            # """
            #     If there are more than one result,
            #     and this one has a score that is >= GOOD SCORE,
            #     then ignore the rest of the results
            # """
            if not manual and len(info) > 1 and r['score'] >= GOOD_SCORE:
                log.info(
                    '            *** The score for these results are great, '
                    'so we will use them, and ignore the rest. ***'
                )
                break

    def update(self, metadata, media, lang, force):
        """
            Update an album.
        """
        log.separator(
            msg=(
                "UPDATING: " + media.title + (
                    " ID: " + metadata.id
                )
            ),
            log_level="info"
        )

        # Instantiate update helper
        update_helper = AlbumUpdateTool(
            'books', force, lang, media, metadata, Prefs)

        self.call_item_api(update_helper)

        self.compile_metadata(update_helper)

    def call_search_api(self, helper):
        # type: (AlbumSearchTool) -> list
        """
            Calls the Audnexus API to get book details,
            then calls helper to parse those details.
            Builds URL then calls API, returns the JSON to helper function.
        """
        query = helper.build_search_args()
        search_url = helper.build_url(query)
        request = str(make_request(search_url, ))
        response = json_decode(request)
        results_list = helper.parse_api_response(response)
        return results_list

    def process_results(self, helper, result):
        # type: (AlbumSearchTool, list) -> list
        """
            Process the results from the API call.
        """
        # Walk the found items and gather extended information
        info = []

        log.separator(msg="Search results", log_level="info")
        for index, result_dict in enumerate(result):
            date = self.getDateFromString(result_dict['date'])
            year = ''
            if date is not None:
                year = date.year

                # Make sure this isn't a pre-order listing
                if helper.check_if_preorder(date):
                    continue

            score_helper = ScoreTool(
                helper,
                index,
                info,
                Locale.Language.English,
                Util.LevenshteinDistance,
                result_dict,
                year
            )
            score_helper.run_score_book()

            # Print separators for easy reading
            if index <= len(result):
                log.separator(log_level="info")

        info = sorted(info, key=lambda inf: inf['score'], reverse=True)
        return info

    def call_item_api(self, helper):
        # type: (AlbumUpdateTool) -> None
        """
            Calls Audnexus API to get book details,
            then calls helper to parse those details.
        """
        update_url = helper.build_url()
        backup_url = helper.build_url(backup=True)
        request = str(make_request(update_url, backup_url))
        log.debug(
            'Response from API: %s',
            request
        )
        response = json_decode(request)
        helper.parse_api_response(response)

        # Set date to date object
        helper.date = self.getDateFromString(helper.date)

    def compile_metadata(self, helper):
        # type: (AlbumUpdateTool) -> None
        """
            Compiles the metadata for the book.
        """
        # Date.
        helper.set_metadata_date()
        # Tags.
        helper.set_metadata_tags()
        # Title.
        helper.set_metadata_title()
        # Sort Title.
        helper.set_metadata_sort_title()
        # Studio.
        helper.set_metadata_studio()
        # Summary.
        helper.set_metadata_summary()
        # Thumb.
        # Kept here because of Proxy
        if helper.thumb:
            if helper.thumb not in helper.metadata.posters or helper.force:
                helper.metadata.posters[helper.thumb] = Proxy.Media(
                    make_request(helper.thumb, accept_json=False), sort_order=0
                )
                # Re-prioritize the poster to the first position
                helper.metadata.posters.validate_keys([helper.thumb])
        if Prefs['extra_cover_art']:
            extra_covers = get_covers_from_audiobookcovers(helper.metadata.title)
            for index, url in enumerate(extra_covers):
                if url not in helper.metadata.posters or helper.force:
                    helper.metadata.posters[url] = Proxy.Media(
                        make_request(url, accept_json=False), sort_order=index + 10
                    )
        # Rating.
        helper.set_metadata_rating()

        # Set adult content flag
        helper.set_metadata_adult()

        # Log the resulting metadata
        helper.log_update_metadata()

        # add Collections to metadata
        helper.make_collections()

    def getDateFromString(self, string):
        """
            Converts a string to a date object.
        """
        try:
            return Datetime.ParseDate(string).date()
        except AttributeError:
            return None
        except ValueError:
            return None


def get_covers_from_audiobookcovers(query):
    # Construct the search URL
    search_url = "https://api.audiobookcovers.com/cover/bytext?q=" + String.Quote(query)

    # Make the HTTP request
    try:
        response = HTTP.Request(search_url, timeout=10, immediate=True)
        covers = json_decode(str(response))
    except Exception as e:
        log.error("Failed to fetch audiobook covers: %s", e)
        return []

    if isinstance(covers, list):
        return [
            c.get('versions', {}).get('png', {}).get('original')
            for c in covers
            if 'versions' in c and 'png' in c['versions'] and 'original' in c['versions']['png']
        ]
    return []


# Common helpers
def json_decode(output):
    # type: (str) -> dict | None
    """
        Decodes JSON output.
        :param output: JSON string to decode
        :return: Decoded JSON object or None if decoding fails
    """
    try:
        return json.loads(output, encoding="utf-8")
    except AttributeError:
        return None


def make_request(url, url2=None, accept_json=True):
    # type: (str, Optional[str], bool) -> str
    """
        Makes and returns an HTTP request.
        Retries 4 times, increasing  time between each retry.
    """
    sleep_time = 1
    num_retries = 4
    if accept_json:
        HTTP.Headers['accept'] = 'application/json'
    else:
        if 'accept' in HTTP.Headers:
            del HTTP.Headers['accept']
    for x in range(0, num_retries):
        request = the_request(url, sleep_time, return_binary=not accept_json)
        if url2 is not None and request is None:
            log.error("Failed http request attempt #" + str(x) + ": " + url)
            log.warn("Audnexus API is down, trying backup URL")
            log.info("Trying backup URL: " + url2)
            request = the_request(url2, sleep_time, return_binary=not accept_json)
            if request is None:
                log.error("Failed http request attempt #" + str(x) + ": " + url2 + " (backup)")
        if request is None:
            sleep(sleep_time)
            sleep_time = max(1, sleep_time * 2)
        else:
            break
    return request


def the_request(url, sleep_time=1, return_binary=False):
    # type: (str, int, bool) -> str
    """
        Makes and returns an HTTP request.
        Retries 4 times, increasing  time between each retry.
    """
    log.debug("Making request to: " + url)
    try:
        # Make the HTTP request
        # eventually this will be replaced with a more robust HTTP client aka requests
        response = HTTP.Request(url, timeout=90, sleep=sleep_time, immediate=True)
    except Exception as str_error:
        log.error(str_error)
        return None
    if return_binary:
        return response.content  # Binary (e.g., for images)
    else:
        return str(response)  # JSON/text
