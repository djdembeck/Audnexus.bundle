# Audnexus Agent
# coding: utf-8
import json
import Queue
import re
# Import internal tools
from logging import Logging
from search_tools import AlbumSearchTool, ArtistSearchTool
from update_tools import AlbumUpdateTool, ArtistUpdateTool
from _version import version

VERSION_NO = version

# Starting value for score before deductions are taken.
INITIAL_SCORE = 100
# Score required to short-circuit matching and stop searching.
GOOD_SCORE = 98
# Any score lower than this will be ignored.
IGNORE_SCORE = 45

THREAD_MAX = 20

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
            "Audible Audiobooks Agent v" + VERSION_NO
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
            description = r['artist']

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

        # Setup logging of all data in the array
        data_to_log = [
            {'author': update_helper.name},
            {'description': update_helper.description},
            {'genres': ', '.join(
                genre['name'] for genre in update_helper.genres
            )},
            {'thumb': update_helper.thumb},
        ]
        log.metadata(data_to_log, log_level="debug")

        self.compile_metadata(update_helper)

    def call_search_api(self, helper):
        """
            Builds URL then calls API, returns the JSON to helper function.
        """
        search_url = helper.build_url()
        request = str(HTTP.Request(search_url, timeout=15))
        response = json_decode(request)
        results_list = helper.parse_api_response(response)
        return results_list

    def process_results(self, helper, result):
        # Walk the found items and gather extended information
        info = []

        log.separator(msg="Search results", log_level="info")
        for i, f in enumerate(result):
            self.score_result(f, helper, i, info)

            # Print separators for easy reading
            if i <= len(result):
                log.separator(log_level="info")

        info = sorted(info, key=lambda inf: inf['score'], reverse=True)
        return info

    def score_result(self, f, helper, i, info):
        asin = f['asin']
        author = f['name']

        # Array to hold score points for processing
        all_scores = []

        # Author name score
        author_score = self.score_author(helper, author)
        if author_score:
            all_scores.append(author_score)

        score = INITIAL_SCORE - author_score

        log.info("Result #" + str(i + 1))
        # Log basic metadata
        data_to_log = [
            {'ID is': asin},
            {'Author is': author},
            {'Score is': str(score)},
        ]
        log.metadata(data_to_log, log_level="info")

        if score >= IGNORE_SCORE:
            info.append(
                {
                    'id': asin,
                    'score': score,
                    'artist': author,
                }
            )
        else:
            log.info(
                '# Score is below ignore boundary (%s)... Skipping!',
                IGNORE_SCORE
            )

    def score_author(self, helper, author):
        """
            Compare the input author similarity to the search result author.
            Score is calculated with LevenshteinDistance
        """
        if helper.media.artist:
            scorebase3 = helper.media.artist
            scorebase4 = author
            author_score = Util.LevenshteinDistance(
                scorebase3.lower()
                .replace('-', '').replace(' ', '').replace('.', ''),
                scorebase4.lower()
                .replace('-', '').replace(' ', '').replace('.', '')
            )
            log.debug("Score deduction from author: " + str(author_score))
            return author_score

    def call_item_api(self, helper):
        """
            Calls Audnexus API to get author details,
            then calls helper to parse those details.
        """
        request = str(HTTP.Request(helper.UPDATE_URL + helper.metadata.id, timeout=15))
        response = json_decode(request)
        helper.parse_api_response(response)

    def compile_metadata(self, helper):
        # Description.
        if not helper.metadata.summary or helper.force:
            helper.metadata.summary = helper.description
        # Genres.
        self.add_genres(helper)
        # Title.
        if not helper.metadata.title or helper.force:
            helper.metadata.title = helper.name
        # Sort Title.
        if not helper.metadata.title_sort or helper.force:
            split_author_surname = re.match(
                '^(.+?).([^\s,]+)(,?.(?:[JS]r\.?|III?|IV))?$',
                helper.name,
            )
            helper.metadata.title_sort = (
                split_author_surname.group(2) + ', ' +
                split_author_surname.group(1)
            )
        # Thumb.
        if helper.thumb not in helper.metadata.posters or helper.force:
            helper.metadata.posters[helper.thumb] = Proxy.Media(
                HTTP.Request(helper.thumb, timeout=15), sort_order=0
            )

        helper.writeInfo()

    def add_genres(self, helper):
        """
            Add genre(s) to Plex genres where available and depending on preference.
        """
        if not Prefs['no_overwrite_genre']:
            if not helper.metadata.genres or helper.force:
                helper.metadata.genres.clear()
                for genre in helper.genres:
                    if genre['name']:
                        helper.metadata.genres.add(genre['name'])

    def hasProxy(self):
        return Prefs['imageproxyurl'] is not None

    def makeProxyUrl(self, url, referer):
        return Prefs['imageproxyurl'] + ('?url=%s&referer=%s' % (url, referer))

    def worker(self, queue, stoprequest):
        while not stoprequest.isSet():
            try:
                func, args, kargs = queue.get(True, 0.05)
                try:
                    func(*args, **kargs)
                except Exception as e:
                    log.error(e)
                queue.task_done()
            except Queue.Empty:
                continue

    def addTask(self, queue, func, *args, **kargs):
        queue.put((func, args, kargs))


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
        normalizedName = self.normalize_name(search_helper.media.album)
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
            artist_initials = self.name_to_initials(r['artist'])
            # Shorten narrator
            narrator_initials = self.name_to_initials(r['narrator'])

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

        # Setup logging of all data in the array
        data_to_log = [
            {'author': ', '.join(
                genre['name'] for genre in update_helper.author
            )},
            {'date': update_helper.date},
            {'genres': ', '.join(
                genre['name'] for genre in update_helper.genres
            )},
            {'narrator': ', '.join(
                genre['name'] for genre in update_helper.narrator
            )},
            {'rating': update_helper.rating},
            {'series': update_helper.series},
            {'series2': update_helper.series2},
            {'studio': update_helper.studio},
            {'synopsis': update_helper.synopsis},
            {'thumb': update_helper.thumb},
            {'title': update_helper.title},
        ]
        log.metadata(data_to_log, log_level="debug")

        self.compile_metadata(update_helper)

    """
        Search functions that require PMS imports,
        thus we cannot 'outsource' them to AlbumSearchTool
        Sorted by position in the search process
    """

    def normalize_name(self, input_name):
        # Normalize the name
        normalizedName = String.StripDiacritics(
            input_name
        )
        return normalizedName

    def name_to_initials(self, input_name):
        # Shorten input_name by splitting on whitespaces
        # Only the surname stays as whole, the rest gets truncated
        # and merged with dots.
        # Example: 'Arthur Conan Doyle' -> 'A.C.Doyle'
        name_parts = input_name.split()
        new_name = ""

        # Check if prename and surname exist, otherwise exit
        if len(name_parts) < 2:
            return input_name

        # traverse through prenames
        for i in range(len(name_parts)-1):
            s = name_parts[i]
            # If prename already is an initial take it as is
            new_name += (s[0] + '.') if len(s)>2 and s[1]!='.' else s
        # Add surname
        new_name += name_parts[-1]

        return new_name

    def call_search_api(self, helper):
        """
            Builds URL then calls API, returns the JSON to helper function.
        """
        search_url = helper.build_url()
        request = str(HTTP.Request(search_url, timeout=15))
        response = json_decode(request)
        results_list = helper.parse_api_response(response)
        return results_list

    def process_results(self, helper, result):
        # Walk the found items and gather extended information
        info = []

        log.separator(msg="Search results", log_level="info")
        for i, f in enumerate(result):
            date = self.getDateFromString(f['date'])
            year = ''
            if date is not None:
                year = date.year

                # Make sure this isn't a pre-order listing
                if helper.check_if_preorder(date):
                    continue

            self.score_result(f, helper, i, info, year)

            # Print separators for easy reading
            if i <= len(result):
                log.separator(log_level="info")

        info = sorted(info, key=lambda inf: inf['score'], reverse=True)
        return info

    def score_result(self, f, helper, i, info, year):
        asin = f['asin']
        author = f['author'][0]['name']
        date = f['date']
        language = f['language'].title()
        narrator = f['narrator'][0]['name']
        title = f['title']

        # Array to hold score points for processing
        all_scores = []

        # Album name score
        title_score = self.score_album(helper, title)
        if title_score:
            all_scores.append(title_score)
        # Author name score
        author_score = self.score_author(helper, author)
        if author_score:
            all_scores.append(author_score)
        # Library language score
        lang_score = self.score_language(helper, language)
        if lang_score:
            all_scores.append(lang_score)

        # Because builtin sum() isn't available
        sum_scores=lambda numberlist:reduce(lambda x,y:x+y,numberlist,0)
        # Subtract difference from initial score
        # Subtract index to use Audible relevance as weight
        score = INITIAL_SCORE - sum_scores(all_scores) - i

        log.info("Result #" + str(i + 1))
        # Log basic metadata
        data_to_log = [
            {'ID is': asin},
            {'Title is': title},
            {'Author is': author},
            {'Narrator is': narrator},
            {'Date is ': str(date)},
            {'Score is': str(score)},
        ]
        log.metadata(data_to_log, log_level="info")

        if score >= IGNORE_SCORE:
            info.append(
                {
                    'id': asin,
                    'title': title,
                    'year': year,
                    'date': date,
                    'score': score,
                    'artist': author,
                    'narrator': narrator
                }
            )
        else:
            log.info(
                '# Score is below ignore boundary (%s)... Skipping!',
                IGNORE_SCORE
            )

    def score_album(self, helper, title):
        """
            Compare the input album similarity to the search result album.
            Score is calculated with LevenshteinDistance
        """
        scorebase1 = helper.media.album
        scorebase2 = title.encode('utf-8')
        album_score = Util.LevenshteinDistance(
            scorebase1, scorebase2
        )
        log.debug("Score deduction from album: " + str(album_score))
        return album_score

    def score_author(self, helper, author):
        """
            Compare the input author similarity to the search result author.
            Score is calculated with LevenshteinDistance
        """
        if helper.media.artist:
            scorebase3 = helper.media.artist
            scorebase4 = author
            author_score = Util.LevenshteinDistance(
                scorebase3, scorebase4
            )
            log.debug("Score deduction from author: " + str(author_score))
            return author_score

    def score_language(self, helper, language):
        """
            Compare the library language to search results
            and knock off 2 points if they don't match.
        """
        lang_dict = {
            Locale.Language.English: 'English',
            'de': 'Deutsch',
            'fr': 'Français',
            'it': 'Italiano'
        }

        if language != lang_dict[helper.lang]:
            log.debug(
                'Audible language: %s; Library language: %s',
                language,
                lang_dict[helper.lang]
            )
            log.debug("Book is not library language, deduct 2 points")
            return 2
        return 0

    """
        Update functions that require PMS imports,
        thus we cannot 'outsource' them to AlbumUpdateTool
        Sorted by position in the update process
    """

    def call_item_api(self, helper):
        """
            Calls Audnexus API to get book details,
            then calls helper to parse those details.
        """
        request = str(HTTP.Request(helper.UPDATE_URL + helper.metadata.id, timeout=15))
        response = json_decode(request)
        helper.parse_api_response(response)

        # Set date to date object
        helper.date = self.getDateFromString(helper.date)

    def compile_metadata(self, helper):
        # Date.
        if helper.date is not None:
            if not helper.metadata.originally_available_at or helper.force:
                helper.metadata.originally_available_at = helper.date
        # Genres.
        self.add_genres(helper)
        # Narrators.
        self.add_narrators_to_styles(helper)
        # Authors.
        self.add_authors_to_moods(helper)
        # Series.
        self.add_series_to_moods(helper)
        # Title.
        if not helper.metadata.title or helper.force:
            helper.metadata.title = helper.title
        # Sort Title.
        # Add series/volume to sort title where possible.
        series_with_volume = ''
        if helper.series and helper.volume:
            series_with_volume = helper.series + ', ' + helper.volume
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
        if helper.thumb not in helper.metadata.posters or helper.force:
            helper.metadata.posters[helper.thumb] = Proxy.Media(
                HTTP.Request(helper.thumb, timeout=15), sort_order=0
            )
        # Rating.
        # We always want to refresh the rating
        if helper.rating:
            helper.metadata.rating = float(helper.rating) * 2

        helper.writeInfo()

    def add_genres(self, helper):
        """
            Add genre(s) to Plex genres where available and depending on preference.
        """
        if not Prefs['no_overwrite_genre']:
            if not helper.metadata.genres or helper.force:
                helper.metadata.genres.clear()
                for genre in helper.genres:
                    if genre['name']:
                        helper.metadata.genres.add(genre['name'])

    def add_narrators_to_styles(self, helper):
        """
            Adds narrators to styles.
        """
        if not helper.metadata.styles or helper.force:
            helper.metadata.styles.clear()
            for narrator in helper.narrator:
                helper.metadata.styles.add(narrator['name'].strip())

    def add_authors_to_moods(self, helper):
        """
            Adds authors to moods, except for cases in contibutors list.
        """
        author_contributers_list = [
            'contributor',
            'translator',
            'foreword',
            'translated',
        ]
        if not helper.metadata.moods or helper.force:
            helper.metadata.moods.clear()
            # Loop through authors to check if it has contributor wording
            for author in helper.author:
                if not [
                    contrib for contrib in author_contributers_list if (
                        contrib in author['name'].lower()
                    )
                ]:
                    helper.metadata.moods.add(author['name'].strip())

    def add_series_to_moods(self, helper):
        """
            Adds book series' to moods, since collections are not supported
        """
        if helper.series:
            helper.metadata.moods.add("Series: " + helper.series)
        if helper.series2:
            helper.metadata.moods.add("Series: " + helper.series2)

    """
        General helper/repeated use functions
        Sorted alphabetically
    """

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

    """
        Queueing functions
    """

    def worker(self, queue, stoprequest):
        while not stoprequest.isSet():
            try:
                func, args, kargs = queue.get(True, 0.05)
                try:
                    func(*args, **kargs)
                except Exception as e:
                    log.error(e)
                queue.task_done()
            except Queue.Empty:
                continue

    def addTask(self, queue, func, *args, **kargs):
        queue.put((func, args, kargs))


# Common helpers
def json_decode(output):
    try:
        return json.loads(output, encoding="utf-8")
    except AttributeError:
        return None
