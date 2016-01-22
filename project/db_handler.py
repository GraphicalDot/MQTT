import os
import psycopg2
import psycopg2.extras
import sys

sys.path.append(os.path.dirname(os.path.abspath(__file__)).rsplit('/', 1)[0])
from project import app_settings


class QueryHandler(object):
    @classmethod
    def get_connection(cls):
        connection = psycopg2.connect("dbname=%s host=%s user=%s password=%s"
                                      % (app_settings.LOCAL_DB_NAME, app_settings.LOCAL_DB_HOST,
                                         app_settings.LOCAL_DB_USER, app_settings.LOCAL_DB_PSWD))
        return connection

    @classmethod
    def get_results(cls, query, variables=None):
        connection = cls.get_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        print(cursor.mogrify(query, variables))
        cursor.execute(query, variables)
        results = cursor.fetchall()
        connection.commit()
        cursor.close()
        return results

    @classmethod
    def execute(cls, query, variables=None):
        connection = cls.get_connection()
        cursor = connection.cursor()
        print(cursor.mogrify(query, variables))
        cursor.execute(query, variables)
        connection.commit()
        cursor.close()

    @classmethod
    def get_count(cls, query, variables=None):
        connection = cls.get_connection()
        cursor = connection.cursor()
        cursor.execute(query, variables)
        count = cursor.fetchone()
        connection.commit()
        cursor.close()
        return count[0]
