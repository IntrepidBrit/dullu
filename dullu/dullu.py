# -*- coding: utf-8 -*-
import http.client
import socket
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from dullu.HTTPStatus import HTTPStatus


def get_all_links(s):
    """
    Find all the urls in the text and stick them in a list for later processing.

    :param s: Input string
    :return: List of links
    """
    soup = BeautifulSoup(s, "html.parser")
    return [link.get('href') for link in soup.find_all('a')]


def get_link_status_code(link):
    """

    :param link: a string containing an url
    :return:
    """
    # noinspection PyArgumentList
    try:
        parsed_link = urlparse(link)
        conn = http.client.HTTPConnection(parsed_link.netloc)
        conn.request("HEAD", parsed_link.path)
        return HTTPStatus(conn.getresponse().status,)
    except http.client.BadStatusLine:
        return HTTPStatus.BAD_REQUEST
    except socket.gaierror as e:
        if e.errno == 11001:
            # Technically speaking, a HTTP status code doesn't make sense because DNS lookup has failed ...
            return HTTPStatus.NOT_FOUND
        else:
            raise


def get_all_link_status_codes(list_of_links):
    """
    Takes a list of links, tries to establish a connection and gets the status code. Lumps both together in a dict and
    then appends that dict to a list.

    :param list_of_links: list of link url strings
    :return: list of link dicts with keys: link, code
    """

    links = []
    for link in list_of_links:
        links.append({'link': link, 'code': get_link_status_code(link)})

    return links
