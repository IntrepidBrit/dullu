"""
A very simple Flask app to display the current state of link rot. Currently relies on HTTP Basic access
authentication to protect it.
"""

import configparser
import logging

import MySQLdb
import os
from flask import Flask, request, render_template, abort
from werkzeug.exceptions import BadRequest

CONFIG_FILE_LOCATION = os.path.join(os.path.dirname(__file__), 'db_info.conf')
POST_PATH = '/url/new/'

app = Flask(__name__)


def load_db_connection_info_from_parser():
    try:
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE_LOCATION)
        return config
    except configparser.Error:
        abort(500)


@app.route(POST_PATH, methods=['POST'])
def add_new_url():
    if request.method == 'POST':
        # sanitise incoming json
        
        try:
            rot_json_dict = request.get_json()
        except BadRequest:
            return abort(400)

        if rot_json_dict is None:
            return abort(422)

        try:
            if rot_json_dict['short'] and rot_json_dict['stout']:
                return abort(418)
        except KeyError:
            pass

        # TODO - pull these from elsewhere in the project. Hardcoding for testing.
        if not all([k in rot_json_dict.keys() for k in ['url',
                                                        'entity_id',
                                                        'entity_type',
                                                        'attempts',
                                                        'last_code',
                                                        'last_stamp',
                                                        'last_checker']]):
            return abort(422)

        db, cursor = db_connect()
        try:

            cursor.execute("INSERT INTO rot (entity_id, type, url, attempts, last_code, last_stamp, last_checker) VALUES (%(entity_id)s, %(type)s, %(url)s, %(attempts)s, %(last_code)s, %(last_stamp)s, %(last_checker)s);",
                           {'entity_id': rot_json_dict['entity_id'],
                            'type': rot_json_dict['entity_type'],
                            'url': rot_json_dict['url'],
                            'attempts': rot_json_dict['attempts'],
                            'last_code': rot_json_dict['last_code'],
                            'last_stamp': rot_json_dict['last_stamp'],
                            'last_checker': rot_json_dict['last_checker']})
            db.commit()
            return "k"
        finally:
            cursor.close()
            db.close()
    else:
        return abort(405)


def db_connect():
    db_config = load_db_connection_info_from_parser()
    db = MySQLdb.connect(host=db_config['DB']['host'],
                         user=db_config['DB']['user'],
                         passwd=db_config['DB']['password'],
                         db=db_config['DB']['name'])
    cursor = db.cursor()
    return db, cursor


@app.route('/view/all/')
def dirtily_simple_view():
    db, cursor = db_connect()
    try:
        cursor.execute("SELECT entity_id, type, url, attempts, last_code, last_stamp, last_checker FROM rot;")
        sql_results = cursor.fetchall()  # Yeah, because that's a good idea Mark
        # TODO - limit number of rows returned, and accept GET parameters specifying the number to return AND start id
    finally:
        cursor.close()
        db.close()
    return render_template('simple_all_view.html', sql_results=sql_results)


@app.route('/')
def hello_world():
    try:
        return 'Hallo.'
    except Exception as e:
        logging.error(e)
