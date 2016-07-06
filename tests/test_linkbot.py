import time
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

    test_decode_string = None

    def decode(self):
        return self.test_decode_string


def reset_callback_params():
    return FakeChannel(), FakeMethod(), FakeProperties(), FakeBody()


def test_linkbot_callback():
    JSON__GOOD = "{\"entity_id\":\"1\",\"entity_type\":\"q\",\"url\":\"http://sopython.com/salad/\",\"last_stamp\":\"33\",\"attempts\":\"0\"}"
    JSON__TOOSOON = "{{\"entity_id\":\"2\",\"entity_type\":\"q\",\"url\":\"http://sopython.com/salad/\",\"last_stamp\":\"{0}\",\"attempts\":\"0\"}}".format(int(time.time()))
    JSON__NOID = "{\"entity_type\":\"q\",\"url\":\"http://sopython.com/salad/\",\"attempts\":\"0\"}"
    JSON__NOURL = "{\"entity_id\":\"4\",\"entity_type\":\"q\",\"attempts\":\"0\"}"
    JSON__NOTYPE = "{\"entity_id\":\"5\",\"url\":\"http://sopython.com/salad/\",\"attempts\":\"0\"}"
    JSON__NOATTEMPTS_KEY = "{\"entity_id\":\"6\",\"entity_type\":\"q\",\"url\":\"http://sopython.com/salad/\"}"
    JSON__TOOMANYATTEMPTS = "{{\"entity_id\":\"7\",\"entity_type\":\"q\",\"url\":\"http://sopython.com/salad/\",\"attempts\":\"{0}\"}}".format(Linkbot.ATTEMPTS_THRESHOLD + 1)
    JSON__INVALID = "[OMFG,I<3radish"


    ch, method, properties, body = reset_callback_params()
    body.test_decode_string = JSON__INVALID
    Linkbot.callback_check_url(ch, method, properties, body)
    assert ch.rejected
    assert not ch.requeue

    ch, method, properties, body = reset_callback_params()
    body.test_decode_string = JSON__NOID
    Linkbot.callback_check_url(ch, method, properties, body)
    assert ch.rejected
    assert not ch.requeue

    ch, method, properties, body = reset_callback_params()
    body.test_decode_string = JSON__NOURL
    Linkbot.callback_check_url(ch, method, properties, body)
    assert ch.rejected
    assert not ch.requeue

    ch, method, properties, body = reset_callback_params()
    body.test_decode_string = JSON__NOTYPE
    Linkbot.callback_check_url(ch, method, properties, body)
    assert ch.rejected
    assert not ch.requeue

    ch, method, properties, body = reset_callback_params()
    body.test_decode_string = JSON__TOOMANYATTEMPTS
    Linkbot.callback_check_url(ch, method, properties, body)
    assert ch.rejected
    assert not ch.requeue

    ch, method, properties, body = reset_callback_params()
    body.test_decode_string = JSON__TOOSOON
    Linkbot.callback_check_url(ch, method, properties, body)
    assert ch.rejected
    assert ch.requeue

    ch, method, properties, body = reset_callback_params()
    body.test_decode_string = JSON__NOATTEMPTS_KEY
    Linkbot.callback_check_url(ch, method, properties, body)
    assert not ch.rejected
    assert not ch.requeue

    ch, method, properties, body = reset_callback_params()
    body.test_decode_string = JSON__GOOD
    Linkbot.callback_check_url(ch, method, properties, body)
    assert not ch.rejected
    assert ch.requeue is None


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
