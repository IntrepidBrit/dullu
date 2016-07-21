"""
Puts a question/answer/comment onto the dullu queue for testing purposes.
"""

import json
import os
import linkbot
import pika
import os.path as osp
from dullu import Dullu

if __name__ == "__main__":
    with open(osp.join(osp.dirname(osp.abspath(__file__)), "..", "tests", "data", "test_question.json"), "r") as f:
        sample_question_json = json.load(f)

    """
    TODO - commit this current batch of work, then uncomment the following code. Going to implement some enums based on
    the stack exchange API
    """
    json_dict = {Dullu.JSON_KEY__ENTITYQ__ID: sample_question_json[Dullu.JSON_KEY__ENTITYQ__ID],
                 Dullu.JSON_KEY__ENTITYQ__TYPE: sample_question_json[Dullu.JSON_KEY__ENTITYQ__TYPE],
                 Dullu.JSON_KEY__ENTITYQ__BODY: sample_question_json[Dullu.JSON_KEY__ENTITYQ__BODY]}

    jdump = json.dumps(json_dict)

    connection = pika.BlockingConnection(pika.ConnectionParameters(host='localhost'))
    channel = connection.channel()
    channel.queue_declare(queue=Dullu.RABBITMQ_QUEUE_ENTITY_NAME, durable=True)
    channel.basic_publish(exchange='',
                          routing_key=Dullu.RABBITMQ_QUEUE_ENTITY_NAME,
                          body=jdump)
    print(" [x] Sent!")
    connection.close()
