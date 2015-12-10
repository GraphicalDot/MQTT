import psycopg2
import psycopg2.extras
from settings import *


class LocalQueryHandler(object):
    @classmethod
    def get_connection(cls):
        connection = psycopg2.connect("dbname=%s host=%s user=%s password=%s"
                                      % (local_db_name, local_db_host, local_db_user, local_db_pswd))
        return connection

    @classmethod
    def get_results(cls, query, variables=None):
        connection = cls.get_connection()
        cursor = connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
        # print(cursor.mogrify(query, variables))
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
