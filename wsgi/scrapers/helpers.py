import gzip
from StringIO import StringIO
from eventlet.green import urllib2
import ext

def openurl(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/27.0.1453.110 Safari/537.36',
        'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.6,en;q=0.4',
        'Accept-Encoding': 'gzip,deflate',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Cache-Control': 'max-age=0'
    }

    opener = urllib2.build_opener()
    opener.addheaders = headers.items()
    response = opener.open(ext.iriToUri(url))

    if response.info().get('Content-Encoding') == 'gzip':
        buf = StringIO(response.read())
        response = gzip.GzipFile(fileobj=buf)

    page = response.read()
    return page