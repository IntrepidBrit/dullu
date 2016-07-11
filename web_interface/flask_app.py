
# A very simple Flask app to display the current state of link rot. Currently relies on HTTP Basic access authentication to protect it.

from flask import Flask
import logging
import json
import MySQLdb
import configparser

CONFIG_FILE_LOCATION = 'db_info.conf'

app = Flask(__name__)

def load_db_connection_info_from_parser():
    try:
        config = configparser.ConfigParser()
        config.read(CONFIG_FILE_LOCATION)  # TODO - work out the best way to dynamically specify this from within PythonAnywhere
    except configparser.Error as cpe:
        logging.error(cpe)
        return http_status_page("Invalid DB connection", 500)
    return config

def http_status_page(status, reason='Unspecified'):
    return (reason, status)

@app.route('/url/new/', methods=['POST'])
def add_new_url(rot_json):
    if request.method == 'POST':
        # sanitise incoming json
        try:
            json_dict = json.loads(rot_json)
        except json.JSONDecodeError as jsonde:
            return http_status_page('Badly formed object', 422)

        # TODO - pull these from elsewhere in the project. Hardcoding for testing.
        if not ['url', 'entity_id', 'entity_type', 'attempts', 'last_code', 'last_stamp', 'last_checker'] in json_dict:
            return http_status_page('Missing params', 422)

        db_config = load_db_connection_info_from_parser()

        db = MySQLdb.connect(host=db_config['host'], user=db_config['user'], passwd=db_config['password'], db=db_config['db'])
        try:
            cursor = db.cursor()
            cursor.execute("INSERT INTO rot (entity_id, type, url, attempts, last_code, last_stamp, last_checker) VALUES (:entity_id, :type, :url, :attempts, :last_code, :last_stamp, :last_checker;",
                    {'entity_id': json_dict['entity_id'],
                     'type': json_dict['type'],
                     'url': json_dict['url'],
                     'attempts': json_dict['attempts'],
                     'last_code': json_dict['last_code'],
                     'last_stamp': json_dict['last_stamp'],
                     'last_checker': json_dict['last_checker']})
            row = cursor.fetchone()
            return row
        finally:
            cursor.close()
            db.close()
    else:
        return http_status_page("POST required", 422)

@app.route('/')
def hello_world():
    try:
        return 'Hallo.'
    except Exception as e:
        logging.error(e)

