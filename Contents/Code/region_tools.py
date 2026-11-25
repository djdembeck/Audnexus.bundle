try:
    from urlparse import urlparse
except ImportError:
    from urllib.parse import urlparse

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


DEFAULT_API_URL = 'https://api.audnex.us'


def get_api_url(prefs):
    """
        Returns the configured Audnexus API base URL.
    """
    try:
        api_url = prefs['api_url']
    except (KeyError, TypeError):
        api_url = None
    return (api_url or '').strip().rstrip('/') or DEFAULT_API_URL


APPROVED_ARTWORK_HOSTS = (
    'm.media-amazon.com',
    'images-na.ssl-images-amazon.com',
    'images-eu.ssl-images-amazon.com',
    'images-ca.ssl-images-amazon.com',
    'images-fe.ssl-images-amazon.com',
    'images-jp.ssl-images-amazon.com',
)


def get_url_origin(url):
    """
        Returns (scheme, host, port) for a URL, or None when invalid.
    """
    try:
        parsed = urlparse(url)
        if parsed.username or parsed.password:
            return None
        scheme = (parsed.scheme or '').lower()
        host = (parsed.hostname or '').lower()
        if scheme not in ('http', 'https') or not host:
            return None
        port = parsed.port
        if port is None:
            port = 443 if scheme == 'https' else 80
        if not isinstance(port, int) or port <= 0 or port > 65535:
            return None
        return (scheme, host, port)
    except (TypeError, ValueError, AttributeError):
        return None


def is_approved_artwork_url(url, api_url):
    """
        Returns True when an artwork URL targets an approved origin.
    """
    origin = get_url_origin(url)
    if origin is None:
        return False
    if (origin[0] == 'https' and
            origin[1] in APPROVED_ARTWORK_HOSTS and
            origin[2] == 443):
        return True
    return origin == get_url_origin(api_url)


def describe_url(url):
    """
        Returns a log-safe origin for a URL.
    """
    origin = get_url_origin(url)
    if origin:
        return '%s://%s:%s' % origin
    return 'invalid URL'


class RegionTool:
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
        base_url : str, optional
            Audnexus API base URL. Defaults to the public API.
    """

    def __init__(self, region, content_type, id=None, query=None, base_url=None):
        self.region = region
        self.id = id
        self.query = query
        self.content_type = content_type
        self.base_url = (base_url or DEFAULT_API_URL).strip().rstrip('/')

    def get_region(self):
        """
            Returns the region code.
        """
        return self.region

    def get_region_name(self):
        """
            Returns the region name.
        """
        return available_regions[self.region]['name']

    # Audnexus
    def get_region_query(self):
        """
            Returns the region query string.
        """
        return '?region=' + self.region

    def get_region_tld(self):
        """
            Returns the region TLD.
        """
        return available_regions[self.region]['TLD']

    def get_content_type_url(self):
        """
            Returns the content type URL.
        """
        return self.base_url + '/' + self.content_type

    def get_search_url(self):
        """
            Returns the search URL.
        """
        return self.get_content_type_url() + self.get_region_query() + '&' + self.query

    def get_id_url(self):
        """
            Returns the ID URL.
        """
        return self.get_content_type_url() + '/' + self.id + self.get_region_query()

    def get_id_url_with_query(self):
        """
            Returns the ID URL with query.
        """
        return self.get_content_type_url() + '/' + self.id + self.get_region_query() + '&' + self.query

    # Audible
    def get_api_region_url(self):
        """
            Returns the API region URL.
        """
        return 'https://api.audible.{}'.format(
            available_regions[self.region]['TLD']
        )

    def get_api_params(self):
        """
            Returns the API parameters.
        """
        return (
            '?response_groups=contributors,product_desc,product_attrs'
            '&num_results=25&products_sort_by=Relevance'
        )

    def get_api_search_url(self):
        """
            Returns the API search URL.
        """
        return self.get_api_region_url() + '/' + '1.0/catalog/products' + self.get_api_params() + '&' + self.query
