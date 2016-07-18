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
