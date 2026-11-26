# Audnexus Agent
# coding: utf-8
import json
# Import internal tools
from _version import version
from logging import Logging
from region_tools import (
    APPROVED_ARTWORK_HOSTS,
    describe_artwork_url,
    describe_url,
    get_url_origin,
    is_approved_artwork_url,
)
from search_tools import AlbumSearchTool, ArtistSearchTool, ScoreTool
from time import sleep
try:
    from urlparse import urlparse, urljoin
except ImportError:
    from urllib.parse import urlparse, urljoin
from update_tools import (
    AlbumUpdateTool,
    ArtistUpdateTool,
    MAX_HISTORY_POSTERS,
    store_similar_enabled,
)

VERSION_NO = version

# Score required to short-circuit matching and stop searching.
GOOD_SCORE = 98

# Setup logger
log = Logging()


def ValidatePrefs():
    log.debug('ValidatePrefs function call')


def Start():
    HTTP.ClearCache()
    HTTP.CacheTime = CACHE_1WEEK
    HTTP.Headers['User-agent'] = (
        'Mozilla/4.0 (compatible; MSIE 8.0; Windows NT 6.2; Trident/4.0;'
        'SLCC2; .NET CLR 2.0.50727; .NET CLR 3.5.30729; .NET CLR 3.0.30729;'
        'Media Center PC 6.0'
    )
    HTTP.Headers['Accept-Encoding'] = 'gzip'
    log.separator(
        msg=(
            "Audnexus Audiobooks Agent v" + VERSION_NO
        ),
        log_level="info"
    )


class AudiobookArtist(Agent.Artist):
    name = 'Audnexus Agent'
    languages = [
        Locale.Language.English,
        'de',
        'es',
        'fr',
        'it',
        'ja',
    ]
    primary_provider = True
    accepts_from = ['com.plexapp.agents.localmedia']

    prev_search_provider = 0

    def search(self, results, media, lang, manual):
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

            """
                If there are more than one result,
                and this one has a score that is >= GOOD SCORE,
                then ignore the rest of the results
            """
            if not manual and len(info) > 1 and r['score'] >= GOOD_SCORE:
                log.info(
                    '            *** The score for these results are great, '
                    'so we will use them, and ignore the rest. ***'
                )
                break

    def update(self, metadata, media, lang, force):
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

        if not self.call_item_api(update_helper):
            log.warn('Skipping metadata update: no valid Audnexus response')
            return

        self.compile_metadata(update_helper)

    def call_search_api(self, helper):
        """
            Builds URL then calls API, returns the JSON to helper function.
        """
        query = helper.build_search_args()
        search_url = helper.build_url(query)
        request = make_api_request(search_url, helper.api_url)
        if request is None:
            return []
        response = json_decode(str(request))
        # When using asin match, put it into array
        if isinstance(response, list):
            arr_to_pass = response
        else:
            arr_to_pass = [response]
        results_list = helper.parse_api_response(arr_to_pass)
        return results_list

    def process_results(self, helper, result):
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
        """
            Calls Audnexus API to get author details,
            then calls helper to parse those details.
        """
        update_url = helper.build_url()
        request = make_api_request(update_url, helper.api_url)
        if request is None:
            log.error('No response from Audnexus (%s)' % describe_url(update_url))
            return False
        try:
            response = json_decode(str(request))
        except Exception:
            log.error('Invalid Audnexus response (%s)' % (
                describe_url(update_url)))
            return False
        if (not isinstance(response, dict) or
                'error' in response or 'asin' not in response):
            log.error('Invalid Audnexus response (%s)' % describe_url(update_url))
            return False
        helper.parse_api_response(response)
        return True

    def compile_metadata(self, helper):
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
    name = 'Audnexus Agent'
    languages = [
        Locale.Language.English,
        'de',
        'es',
        'fr',
        'it',
        'ja',
    ]
    primary_provider = True
    accepts_from = ['com.plexapp.agents.localmedia']

    prev_search_provider = 0

    def search(self, results, media, lang, manual):
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
            'de': {'T_A': 'von', 'A_N': 'mit'},
            'fr': {'T_A': 'de', 'A_N': 'ac'},
            'it': {'T_A': 'di', 'A_N': 'con'}
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

            """
                If there are more than one result,
                and this one has a score that is >= GOOD SCORE,
                then ignore the rest of the results
            """
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

        if not self.call_item_api(update_helper):
            log.warn('Skipping metadata update: no valid Audnexus response')
            return

        self.compile_metadata(update_helper)

    def call_search_api(self, helper):
        """
            Builds URL then calls API, returns the JSON to helper function.
        """
        query = helper.build_search_args()
        search_url = helper.build_url(query)
        request = str(make_request(search_url))
        response = json_decode(request)
        results_list = helper.parse_api_response(response)
        return results_list

    def process_results(self, helper, result):
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
        """
            Calls Audnexus API to get book details,
            then calls helper to parse those details.
        """
        update_url = helper.build_url()
        request = make_api_request(update_url, helper.api_url)
        if request is None:
            log.error('No response from Audnexus (%s)' % describe_url(update_url))
            return False
        try:
            response = json_decode(str(request))
        except Exception:
            log.error('Invalid Audnexus response (%s)' % (
                describe_url(update_url)))
            return False
        if (not isinstance(response, dict) or
                'error' in response or 'asin' not in response):
            log.error('Invalid Audnexus response (%s)' % describe_url(update_url))
            return False
        helper.parse_api_response(response)
        self.fetch_artwork(helper)
        if store_similar_enabled(helper.prefs):
            self.fetch_similar(helper)

        # Set date to date object
        helper.date = self.getDateFromString(helper.date)
        return True

    def fetch_artwork(self, helper):
        """
            Fetches retained artwork for the Plex poster picker.
        """
        artwork_url = helper.build_artwork_url()
        if not artwork_url:
            return
        try:
            response = make_api_request(artwork_url, helper.api_url)
            if response is None:
                helper.artwork_ok = False
                helper.artwork_urls = []
                helper.artwork_fallbacks = {}
                return
            helper.parse_artwork_response(json_decode(str(response)))
        except Exception:
            helper.artwork_ok = False
            helper.artwork_urls = []
            helper.artwork_fallbacks = {}
            log.error('Failed to fetch artwork history (%s)' % (
                describe_url(artwork_url)))

    def fetch_similar(self, helper):
        """
            Fetches similar books from the dedicated endpoint.
        """
        similar_url = helper.build_similar_url()
        if not similar_url:
            return
        try:
            response = make_api_request(similar_url, helper.api_url)
            if response is None:
                return
            helper.parse_similar_response(json_decode(str(response)))
        except Exception:
            log.error('Failed to fetch similar books (%s)' % (
                describe_url(similar_url)))

    def compile_metadata(self, helper):
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
        poster_urls = []
        history_urls = [url for url in helper.artwork_urls if url]
        if helper.poster_order == 'Oldest historical cover':
            history_urls.reverse()
            history_urls = history_urls[:MAX_HISTORY_POSTERS]
            poster_urls.extend(history_urls)
            if helper.thumb:
                poster_urls.append(helper.thumb)
        elif helper.poster_order == 'Largest resolution cover':
            history_urls.sort(
                key=lambda url: helper.artwork_sizes.get(url, 0),
                reverse=True
            )
            history_urls = history_urls[:MAX_HISTORY_POSTERS]
            ranked = []
            for url in history_urls:
                ranked.append((helper.artwork_sizes.get(url, 0), url))
            if helper.thumb:
                ranked.append((helper.current_artwork_size, helper.thumb))
            ranked.sort(key=lambda item: item[0], reverse=True)
            poster_urls = [url for size, url in ranked]
        else:
            if helper.thumb:
                poster_urls.append(helper.thumb)
            poster_urls.extend(history_urls[:MAX_HISTORY_POSTERS])
        unique_urls = []
        for url in poster_urls:
            if url and url not in unique_urls:
                unique_urls.append(url)
        poster_urls = unique_urls

        def fetch_poster(url, fallback, skip_fallback=False):
            data = make_artwork_request(url, helper.api_url)
            if data is not None:
                return url, data
            if fallback and not skip_fallback:
                data = make_artwork_request(fallback, helper.api_url)
                if data is not None:
                    return fallback, data
            return None, None

        available_urls = []

        def set_cached_order(url, order):
            if url in available_urls:
                return
            try:
                helper.metadata.posters[url].sort_order = order
            except Exception:
                pass

        def append_available(url):
            if url and url not in available_urls:
                available_urls.append(url)
        for index, url in enumerate(poster_urls):
            fallback = helper.artwork_fallbacks.get(url)
            cached_url = None
            if url in helper.metadata.posters:
                cached_url = url
            elif fallback and fallback in helper.metadata.posters:
                cached_url = fallback
            if cached_url:
                retry = helper.force or index == 0 or cached_url != url
                if retry:
                    poster_url, data = fetch_poster(
                        url, fallback,
                        skip_fallback=(cached_url == fallback and
                                        not helper.force))
                    if data is not None:
                        if poster_url in available_urls:
                            append_available(poster_url)
                        else:
                            try:
                                helper.metadata.posters[poster_url] = Proxy.Media(
                                    data, sort_order=index
                                )
                                append_available(poster_url)
                            except Exception:
                                log.error('Failed to refresh poster (%s)' % (
                                    describe_artwork_url(poster_url)))
                                set_cached_order(cached_url, index)
                                append_available(cached_url)
                    else:
                        set_cached_order(cached_url, index)
                        append_available(cached_url)
                else:
                    set_cached_order(cached_url, index)
                    append_available(cached_url)
                continue
            poster_url, data = fetch_poster(url, fallback)
            if data is None:
                continue
            if poster_url in available_urls:
                append_available(poster_url)
                continue
            try:
                helper.metadata.posters[poster_url] = Proxy.Media(
                    data, sort_order=index
                )
                append_available(poster_url)
            except Exception:
                log.error('Failed to fetch poster (%s)' % (
                    describe_artwork_url(poster_url)))

        if available_urls:
            if helper.artwork_ok:
                validate_keys = available_urls
            else:
                # Artwork history is unavailable. Keep existing posters but
                # put the current cover first.
                validate_keys = []
                if helper.thumb in helper.metadata.posters:
                    validate_keys.append(helper.thumb)
                for poster_url in helper.metadata.posters:
                    if poster_url not in validate_keys:
                        validate_keys.append(poster_url)
            # The first poster in the ordered collection is the default.
            helper.metadata.posters.validate_keys(validate_keys)
        # Rating.
        helper.set_metadata_rating()

        # Log the resulting metadata
        helper.log_update_metadata()

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


# Common helpers

def json_decode(output):
    """
        Decodes JSON output.
    """
    try:
        return json.loads(output, encoding="utf-8")
    except AttributeError:
        return None


def get_header(headers, name):
    """
        Reads a header without assuming dict.get is available.
    """
    try:
        return headers[name]
    except (KeyError, TypeError, AttributeError):
        return None


def make_api_request(url, api_url):
    """
        Fetches an Audnexus API URL, following redirects only within the
        configured API origin.
    """
    api_origin = get_url_origin(api_url)
    for _ in range(0, 5):
        if api_origin is None or get_url_origin(url) != api_origin:
            log.warn('Rejected API URL (%s)' % describe_url(url))
            return None
        try:
            response = HTTP.Request(
                url, timeout=90, sleep=1, follow_redirects=False
            )
            location = (get_header(response.headers, 'Location') or
                        get_header(response.headers, 'location'))
        except Exception as err:
            # Plex raises RedirectError instead of returning the 3xx
            # response when follow_redirects is False. Follow its Location
            # manually; the next loop checks the configured API origin.
            try:
                location = err.location
            except (AttributeError, KeyError, TypeError):
                location = None
            if location:
                url = urljoin(url, location)
                continue
            log.error('API request failed (%s)' % describe_url(url))
            return None
        if location:
            url = urljoin(url, location)
            continue
        return response
    log.error('Too many API redirects (%s)' % describe_url(url))
    return None


def make_artwork_request(url, api_url):
    """
        Fetches an approved artwork URL and validates each redirect.
    """
    for _ in range(0, 5):
        if not is_approved_artwork_url(url, api_url):
            log.warn('Rejected artwork URL (%s)' % describe_artwork_url(url))
            return None
        try:
            response = HTTP.Request(
                url, timeout=90, sleep=1, follow_redirects=False
            )
            location = (get_header(response.headers, 'Location') or
                        get_header(response.headers, 'location'))
            content_type = (get_header(response.headers, 'Content-Type') or
                            get_header(response.headers, 'content-type') or '')
            try:
                status = response.status
            except AttributeError:
                status = None
            if status is not None:
                try:
                    status = int(status)
                except (TypeError, ValueError):
                    status = None
        except Exception as err:
            # Plex raises RedirectError instead of returning the 3xx
            # response when follow_redirects is False. Follow its Location
            # manually so every hop still passes the approved-host check.
            try:
                location = err.location
            except (AttributeError, KeyError, TypeError):
                location = None
            if location:
                url = urljoin(url, location)
                continue
            log.error('Artwork request failed (%s)' % (
                describe_artwork_url(url)))
            return None
        if location and (status is None or 300 <= status < 400):
            url = urljoin(url, location)
            continue
        if status is not None and status >= 400:
            log.warn('Artwork request returned %s (%s)' % (
                status, describe_artwork_url(url)))
            return None
        if content_type and not content_type.lower().startswith('image/'):
            log.warn('Artwork response is not an image (%s)' % (
                describe_artwork_url(url)))
            return None
        return response
    log.error('Too many artwork redirects (%s)' % describe_artwork_url(url))
    return None


def make_request(url):
    """
        Makes and returns an HTTP request.
        Retries 4 times, increasing  time between each retry.
    """
    sleep_time = 1
    num_retries = 4
    for x in range(0, num_retries):
        try:
            make_request = HTTP.Request(url, timeout=90, sleep=sleep_time)
            str_error = None
            ssl_error = None
        except Exception as str_error:
            log.error("Failed http request attempt #" + x + ": " + url)
            log.error(str_error)
        except SSLError as ssl_error:
            log.error("Failed http request attempt #" + x + ": " + url)
            log.error(ssl_error)

        if str_error or ssl_error:
            sleep(sleep_time)
            sleep_time *= x
        else:
            break
    return make_request
