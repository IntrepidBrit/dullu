import json

import os
import random
from dullu import dullu
from dullu.HTTPStatus import HTTPStatus


def test_get_all_urls():
    """
    The function responsible for grabbing all the links from a block of text, and putting them into a list of links
    :return: None
    """
    assert dullu.get_all_links("") == []

    assert dullu.get_all_links("""Lorem ipsum dolor sit amet, consectetur adipiscing elit. Quisque sodales faucibus
    elementum. Mauris rutrum interdum turpis, id convallis nibh porttitor et. Pellentesque ultrices tortor ut leo
    fermentum sollicitudin. Donec urna ipsum, blandit sit amet posuere quis, suscipit a orci. Mauris vel ex et tortor
    lacinia tincidunt at id turpis. Pellentesque dapibus, risus eu aliquet ornare, nisl lorem porttitor eros, vel auctor
    nisl ante vestibulum ipsum. Ut iaculis arcu quis interdum facilisis. Pellentesque non mollis ante, vitae semper sapien.
    Proin malesuada nisl at nulla sodales ultrices. Sed eget fermentum velit. Cras sed turpis pharetra, consectetur
    mauris non, sollicitudin elit. Etiam non magna lacus. Mauris gravida urna sit amet rutrum malesuada. Nulla ultricies
    eros vel nunc ornare maximus. Duis vitae arcu sit amet quam varius accumsan et ac dui. Morbi varius volutpat nulla,
    non venenatis libero dictum vel. Donec quis massa libero. Proin vitae efficitur est, nec posuere ligula. Nullam quis
    ligula.""") == []

    assert dullu.get_all_links("""<html><head><title>Hello World!</title></head><body><h1>Hello World!</h1><p>I like
                                turtles</p></body></html>""") == []

    assert dullu.get_all_links("<a href=\"http://stackoverflow.com/a/1732454/1241495\">issit zalgo?</a>") != \
           ["http://stackoverflow.com/a/2504454/673991"]

    assert dullu.get_all_links("<a href=\"http://stackoverflow.com/a/1732454/1241495\">oh, noes zalgo!</a>") == \
           ["http://stackoverflow.com/a/1732454/1241495"]

    f = open(os.path.join(os.path.dirname(__file__), 'data', 'test_question.json'), 'r')
    try:
        assert dullu.get_all_links(json.load(f)['Body']) == \
               ['http://c-faq.com/stdio/scanfprobs.html',
                'http://c-faq.com/stdio/getsvsfgets.html',
                'http://stackoverflow.com/questions/9378500/why-is-splitting-a-string-slower-in-c-than-python']
    finally:
        f.close()


def test_get_link_status_code():
    """
    The function responsible for trying to grab the status code of the link
    :return: None
    """

    assert dullu.get_link_status_code("") == HTTPStatus.BAD_REQUEST
    assert dullu.get_link_status_code("sopython.com") == HTTPStatus.BAD_REQUEST
    assert dullu.get_link_status_code("http://sopython.com") == HTTPStatus.OK
    assert dullu.get_link_status_code("http://ww.thiswebsiteshouldneverexistyo.roflbob") == HTTPStatus.NOT_FOUND

    # Can take a long time.
    for i in range(0,3):
        test_status = random.choice(list(HTTPStatus))
        assert dullu.get_link_status_code("http://httpstat.us/{code}".format(code=test_status.value)) == test_status

