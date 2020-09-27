# -*- coding: utf-8 -*-
"""
Add_Tdefs.py - Initial version (Python 3).

Created on Wed 16/09/2020

@author: t.lawson

Add T_def to db.Res_Info table (one entry per resistor)
"""

import sqlite3
import GTC as gtc


def ureal_to_str(un):
    archive = gtc.pr.Archive()
    d = {un.label: un}
    archive.add(**d)
    return gtc.pr.dumps_json(archive)


# Set up connection to database:
db_path = input('Full Resistors.db path? (press "d" for default location) >')
if db_path == 'd':
    db_path = r'G:\My Drive\Resistors.db'  # Default location.
db_connection = sqlite3.connect(db_path)
curs = db_connection.cursor()

q_get_R_lst = "SELECT DISTINCT R_Name FROM Res_Info;"
curs.execute(q_get_R_lst)
R_lst = [r[0] for r in curs.fetchall()]

for R in R_lst:
    val = 0
    unc = 0.05
    df = 3
    lbl = f'{R}_Tdef'
    T_def = gtc.ureal(val, gtc.type_b.distribution['gaussian'](unc), df,
                      label=lbl)
    Tdef_str = ureal_to_str(T_def)

    headings = 'R_Name,Parameter,Value,Uncert,DoF,Label,Ref_Comment,Ureal_Str'
    values = f"'{R}','Tdef',{val},{unc},{df},'{lbl}','Guess','{Tdef_str}'"
    q_set_Tdef = f"INSERT OR REPLACE INTO Res_Info ({headings}) VALUES ({values});"
    curs.execute(q_set_Tdef)
    print(f"{R}: Added {lbl}:\n{Tdef_str}")

# tidy up:
db_connection.commit()  # Assign all updates to database.
curs.close()
if db_connection:
    db_connection.close()
