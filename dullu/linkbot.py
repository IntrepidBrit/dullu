import datetime
import http.client
import json
import logging
import socket
import traceback
from urllib.error import URLError
from urllib.parse import urlparse, urljoin
from urllib.robotparser import RobotFileParser

import pika
from HTTPStatus import HTTPStatus


class Linkbot:
    """
    The class responsible for actually going out and checking the links. There is little "forward-thinking" in the
    Linkbot, it just checks the queue, determines if it's allowed to check the url from the robots.txt and then attempts
    to check the url itself.

    Dullu's primary workers will handle any url caching and the like.
    """
    RABBITMQ_URL_QUEUE_NAME = 'dullu_url_queue'
    USERAGENT_NAME = 'Dullu Linkrot Checker {version_number} (sopython.com)'.format(version_number="0.0.0")
    ATTEMPTS_THRESHOLD = 5
    MAX_TIME_BETWEEN_TESTS = datetime.timedelta(days=1)
    # MAX_TIME_BETWEEN_TESTS = datetime.timedelta(seconds=10)  # just for development

    JSON_KEY__ENTITY_ID = 'entity_id'
    JSON_KEY__ENTITY_TYPE = 'entity_type'
    JSON_KEY__ATTEMPTS = 'attempts'
    JSON_KEY__URL = 'url'
    JSON_KEY__LAST_TEST_CODE = 'last_code'
    JSON_KEY__LAST_TEST_STAMP = 'last_stamp'

    def __init__(self, broker_address='localhost'):
        """

        :param broker_address: a unicode string containing the hostname or IP address of the broker.
        """
        self.broker_address = broker_address
        self.user_agent = self.USERAGENT_NAME

    def callback_check_url(self, ch, method, properties, body):
        """
        Where the linkbot magic happens. This will get called when the broker passes a message to the linkbots. Will
        firstly sanitise the message, then see if it is allowed to visit the url (from the robots.txt). Then will try
        to

        If the body is valid, but couldn't properly access the page, then it will re-add the url to the back of the
        queue, but increment the number of attempts. If there are too many attempts,  then it

        Known issues:

        1) Currently, any links that need to be checked but sufficient time (MAX_TIME_BETWEEN_TESTS)
        hasn't elapsed, then the message will passed to a linkbot, processed and then immediately re-added to the queue.
        This is really wasteful.

        2) There's very little status code specific handling going on just now. This will be extended later.

        :param ch: pika.Channel - Will be provided by RabbitMQ
        :param method: pika.spec.Basic.Deliver - Will be provided by RabbitMQ
        :param properties: pika.spec.BasicProperties - Will be provided by RabbitMQ
        :param body: str, unicode or bytes - Will be provided by RabbitMQ, but will have originally come from dullu
        :return:
        """
        # entity id, entity type, # of attempts, url, last failure type, date of last test
        logging.debug("Received url from broker.")

        try:
            json_dict = json.loads(body.decode())
        except json.decoder.JSONDecodeError as jsonde:
            logging.error("Oops! Couldn't decode that request. Caught {0}. Body = [{1}]. ".format(jsonde, body))

            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return

        if not all(k in json_dict for k in (self.JSON_KEY__ENTITY_ID, self.JSON_KEY__ENTITY_TYPE, self.JSON_KEY__URL)):
            logging.error("Rejecting request. Missing information ({k1}:{v1},{k2}:{v2},{k2}:{v2}).".format(
                k1=self.JSON_KEY__ENTITY_ID,
                k2=self.JSON_KEY__ENTITY_TYPE,
                k3=self.JSON_KEY__URL,
                v1=self.JSON_KEY__ENTITY_ID in json_dict,
                v2=self.JSON_KEY__ENTITY_TYPE in json_dict,
                v3=self.JSON_KEY__URL in json_dict))

            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return

        try:
            if int(json_dict[self.JSON_KEY__ATTEMPTS]) > self.ATTEMPTS_THRESHOLD:
                '''
                Remove from the queue, inform web service that we have detected some likely link rot and that human
                intervention is required '''

                # TODO - convert my pythonanywhere instance for link rot notification
                logging.info("Too many failed attempts for {id}:{ty}. Adding to rot list.".format(
                    id=json_dict[self.JSON_KEY__ENTITY_ID],
                    ty=json_dict[self.JSON_KEY__ENTITY_TYPE]))

                self.link_rot_action(json_dict)
                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
                return
        except KeyError:
            json_dict[self.JSON_KEY__ATTEMPTS] = 0

        try:
            # to make the comparison below more pretty...
            now = datetime.datetime.now(datetime.timezone.utc)
            then = datetime.datetime.fromtimestamp(int(json_dict[self.JSON_KEY__LAST_TEST_STAMP]),
                                                  tz=datetime.timezone.utc)

            if (now - then) < self.MAX_TIME_BETWEEN_TESTS:
                logging.info("Too soon to retry for {id}:{ty}. Re-adding to the queue.".format(
                    id=json_dict[self.JSON_KEY__ENTITY_ID],
                    ty=json_dict[self.JSON_KEY__ENTITY_TYPE]))

                ch.basic_reject(delivery_tag=method.delivery_tag, requeue=True)
                return

        except KeyError:
            json_dict[self.JSON_KEY__LAST_TEST_STAMP] = 0

        logging.debug("Checking {url}.".format(url=json_dict[self.JSON_KEY__URL]))

        status_code = self.get_url_status_code(json_dict[self.JSON_KEY__URL])

        json_dict[self.JSON_KEY__LAST_TEST_STAMP] = datetime.datetime.now(datetime.timezone.utc).timestamp()
        json_dict[self.JSON_KEY__LAST_TEST_CODE] = status_code

        if status_code == HTTPStatus.OK:
            logging.debug("OKAY: {url}.".format(url=json_dict[self.JSON_KEY__URL]))
            ch.basic_ack(delivery_tag=method.delivery_tag)

        # Do any status code specific handling here.
        elif status_code == HTTPStatus.NO_INDEX or status_code == HTTPStatus.MOVED_PERMANENTLY:
            logging.info("Manual intervention required for {url} [code = {code}].".format(
                url=json_dict[self.JSON_KEY__URL],
                code=json_dict[self.JSON_KEY__LAST_TEST_CODE]))

            self.needs_human_verification(json_dict)
            ch.basic_ack(delivery_tag=method.delivery_tag)

        # Treat everything else the same
        else:
            logging.debug("Putting {url} back on the queue. [Code = {code}].".format(
                url=json_dict[self.JSON_KEY__URL],
                code=json_dict[self.JSON_KEY__LAST_TEST_CODE]))

            json_dict[self.JSON_KEY__ATTEMPTS] = int(json_dict[self.JSON_KEY__ATTEMPTS]) + 1
            ch.basic_publish(exchange='', routing_key=self.RABBITMQ_URL_QUEUE_NAME, body=json.dumps(json_dict))
            ch.basic_ack(delivery_tag=method.delivery_tag)

    def needs_human_verification(self, json_body_dict):
        """
        Currently a placeholder function. Will connect to some notification API.
        :param json_body_dict:
        :return:
        """
        print("Need a human to check: \"{url}\"; reason: {reason} ".format(
            url=json_body_dict[self.JSON_KEY__URL],
            reason=json_body_dict[self.JSON_KEY__LAST_TEST_CODE]))

    def link_rot_action(self, json_body_dict):
        """
        Currently a placeholder function. Will connect to some notification API.
        Might not actually differ from "needs human verification" in the final version of code.

        :param json_body_dict: The json decoded unicode dict of the message body string
        :return:
        """
        print("Link rot found: [{0}]; reason: {1}".format(json_body_dict[self.JSON_KEY__URL],
                                                          json_body_dict[self.JSON_KEY__LAST_TEST_CODE]))

    def check_robots_txt(self, parsed_link):
        """
        Checks the site's robots.txt file to make sure our user agent is allowed to visit that url.
        :param parsed_link:
        :return: boolean . True if we're allowed to visit (or there's no robots.txt)
        """
        rp = RobotFileParser()
        rp.set_url(urljoin(parsed_link.geturl(), '/robots.txt'))
        rp.read()
        return rp.can_fetch(self.user_agent, parsed_link.geturl())

    def get_url_status_code(self, url):
        """
        TODO: Might make a wrapper around some of the connection stuff so that we can 'hide' the logic to catch things
        like winerror.

        :param url:
        :param link: a string containing an url
        :return: HTTPStatus enum - the http status code returned when we visited that url.
        """
        # noinspection PyArgumentList
        try:
            parsed_link = urlparse(url)

            if not self.check_robots_txt(parsed_link):
                return HTTPStatus.NO_INDEX

            headers = {'X-Clacks-Overhead': 'GNU Terry Pratchett', 'User-Agent': self.user_agent}
            conn = http.client.HTTPConnection(parsed_link.netloc)
            conn.request("HEAD", parsed_link.path, headers=headers)
            return HTTPStatus(conn.getresponse().status)
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

    def run(self):
        """
        This will set up the link bot and connect to the broker. If the channel doesn't yet exist, it will create it
        on the broker (shouldn't actually happen unless someone runs things in the wrong order).

        channel.start_consuming is a blocking function.
        :return:
        """
        logging.info("Attempting to connect to broker at: {0}.".format(self.broker_address))
        connection = pika.BlockingConnection(pika.ConnectionParameters(self.broker_address))

        try:
            channel = connection.channel()
            channel.queue_declare(queue=self.RABBITMQ_URL_QUEUE_NAME, durable=True)
            channel.basic_consume(self.callback_check_url, queue=self.RABBITMQ_URL_QUEUE_NAME, no_ack=False)
            channel.basic_qos(prefetch_count=1)
            logging.info("Ready to start consuming")
            channel.start_consuming()
        except:
            logging.warning("Exception detected.")
            logging.error(traceback.format_exc())
        finally:
            logging.info("Link bot terminating...".format(self.broker_address))
            connection.close()
            logging.debug("Fin.")
