import datetime
import json
import sqlite3
from multiprocessing import Process

import os
import pika
from bs4 import BeautifulSoup
from dullu import temp

PERSISTENT_SQLITE_DB_NAME = "dullu_persistent.sqlite3"
DATETIME_RECHECK_THRESHOLD = datetime.timedelta(days=30)
ATTEMPT_THRESHOLD = 5


def db_connect():
    db_path = os.path.join(os.path.dirname(os.path.normpath(__file__)), PERSISTENT_SQLITE_DB_NAME)
    db_connection = sqlite3.connect(db_path)
    db_cursor = db_connection.cursor()

    try:
        db_cursor.execute("SELECT * FROM links_to_visit LIMIT 1;")
        db_cursor.execute("SELECT * FROM last_rot_check LIMIT 1;")
    except sqlite3.OperationalError:
        db_cursor.execute("CREATE TABLE links_to_visit (entity_id INTEGER, url TEXT, attempts INTEGER);")
        db_cursor.execute("CREATE TABLE last_rot_check (entity_id INTEGER, stamp INTEGER);")

    return db_connection, db_cursor

def link_checker_callback(ch, method, properties, body):
    try:
        json_dict = json.loads(body.decode())
    except json.decoder.JSONDecodeError as jsonde:
        print("Oops! Couldn't decode that request. " + str(jsonde))
        return

    db_connection, db_cursor = db_connect()
    try:
        if json_dict['was_successful']:
            db_cursor.execute("UPDATE last_rot_check SET stamp = ? WHERE rowid = ?;",
                              (int(datetime.datetime.utcnow().timestamp()), json_dict['rowid']))

            # TODO - delete old links_to_visit entry
        else:
            db_cursor.execute("SELECT attemps FROM links_to_visit;")
            attempts = db_cursor.fetchone()[0] + 1

            if attempts == ATTEMPT_THRESHOLD:
                # Do what we want to do with these results:
                # TODO - print to console
                # TODO - delete links_to_visit entry
                pass
            else:
                db_cursor.execute("UPDATE links_to_visit SET attempts = ? WHERE rowid = ?;",
                                  (attempts, json_dict['rowid']))
                # TODO - re-add to rabbit MQ queue.


        db_connection.commit()
    finally:
        db_cursor.close()
        db_connection.close()


def get_all_links(s):
    """
    Find all the urls in the text and stick them in a list for later processing.

    :param s: Input string
    :return: List of links
    """
    soup = BeautifulSoup(s, "html.parser")
    return [link.get('href') for link in soup.find_all('a')]


def kesh_eridu_callback(ch, method, properties, body):
    db_connection, db_cursor = db_connect()

    try:
        try:
            json_dict = json.loads(body.decode())
        except json.decoder.JSONDecodeError as jsonde:
            print("Oops! Couldn't decode that request. " + str(jsonde))
            return

        db_cursor.execute("SELECT * FROM links_to_visit;")
        print(db_cursor.fetchall())

        """
        Double check that entity doesn't already exist within our system.
        """
        db_cursor.execute("SELECT * FROM last_rot_check WHERE entity_id = ? LIMIT 1;", (json_dict['entity_id'],))
        result = db_cursor.fetchone()

        # If this callback has been triggered, that means there's been a change that needs to be checked (or it's new)

        list_of_links = get_all_links(json_dict['body'])

        if result is None:
            db_cursor.execute("INSERT INTO last_rot_check VALUES (?, 0);", (json_dict['entity_id'],))

        # I wonder if this'll actually be faster than managing sqlite3's transactions ourselves?
        batch = [(json_dict['entity_id'], link) for link in list_of_links]
        db_cursor.executemany('INSERT INTO links_to_visit VALUES (?,?,0);', batch)

    finally:
        db_connection.commit()
        db_cursor.close()
        db_connection.close()

        ch.basic_ack(delivery_tag=method.delivery_tag)


def kesh_eridu_callback_listener():
    connection = pika.BlockingConnection(pika.ConnectionParameters('localhost'))

    try:
        channel = connection.channel()
        channel.queue_declare(queue=temp.RABBITMQ_CHANNEL_NAME, durable=True)
        channel.basic_consume(kesh_eridu_callback, queue=temp.RABBITMQ_CHANNEL_NAME, no_ack=True)
        channel.basic_qos(prefetch_count=1)

        print(' [*] Waiting for messages. To exit press CTRL+C')
        channel.start_consuming()
    finally:
        connection.close()

def main():
    '''
    The main dullu thread will be responsible for aggregating information from both kesh and eridu.

    Will also parcel work out to other workers so we can have a range of different IP addresses (and so we don't get
    blocked).

    It also needs to be responsible for passing on any broken links to the outside world.
    :return:
    '''

    # Fire up process responsible for listening to the kesh & eridu message queues and writing them to the database.
    kesheridu_listener_process = Process(target=kesh_eridu_callback_listener)
    kesheridu_listener_process.start()

    kesheridu_listener_process.join()


if __name__ == "__main__":
    main()
