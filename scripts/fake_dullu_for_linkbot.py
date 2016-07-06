"""
Puts a url onto the linkbot queue for testing purposes.
"""

import json

import linkbot
import pika

if __name__ == "__main__":
    json_dict = {"entity_id": "1",  # the SO question ID
                 "entity_type": "q",  # SO question entity (as opposed to a comment or an answer)
                 "url": "http://placehold.it/32x32",  # Should 301
                 "last_stamp": "0",
                 "attempts": "0"}

    jdump = json.dumps(json_dict)
    print(jdump)

    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue=linkbot.Linkbot.RABBITMQ_URL_QUEUE_NAME, durable=True)
    channel.basic_publish(exchange='',
                          routing_key=linkbot.Linkbot.RABBITMQ_URL_QUEUE_NAME,
                          body=jdump)
    print(" [x] Sent!")
    connection.close()
