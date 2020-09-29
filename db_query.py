# -*- coding: utf-8 -*-
"""
db_query.py - Initial version (Python 3).

Created on Tue 28/09/2020

@author: t.lawson
"""

import sqlite3


# Set up connection to database:
db_path = input('Full Resistors.db path? (press "d" for default location) >')
if db_path == 'd':
    db_path = r'G:\My Drive\Resistors_v100.db'  # Default location.
db_connection = sqlite3.connect(db_path)
curs = db_connection.cursor()


q_schema = "select * fROM sqlite_schema;"
curs.execute(q_schema)
rows = curs.fetchall()
for row in rows:
    print(row)

# tidy up:
db_connection.commit()  # Assign all updates to database.
curs.close()
if db_connection:
    db_connection.close()