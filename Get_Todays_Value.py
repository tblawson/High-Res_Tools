# -*- coding: utf-8 -*-
"""
Get_Todays_Value.py.

Created on Thur 2/09/2021

@author: t.lawson

Interrogates database and returns resistor value and uncertainty,
given resistor name and, temperature and test-voltage.
"""

import sqlite3
import GTC as gtc
import datetime as dt
import time
import sys


T_FMT = '%Y-%m-%d %H:%M:%S'


"""
-------------------- Useful Functions -----------------------
"""


def db_connect():
    # Connect to Resistors database:
    db_path = input('Full Resistors.db path? (press "d" for default location) >')
    if db_path == 'd':
        db_path = r'G:\My Drive\Resistors.db'  # Default location.
    db_connection = sqlite3.connect(db_path)
    return db_connection


def str_to_ureal(j_str, name):
    archive = gtc.pr.loads_json(j_str)
    return archive.extract(name)


"""
------------------------ Main Script --------------------------
"""

# Set up connections to database. # and XL file...
db_connection = db_connect()
curs = db_connection.cursor()

R_name = input('Resistor name? ')
R_temp_val = float(input('Resistor temperature? '))
R_V_val = float(input('Resistor test-voltage? '))
R_time = input('Resistor calibration date ("yyyy-mm-dd HH:MM:SS" or "n" for now)? ')
if R_time == 'n':
    t_val_dt = dt.datetime.now()  # A datetime object
else:
    t_val_dt = dt.datetime.strptime(R_time,  T_FMT)  # A datetime object.

t_tup = dt.datetime.timetuple(t_val_dt,)  # A time-tuple object.
t_s = time.mktime(t_tup)  # Time as float (seconds from epoch).
t_days = t_s/86400  # Time as float (days from epoch).

query = f"SELECT * FROM Res_Info WHERE R_Name = '{R_name}';"
curs.execute(query)

try:
    rows = curs.fetchall()
    assert len(rows) > 0, 'No resistor info available!'
except AssertionError as msg:
    print(msg)
    sys.exit()

#  Compile data for this resistor into a dictionary.
res_info = {}
for row in rows:
    parameter = row[1]
    val = row[2]
    unc = row[3]
    df = row[4]
    lbl = row[5]
    u_str = row[7]
    res_info.update(
        {parameter: {'value': val,
                     'uncert': unc,
                     'dof': df,
                     'label': lbl,
                     'ureal_str': u_str
                     }
         }
    )

    # construct ureals and add to sub-dictionaries:
    res_info[parameter].update({lbl: str_to_ureal(res_info[parameter]['ureal_str'], lbl)})

R0 = res_info['R0'][f'{R_name}_R0']
alpha = res_info['alpha'][f'{R_name}_alpha']
T0 = res_info['TRef'][f'{R_name}_TRef']
gamma = res_info['gamma'][f'{R_name}_gamma']
V0 = res_info['VRef'][f'{R_name}_VRef']
tau = res_info['tau'][f'{R_name}_tau']
t0 = res_info['Cal_Date'][f'{R_name}_t0']

R = R0*(1 + alpha*(R_temp_val-T0) + gamma*(R_V_val-V0) + tau*(t_days-t0))
print(f'R-value now:\n\t{R.x} +/- {R.u}, df = {R.df}')

# print(res_info.keys())
# date_u_str = res_info['Cal_Date']['ureal_str']
# print(date_u_str)
# Cal_date = str_to_ureal(date_u_str, f'av_date_{R_name}')
# print(Cal_date)
