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


def input_to_ureal(msg):
    """
    Request input from user and return it as a ureal.

    Initial input string is split() at the ' 's, yielding a list of numbers (as str).
    Create a list of floats by casting each str element using a list comprehension.
    Finally, unpack the list of floats as arguments to ureal().

    :param msg: User instructions defining type of input.
    :return: ureal
    """

    arg_lst = [float(i) for i in input(msg).split()]  # 0, 1, 2 or 3 arguments.
    assert len(arg_lst) > 1, 'Not enough values to construct ureal!'
    return gtc.ureal(*arg_lst)


def get_true_R_name(guess, curs):
    query = f"SELECT DISTINCT R_name FROM Res_Info WHERE R_Name LIKE '%{guess}%';"
    curs.execute(query)
    return curs.fetchone()[0]


"""
------------------------ Main Script --------------------------
"""

# Set up connections to database. # and XL file...
db_connection = db_connect()
curs = db_connection.cursor()

R_name_guess = input('Resistor name? ')
R_name = get_true_R_name(R_name_guess, curs)
print(f'I assume you meant {R_name}!')

R_temp = input_to_ureal('Resistor temperature (in ureal format: "val unc dof")? ')
R_V = input_to_ureal('Resistor test-voltage (in ureal format: "val unc dof")? ')
R_time = input('Resistor calibration date ("yyyy-mm-dd HH:MM:SS" or "n" for now)? ')
if R_time == 'n':
    t_val_dt = dt.datetime.now()  # A datetime object
else:
    t_val_dt = dt.datetime.strptime(R_time, T_FMT)  # A datetime object.

t_tup = dt.datetime.timetuple(t_val_dt,)  # A time-tuple object.
t_s = time.mktime(t_tup)  # Time as float (seconds from epoch).
t_days = t_s/86400  # Time as float (days from epoch).

query = f"SELECT * FROM Res_Info WHERE R_Name LIKE '%{R_name}%';"
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
print(f'alpha = {alpha}')
T0 = res_info['TRef'][f'{R_name}_TRef']
gamma = res_info['gamma'][f'{R_name}_gamma']
print(f'gamma = {gamma}')
V0 = res_info['VRef'][f'{R_name}_VRef']
tau = res_info['tau'][f'{R_name}_tau']
print(f'tau = {tau}')
t0 = res_info['Cal_Date'][f'{R_name}_t0']

R = R0*(1 + alpha*(R_temp-T0) + gamma*(R_V-V0) + tau*(t_days-t0))
print(f'R-value :\n\t{R.x} +/- {R.u}, df = {R.df}')
