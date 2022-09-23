# -*- coding: utf-8 -*-
"""
Fix_date_format.py - Initial version (Python 3).

Created on Tue 11/08/2020

@author: t.lawson

Convert date-string format from 'DD/MM/YYYY hh:mm:ss' to 'YYYY-MM-DD hh:mm:ss'
for all occurrences in table <tab>:
Tables affected: Raw_Data(V1_time, Vd_time, V2_time),
                 Results(Meas_Date),
                 Res_Info(Value WHERE Parameter = 'Cal_Date').
"""


import sqlite3


def convert(t_str):
    date, time = t_str.split()
    day, mon, yr = date.split('/')
    if len(day) == 4 and len(yr) == 2:
        # Return original order if format is correct already.
        return f"{day}-{mon}-{yr} {time}"  # t_str
    else:
        return f"{yr}-{mon}-{day} {time}"


# Set up connection to database:
db_path = input('Full Resistors.db path? (press "d" for default location) >')
if db_path == 'd':
    db_path = r'G:\My Drive\Resistors.db'  # Default location.
db_connection = sqlite3.connect(db_path)
curs = db_connection.cursor()

tab = input('Table? >')

if tab == 'Raw_Data':
    # Raw_data table...
    q_raw_d = "SELECT Run_Id, Meas_No, Rev_No, V1_time, Vd_time, V2_time FROM Raw_Data;"
    curs.execute(q_raw_d)
    rows = curs.fetchall()
    for row in rows:
        runid = row[0]
        meas_no = row[1]
        rev_no = row[2]
        V1t = row[3]
        Vdt = row[4]
        V2t = row[5]
        V1t = convert(V1t)
        Vdt = convert(Vdt)
        V2t = convert(V2t)

        q_raw_d2 = (f"UPDATE Raw_Data SET V1_time='{V1t}', Vd_time='{Vdt}', V2_time='{V2t}'"
                    f" WHERE Run_Id='{runid}' AND Meas_No='{meas_no}' AND Rev_No='{rev_no}';")
        curs.execute(q_raw_d2)

if tab == 'Results':
    # Results table...
    q_res = "SELECT Run_Id, Meas_No, Parameter, Meas_Date FROM Results;"
    curs.execute(q_res)
    rows = curs.fetchall()
    for row in rows:
        runid = row[0]
        meas_no = row[1]
        param = row[2]
        m_date = row[3]
        m_date = convert(m_date)

        q_res_d2 = (f"UPDATE Results SET Meas_Date='{m_date}'"
                    f" WHERE Run_Id='{runid}' AND Meas_No='{meas_no}' AND Parameter='{param}';")
        curs.execute(q_res_d2)

if tab == 'Res_Info':
    # Res_Info table...
    q_res_info = "SELECT R_Name, Value FROM Res_Info WHERE Parameter = 'Cal_Date';"
    curs.execute(q_res_info)
    rows = curs.fetchall()
    for row in rows:
        name = row[0]
        val = row[1]
        val = convert(val)

        q_res_info_d2 = (f"UPDATE Res_Info SET Value='{val}' WHERE "
                         f"R_Name = '{name}' AND Parameter = 'Cal_Date';")
        curs.execute(q_res_d2)

# tidy up:
db_connection.commit()  # Assign all updates to database.
curs.close()
if db_connection:
    db_connection.close()
