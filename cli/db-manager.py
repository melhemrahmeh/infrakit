import psycopg2
from psycopg2 import sql

class DBManager:
    def __init__(self, connection_string):
        self.conn = psycopg2.connect(connection_string)
    
    def create_application(self, name, cluster, chart):
        with self.conn.cursor() as cur:
            cur.execute("""
                INSERT INTO applications (name, cluster, helm_chart)
                VALUES (%s, %s, %s)
            """, (name, cluster, chart))
            self.conn.commit()