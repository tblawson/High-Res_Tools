# -*- coding: utf-8 -*-
"""
Add_date_to_Runs.py - Initial version (Python 3).

Created on Tue 29/09/2020

@author: t.lawson

Add date to 'Runs' table. Use the most recent date
from 'Results'.Meas_Date for each Run_Id.

"""


import sqlite3


# Set up connection to database:
db_path = input('Full Resistors.db path? (press "d" for default location) >')
if db_path == 'd':
    db_path = r'G:\My Drive\Resistors.db'  # Default location.
db_connection = sqlite3.connect(db_path)
curs = db_connection.cursor()

test = True
Q_test_script = input('Test before running properly? (Y/N) >')
if Q_test_script.startswith('N'):
    test = False  # This is NOT a test!

q_get_runs = ("SELECT Run_Id FROM Runs WHERE Run_Id "
              "IN (SELECT Run_Id FROM Results);")  # Include analysed runs only.
curs.execute(q_get_runs)
rows = curs.fetchall()  # A list of 1-item tuples.
print(f'Found {len(rows)} Runs.')
for row in rows:
    runid = row[0]
    q_get_date = (f"SELECT Meas_Date FROM Results WHERE Run_Id='{runid}' "
                  "ORDER by Meas_Date DESC LIMIT 1;")
    curs.execute(q_get_date)
    row = curs.fetchone()  # A 1-item tuple.
    date = row[0]
    print(f'{runid}\tDate={date}')
    q_add_date = f"UPDATE Runs SET Meas_Date='{date}' WHERE Run_Id='{runid}';"
    curs.execute(q_add_date)

# tidy up:
if test is False:
    db_connection.commit()  # Assign all updates to database.

curs.close()
if db_connection:
    db_connection.close()
