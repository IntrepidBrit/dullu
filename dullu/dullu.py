# -*- coding: utf-8 -*-
import pika
import logging
import traceback
import json
import se.api
from bs4 import BeautifulSoup


class Dullu:
    RABBITMQ_QUEUE_URL_NAME = 'dullu_url_queue'
    RABBITMQ_QUEUE_ENTITY_NAME = 'dull_entity_queue'

    # Entity queue, up for change though. Other side not coded.
    JSON_KEY__ENTITYQ__ID = 'Id'
    JSON_KEY__ENTITYQ__TYPE = 'PostTypeId'
    JSON_KEY__ENTITYQ__BODY = 'Body'

    # URL queue
    JSON_KEY__URLQ__ENTITY_ID = 'entity_id'
    JSON_KEY__URLQ__ENTITY_TYPE = 'entity_type'
    JSON_KEY__URLQ__ATTEMPTS = 'attempts'
    JSON_KEY__URLQ__URL = 'url'
    JSON_KEY__URLQ__LAST_TEST_CODE = 'last_code'
    JSON_KEY__URLQ__LAST_TEST_STAMP = 'last_stamp'
    JSON_KEY__URLQ__LAST_CHECKBOT = 'last_checker'

    def __init__(self, broker_address='localhost'):
        self.broker_address = broker_address

    def callback_scan_entity_for_urls(self, ch, method, properties, body):
        logging.debug("Received entity from broker.")

        try:
            json_dict = json.loads(body.decode())
        except json.decoder.JSONDecodeError as jsonde:
            logging.error("Oops! Couldn't decode that request. Caught {0}. Body = [{1}]. ".format(jsonde, body))

            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return

        if not all(k in json_dict for k in (self.JSON_KEY__ENTITYQ__ID, self.JSON_KEY__ENTITYQ__TYPE, self.JSON_KEY__ENTITYQ__BODY)):
            logging.error("Rejecting request. Missing information ({k1}:{v1},{k2}:{v2},{k3}:{v3}).".format(
                k1=self.JSON_KEY__ENTITYQ__ID,
                k2=self.JSON_KEY__ENTITYQ__TYPE,
                k3=self.JSON_KEY__ENTITYQ__BODY,
                v1=self.JSON_KEY__ENTITYQ__ID in json_dict,
                v2=self.JSON_KEY__ENTITYQ__TYPE in json_dict,
                v3=self.JSON_KEY__ENTITYQ__BODY in json_dict))

            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return

        """
        We currently only process certain different types of entities. questions/answers (hopefully comments and docs)
        in the future. We may need special handling for them depending on how eridu ends up working.
        """

        try:
            entity_type = se.api.PostType(json_dict[self.JSON_KEY__ENTITYQ__TYPE])
        except ValueError as ve:
            logging.error("Received an entity we're unwilling to process [{0}]. ".format(json_dict[self.JSON_KEY__ENTITYQ__TYPE]))
            ch.basic_reject(delivery_tag=method.delivery_tag, requeue=False)
            return

        urls = get_all_urls(json_dict[self.JSON_KEY__ENTITYQ__BODY])

        url_dict = {self.JSON_KEY__URLQ__ENTITY_ID: json_dict[self.JSON_KEY__ENTITYQ__ID],
                    self.JSON_KEY__URLQ__ENTITY_TYPE: json_dict[self.JSON_KEY__ENTITYQ__TYPE]}

        for url in urls:
            url_dict[self.JSON_KEY__URLQ__URL] = url
            self.channel.basic_publish(exchange="",
                                       routing_key=Dullu.RABBITMQ_QUEUE_URL_NAME,
                                       body=json.dumps(url_dict))

        ch.basic_ack(delivery_tag=method.delivery_tag)


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
            self.channel = connection.channel()

            # Connect to url queue
            self.channel.queue_declare(queue=self.RABBITMQ_QUEUE_URL_NAME, durable=True)

            # Connect to entity queue
            self.channel.queue_declare(queue=self.RABBITMQ_QUEUE_ENTITY_NAME, durable=True)
            self.channel.basic_consume(self.callback_scan_entity_for_urls, queue=self.RABBITMQ_QUEUE_ENTITY_NAME, no_ack=False)
            self.channel.basic_qos(prefetch_count=1)
            logging.info("Ready to start consuming")
            self.channel.start_consuming()
        except Exception as e:
            logging.warning("Exception detected.")
            logging.error(traceback.format_exc())
            raise e
        finally:
            logging.info("Dullu instance terminating...")
            connection.close()
            logging.debug("Fin.")

def get_all_urls(s):
    """
    Find all the urls in the text and stick them in a list for later processing.

    :param s: Input string
    :return: List of links
    """
    soup = BeautifulSoup(s, "html.parser")
    return [link.get('href') for link in soup.find_all('a')]
