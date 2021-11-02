# Audnexus Agent
# coding: utf-8
import json
import re
# Import internal tools
from _version import version
from logging import Logging
from search_tools import AlbumSearchTool, ArtistSearchTool, ScoreTool
from time import sleep
from update_tools import AlbumUpdateTool, ArtistUpdateTool, TagTool

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
        'fr',
        'it'
    ]
    primary_provider = True
    accepts_from = ['com.plexapp.agents.localmedia']

    prev_search_provider = 0

    def search(self, results, media, lang, manual):
        # Instantiate search helper
        search_helper = ArtistSearchTool(lang, manual, media, results)

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
        log.separator(
            msg=(
                "UPDATING: " + media.title + (
                    " ID: " + metadata.id
                )
            ),
            log_level="info"
        )

        # Instantiate update helper
        update_helper = ArtistUpdateTool(force, lang, media, metadata)

        self.call_item_api(update_helper)

        # cleanup description
        update_helper.description = (
            update_helper.description.replace("<i>", "")
            .replace("</i>", "")
            .replace("<em>", "")
            .replace("</em>", "")
            .replace("<u>", "")
            .replace("</u>", "")
            .replace("<b>", "")
            .replace("</b>", "")
            .replace("<strong>", "")
            .replace("</strong>", "")
            .replace("<ul>", "")
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

        self.compile_metadata(update_helper)

    def call_search_api(self, helper):
        """
            Builds URL then calls API, returns the JSON to helper function.
        """
        search_url = helper.build_url()
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
        request = str(make_request(
            helper.UPDATE_URL + helper.metadata.id
        ))
        response = json_decode(request)
        helper.parse_api_response(response)

    def compile_metadata(self, helper):
        # Description.
        if not helper.metadata.summary or helper.force:
            helper.metadata.summary = helper.description
        tagger = TagTool(helper, Prefs, re)
        # Genres.
        tagger.add_genres()
        # Title.
        if not helper.metadata.title or helper.force:
            helper.metadata.title = helper.name
        # Sort Title.
        if not helper.metadata.title_sort or helper.force:
            if Prefs['sort_author_by_last_name'] and not (
                # Handle single word names
                re.match(r'\A[\w-]+\Z', helper.name)
            ):
                split_author_surname = re.match(
                    '^(.+?).([^\s,]+)(,?.(?:[JS]r\.?|III?|IV))?$',
                    helper.name,
                )
                helper.metadata.title_sort = ', '.join(
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
                helper.metadata.title_sort = helper.metadata.title
        # Thumb.
        if helper.thumb:
            if helper.thumb not in helper.metadata.posters or helper.force:
                helper.metadata.posters[helper.thumb] = Proxy.Media(
                    make_request(helper.thumb), sort_order=0
                )

        helper.writeInfo()

    def hasProxy(self):
        return Prefs['imageproxyurl'] is not None

    def makeProxyUrl(self, url, referer):
        return Prefs['imageproxyurl'] + ('?url=%s&referer=%s' % (url, referer))

class AudiobookAlbum(Agent.Album):
    name = 'Audnexus Agent'
    languages = [
        Locale.Language.English,
        'de',
        'fr',
        'it'
    ]
    primary_provider = True
    accepts_from = ['com.plexapp.agents.localmedia']

    prev_search_provider = 0

    def search(self, results, media, lang, manual):
        # Instantiate search helper
        search_helper = AlbumSearchTool(lang, manual, media, results)

        pre_check = search_helper.pre_search_logging()
        # Purposefully terminate search if it's bad
        if not pre_check:
            log.debug("Didn't pass pre-check")
            return

        # Run helper before passing to AlbumSearchTool
        normalizedName = String.StripDiacritics(
            search_helper.media.album
        )
        # Strip title of things like unabridged and spaces
        search_helper.strip_title(normalizedName)
        # # Validate author name
        search_helper.validate_author_name()

        # Call search API
        result = self.call_search_api(search_helper)

        # Write search result status to log
        if not result:
            log.warn(
                'No results found for query "%s"',
                normalizedName
            )
            return
        log.debug(
            'Found %s result(s) for query "%s"',
            len(result),
            normalizedName
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
        log.separator(
            msg=(
                "UPDATING: " + media.title + (
                    " ID: " + metadata.id
                )
            ),
            log_level="info"
        )

        # Instantiate update helper
        update_helper = AlbumUpdateTool(force, lang, media, metadata)

        self.call_item_api(update_helper)

        # cleanup synopsis
        update_helper.synopsis = (
            update_helper.synopsis.replace("<i>", "")
            .replace("</i>", "")
            .replace("<em>", "")
            .replace("</em>", "")
            .replace("<u>", "")
            .replace("</u>", "")
            .replace("<b>", "")
            .replace("</b>", "")
            .replace("<strong>", "")
            .replace("</strong>", "")
            .replace("<ul>", "")
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

        self.compile_metadata(update_helper)

    def call_search_api(self, helper):
        """
            Builds URL then calls API, returns the JSON to helper function.
        """
        search_url = helper.build_url()
        request = str(make_request(search_url))
        response = json_decode(request)
        results_list = helper.parse_api_response(response)
        return results_list

    def process_results(self, helper, result):
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
        request = str(make_request(
            helper.UPDATE_URL + helper.metadata.id
        ))
        response = json_decode(request)
        helper.parse_api_response(response)

        # Set date to date object
        helper.date = self.getDateFromString(helper.date)

    def compile_metadata(self, helper):
        # Date.
        if helper.date is not None:
            if not helper.metadata.originally_available_at or helper.force:
                helper.metadata.originally_available_at = helper.date
        tagger = TagTool(helper, Prefs, re)
        # Genres.
        tagger.add_genres()
        # Narrators.
        tagger.add_narrators_to_styles()
        # Authors.
        if Prefs['store_author_as_mood']:
            tagger.add_authors_to_moods()
        # Series.
        tagger.add_series_to_moods()
        # Setup title + subtitle where available.
        if helper.subtitle:
            album_title = helper.title + ': ' + helper.subtitle
        else:
            album_title = helper.title
        # Title.
        if not helper.metadata.title or helper.force:
            helper.metadata.title = album_title
        # Sort Title.
        # Add series/volume to sort title where possible.
        series_with_volume = ''
        if helper.series and helper.volume:
            series_with_volume = helper.series + ', ' + helper.volume
        # Only include subtitle in sort if not in a series
        if not helper.volume:
            helper.title = album_title
        if not helper.metadata.title_sort or helper.force:
            helper.metadata.title_sort = ' - '.join(
                filter(
                    None, [(series_with_volume), helper.title]
                )
            )
        # Studio.
        if not helper.metadata.studio or helper.force:
            helper.metadata.studio = helper.studio
        # Summary.
        if not helper.metadata.summary or helper.force:
            helper.metadata.summary = helper.synopsis
        # Thumb.
        if helper.thumb:
            if helper.thumb not in helper.metadata.posters or helper.force:
                helper.metadata.posters[helper.thumb] = Proxy.Media(
                    make_request(helper.thumb), sort_order=0
                )
        # Rating.
        # We always want to refresh the rating
        if helper.rating:
            helper.metadata.rating = float(helper.rating) * 2

        helper.writeInfo()

    def getDateFromString(self, string):
        try:
            return Datetime.ParseDate(string).date()
        except AttributeError:
            return None
        except ValueError:
            return None

    def hasProxy(self):
        return Prefs['imageproxyurl'] is not None

    def makeProxyUrl(self, url, referer):
        return Prefs['imageproxyurl'] + ('?url=%s&referer=%s' % (url, referer))


# Common helpers
def json_decode(output):
    try:
        return json.loads(output, encoding="utf-8")
    except AttributeError:
        return None


def make_request(url):
    """
        Makes and returns an HTTP request.
        Retries 4 times, increasing  time between each retry.
    """
    sleep_time = 2
    num_retries = 4
    for x in range(0, num_retries):
        try:
            make_request = HTTP.Request(url)
            str_error = None
        except Exception as str_error:
            log.error("Failed http request attempt #" + x + ": " + url)
            log.error(str_error)

        if str_error:
            sleep(sleep_time)
            sleep_time *= x
        else:
            break
    return make_request
