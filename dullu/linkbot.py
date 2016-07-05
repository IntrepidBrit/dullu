import http.client
import json
import logging
import socket
from urllib.error import URLError
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

import pika
from HTTPStatus import HTTPStatus


class Linkbot:
    """

    """
    RABBITMQ_URL_QUEUE_NAME = 'dullu_url_queue'
    WHITE_HAT_USERAGENT_NAME = 'Dullu Linkrot Checker {version_number} (sopython.com)'.format(version_number="0.0.0")

    def __init__(self, white_hat=True, broker_address='localhost'):
        self.broker_address = broker_address
        self.white_hat = white_hat

    @staticmethod
    def callback_check_url(ch, method, properties, body):
        logging.debug("Received url from broker.")

        try:
            json_dict = json.loads(body.decode())
        except json.decoder.JSONDecodeError as jsonde:
            logging.error("Oops! Couldn't decode that request. Caught {0}. Body = [{1}]. ".format(jsonde, body))

            # Can switch to nack if we start pulling in multiple messages at once.
            ch.reject(delivery_tag=method.delivery_tag, requeue=False)
            return

    def run(self):
        logging.info("Attempting to connect to broker at: {0}.".format(self.broker_address))
        connection = pika.BlockingConnection(pika.ConnectionParameters(self.broker_address))

        try:
            channel = connection.channel()
            channel.queue_declare(queue=self.RABBITMQ_URL_QUEUE_NAME, durable=True)
            channel.basic_consume(self.callback_checkurl, queue=self.callback_checkurl, no_ack=False)
            channel.basic_qos(prefetch_count=1)
            channel.start_consuming()
        finally:
            logging.info("Link bot terminating...".format(self.broker_address))
            connection.close()
            logging.debug("Fin.")

    def check_robots_txt(self, parsed_link):
        rp = RobotFileParser()
        rp.set_url(urljoin(parsed_link.geturl(), '/robots.txt'))
        rp.read()
        return rp.can_fetch(self.WHITE_HAT_USERAGENT_NAME, parsed_link.geturl())

    def get_url_status_code(self, url):
        """
        TODO: Might make a wrapper around some of the connection stuff so that we don't need to catch things like
        winerror on *nix systems.

        :param link: a string containing an url
        :return:
        """
        # noinspection PyArgumentList
        try:
            parsed_link = urlparse(url)

            if self.white_hat and not self.check_robots_txt(parsed_link):
                return HTTPStatus.NO_INDEX

            conn = http.client.HTTPConnection(parsed_link.netloc)
            conn.request("HEAD", parsed_link.path)
            return HTTPStatus(conn.getresponse().status,)
        except http.client.BadStatusLine:
            return HTTPStatus.BAD_REQUEST
        except socket.gaierror as e:
            if e.errno == 11001:
                return HTTPStatus.DNS_LOOKUP_FAILED
            else:
                raise
        except URLError as urle:
            if urle.winerror == 10060:  # Host did not respond in a timely manner.
                return HTTPStatus.GATEWAY_TIMEOUT
            elif urle.reason.errno == 11001:  # Ew. gaierror has been repackaged by URLError
                return HTTPStatus.DNS_LOOKUP_FAILED
            else:
                raise
