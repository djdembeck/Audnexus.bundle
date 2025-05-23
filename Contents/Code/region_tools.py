try:
    import plexhints  # noqa: F401
except ImportError:
    pass
else:
    from plexhints.prefs_kit import Prefs
available_regions = {
    'au': {
        'name': 'Australia',
        'TLD': 'com.au',
    },
    'ca': {
        'name': 'Canada',
        'TLD': 'ca',
    },
    'de': {
        'name': 'Germany',
        'TLD': 'de',
    },
    'es': {
        'name': 'Spain',
        'TLD': 'es',
    },
    'fr': {
        'name': 'France',
        'TLD': 'fr',
    },
    'in': {
        'name': 'India',
        'TLD': 'in',
    },
    'it': {
        'name': 'Italy',
        'TLD': 'it',
    },
    'jp': {
        'name': 'Japan',
        'TLD': 'co.jp',
    },
    'us': {
        'name': 'United States',
        'TLD': 'com',
    },
    'uk': {
        'name': 'United Kingdom',
        'TLD': 'co.uk',
    }
}


class RegionTool(object):
    """
        Used to generate URLs for different regions for both Audible and Audnexus.

        Parameters
        ----------
        type : str
            The base type, e.g. 'authors' or 'books'
        id : str, optional
            The ASIN of the item to lookup. Can be None.
        query : str, optional
            Any additional query parameters to add to the URL. Can be None.
            Must be pre-formatted for Audnexus, e.g. '&page=1&limit=10'
        region : str
            The region code to generate the URL for.
    """

    def __init__(self, region, content_type, id=None, query=None):
        # type: (str, str, str, str) -> None
        self.region = region
        self.id = id
        self.query = query
        self.content_type = content_type
        self.backup_api = BackupRegionTool(region, content_type, id, query)

    def get_region(self):
        # type: () -> str
        """
            Returns the region code.
        """
        return self.region

    def get_region_name(self):
        # type: () -> str
        """
            Returns the region name.
        """
        return available_regions[self.region]['name']

    # Audnexus
    def get_region_query(self):
        # type: () -> str
        """
            Returns the region query string.
        """
        return '?region=' + self.region

    def get_region_tld(self):
        # type: () -> str
        """
            Returns the region TLD.
        """
        return available_regions[self.region]['TLD']

    def get_content_type_url(self):
        # type: () -> str
        """
            Returns the content type URL.
        """
        return Prefs["audnex_api_url"] + '/' + self.content_type

    def get_search_url(self):
        # type: () -> str
        """
            Returns the search URL.
        """
        if self.content_type == 'books':
            return self.get_api_search_url()
        return self.get_content_type_url() + self.get_region_query() + '&' + self.query

    def get_id_url(self):
        # type: () -> str
        """
            Returns the ID URL.
        """
        return self.get_content_type_url() + '/' + self.id + self.get_region_query()

    def get_id_url_with_query(self):
        # type: () -> str
        """
            Returns the ID URL with query.
        """
        return self.get_content_type_url() + '/' + self.id + self.get_region_query() + '&' + self.query

    # Audible
    def get_api_region_url(self):
        # type: () -> str
        """
            Returns the API region URL.
        """
        return 'https://api.audible.{}'.format(
            available_regions[self.region]['TLD']
        )

    def get_api_params(self):
        # type: () -> str
        """
            Returns the API parameters.
        """
        return (
            '?response_groups=contributors,product_desc,product_attrs'
            '&num_results=25&products_sort_by=Relevance'
        )

    def get_api_search_url(self):
        # type: () -> str
        """
            Returns the API search URL.
        """
        return self.get_api_region_url() + '/' + '1.0/catalog/products' + self.get_api_params() + '&' + self.query


class BackupRegionTool(object):
    """
        Used to generate URLs for different regions for both Audible and Audnexus.

        Parameters
        ----------
        type : str
            The base type, e.g. 'authors' or 'books'
        id : str, optional
            The ASIN of the item to lookup. Can be None.
        query : str, optional
            Any additional query parameters to add to the URL. Can be None.
            Must be pre-formatted for Audnexus, e.g. '&page=1&limit=10'
        region : str
            The region code to generate the URL for.
    """

    def __init__(self, region, content_type, id=None, query=None):
        # type: (str, str, str, str) -> None
        self.region = region
        self.id = id
        self.query = query
        if content_type == 'books':
            self.content_type = 'book'
        elif content_type == 'authors':
            self.content_type = 'author'

    def get_region(self):
        # type: () -> str
        """
            Returns the region code.
        """
        return self.region

    def get_region_name(self):
        # type: () -> str
        """
            Returns the region name.
        """
        return available_regions[self.region]['name']

    # Audnexus
    def get_region_query(self):
        # type: () -> str
        """
            Returns the region query string.
        """
        return '?region=' + self.region

    def get_region_tld(self):
        # type: () -> str
        """
            Returns the region TLD.
        """
        return available_regions[self.region]['TLD']

    def get_content_type_url(self):
        # type: () -> str
        """
            Returns the content type URL.
        """
        return Prefs["audimeta_api_url"] + '/' + self.content_type

    def get_book_search_url(self):
        # type: () -> str
        """
            Returns the search URL.
        """
        return Prefs["audimeta_api_url"]+'/search' + self.get_region_query() + '&' + self.query

    def get_search_url(self):
        # type: () -> str
        """
            Returns the search URL.
        """
        if self.content_type == 'book':
            return Prefs["audimeta_api_url"]+'/search' + self.get_region_query() + '&' + self.query
        return self.get_content_type_url() + self.get_region_query() + '&' + self.query

    def get_id_url(self):
        # type: () -> str
        """
            Returns the ID URL.
        """
        return self.get_content_type_url() + '/' + self.id + self.get_region_query()

    def get_id_url_with_query(self):
        # type: () -> str
        """
            Returns the ID URL with query.
        """
        return self.get_content_type_url() + '/' + self.id + self.get_region_query() + '&' + self.query

    def disable_cache(self):
        # type: () -> None
        """
            Disables the cache for the current region.
        """
        self.query + '&cache=false'
