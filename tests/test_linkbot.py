from urllib.error import URLError
from urllib.parse import urlparse

import pytest
from HTTPStatus import HTTPStatus
from dullu.linkbot import Linkbot


class FakeChannel:
    rejected = False
    requeue = None

    def reject(self, delivery_tag, requeue):
        self.rejected = True
        self.requeue = requeue


class FakeMethod:
    delivery_tag = 1


class FakeProperties:
    pass


class FakeBody:
    def __init__(self,test_decode_string=''):
        self.test_decode_string = test_decode_string

    def decode(self):
        return self.test_decode_string


def reset_callback_params():
    return FakeChannel(), FakeMethod(), FakeProperties(), FakeBody()


def test_linkbot_callback():
    GOOD_JSON = "[{\"entity_id\":\"577ba51b718a354034a91737\",\"url\":\"http://placehold.it/32x32\"}]"
    BAD_JSON = "[OMFG,I<3radish"

    ch, method, properties, body = reset_callback_params()
    body.test_decode_string = BAD_JSON
    Linkbot.callback_check_url(ch, method, properties, body)
    assert ch.rejected

    ch, method, properties, body = reset_callback_params()
    body.test_decode_string = GOOD_JSON
    Linkbot.callback_check_url(ch, method, properties, body)
    assert not ch.rejected


URL_GOOD = 'http://sopython.com/salad/'
URL_DENY = 'http://sopython.com/auth/'
URL_404 = 'http://sopython.com/intrepidissuperool/'
URL_BAD_DOMAIN = 'http://iudrno5teu95e95ew09e5w9.4397by34t983vb9834ybt9v83yt987y549877340834io.co.uk/cheesayyyy/'


def test_check_robots_txt():

    lb = Linkbot()
    assert lb.check_robots_txt(urlparse(URL_GOOD))
    assert lb.check_robots_txt(urlparse(URL_DENY)) == False
    assert lb.check_robots_txt(urlparse(URL_404)) == True  # Even if it doesn't exist, it's allowed by robots.txt
    with pytest.raises(URLError):
        lb.check_robots_txt(urlparse(URL_BAD_DOMAIN))


def test_get_url_status_code():
    lb = Linkbot()
    assert lb.get_url_status_code(URL_GOOD) == HTTPStatus.OK
    assert lb.get_url_status_code(URL_DENY) == HTTPStatus.NO_INDEX
    assert lb.get_url_status_code(URL_404) == HTTPStatus.NOT_FOUND
    assert lb.get_url_status_code(URL_BAD_DOMAIN) == HTTPStatus.DNS_LOOKUP_FAILED

if __name__ == '__main__':
    pytest.main(args=['-s', __file__])
