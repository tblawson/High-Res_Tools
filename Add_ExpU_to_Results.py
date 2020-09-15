# -*- coding: utf-8 -*-
"""
Add_ExpU_to_Results.py - Initial version (Python 3).

Created on Tue 11/08/2020

@author: t.lawson

Fill in 'ExpU' and 'k' fields in Results table.
"""


import sqlite3
import GTC as gtc


# Set up connection to database:
db_path = input('Full Resistors.db path? (press "d" for default location) >')
if db_path == 'd':
    db_path = r'G:\My Drive\Resistors.db'  # Default location.
db_connection = sqlite3.connect(db_path)
curs = db_connection.cursor()

# Populate ExpU, k (for all rows where they're both null):
query = ("SELECT Run_Id, Meas_No, Parameter, Uncert, DoF FROM Results "
         "WHERE ExpU IS NULL AND k IS NULL;")
curs.execute(query)
rows = curs.fetchall()
print(f'Returning {len(rows)} rows with NULL Exp_U, k.')
for row in rows:
    runid = row[0]  # primary key 1
    meas_no = row[1]  # primary key 2
    param = row[2]  # primary key 3
    u = row[3]
    df = row[4]
    if u is None:  # Can't do anything with no std uncert!
        k = 'NULL'
        exp_u = 'NULL'
    else:
        print(f'{row}\t,unc = {u}, df = {df}')
        k = gtc.rp.k_factor(df)
        exp_u = k*u
    # print(f"{row}\t, exp_u = {exp_u}, k = {k}")
    query = (f"UPDATE Results SET ExpU = {exp_u}, k = {k} WHERE Run_Id = '{runid}' AND Meas_no = {meas_no}"
             f" AND Parameter = '{param}';")
    curs.execute(query)

# Populate k (for all rows where it's still null):
query = "SELECT Run_Id, Meas_No, Parameter, Uncert, ExpU FROM Results WHERE k IS NULL;"
curs.execute(query)
rows = curs.fetchall()
print(f'Returning {len(rows)} rows with NULL k.')
for row in rows:
    runid = row[0]  # primary key 1
    meas_no = row[1]  # primary key 2
    param = row[2]  # primary key 3
    u = row[3]
    if u is None:  # Can't do anything with no std uncert!
        k = 'NULL'
    else:
        exp_u = row[4]
        print(f'{row}\t,ExpUnc = {exp_u}')
        k = exp_u/u
    # print(f'{row}\t, k = {k}')
    query = f"UPDATE Results SET k = {k} WHERE Run_Id = '{runid}' AND Meas_No = {meas_no} AND Parameter = '{param}';"
    curs.execute(query)

# tidy up:
db_connection.commit()  # Assign all updates to database.
curs.close()
if db_connection:
    db_connection.close()
