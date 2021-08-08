# -*- coding: utf-8 -*-
"""
HRBC_raw_data_to_db.py - Initial version (Python 3).

Created on Wed 5/08/2020

@author: t.lawson

Extract all raw data rows from 'Data' and 'Rlink' sheets of an HRBC Excel file
and transfer information to Resistors.db >Raw_Rlink_Data, >Raw_Data and >Runs tables.
"""


import pylightxl as xl
import sqlite3


"""
---------------------------------------
            Helper functions:
---------------------------------------
"""


def extract_names(comment):
    """
    Extract resistor names from comment.
    Parse first part of comment for resistor names.
    Names must appear immediately after the strings 'R1: ' and 'R2: ' and
    immediately before the string ' monitored by GMH'.
    """
    assert comment.find('R1: ') >= 0, 'R1 name not found in comment!'
    assert comment.find('R2: ') >= 0, 'R2 name not found in comment!'
    r1_name = comment[comment.find('R1: ') + 4:comment.find(' monitored by GMH')]
    r2_name = comment[comment.find('R2: ') + 4:comment.rfind(' monitored by GMH')]
    return r1_name, r2_name


def convert(t_str):
    try:
        date, time = t_str.split()
        day, mon, yr = date.split('/')
        if len(day) == 4 and len(yr) == 2:
            # Return original if format is correct already.
            return t_str
        else:
            return f"{yr}-{mon}-{day} {time}"
    except ValueError as msg:
        print(msg, f't_str = "{t_str}"')
        return -1


"""
---------------------------------------
Set up connections to database and XL file...
"""
# Connect to Resistors database:
db_path = input('Full Resistors.db path? (press "d" for default location) >')
if db_path =='d':
    db_path = r'G:\My Drive\Resistors.db'  # Default location.
db_connection = sqlite3.connect(db_path)
curs = db_connection.cursor()

# Connect to XL file (E.g: r'G:\My Drive\TechProcDev\E052_Py3\HRBC_test_Py3.xlsx'):
filename = input('Full XL path/filename? >')
wb = xl.readxl(filename, ('Data', 'Rlink'))

"""
---------------------------------------
Start with 'Data' sheet -> Runs & Raw_Data tables...
"""
[maxrow, maxcol] = wb.ws('Data').size
print(f'Data sheet size: {maxrow} rows x {maxcol} columns.')

Role_col = xl.pylightxl.utility_columnletter2num('AC')
Descr_col = xl.pylightxl.utility_columnletter2num('AD')
Rng_mode_col = xl.pylightxl.utility_columnletter2num('AE')

roles = []
instruments = []
reversal = 0
meas_no = 1
this_run = ''
for row in wb.ws('Data').rows:
    role = row[Role_col - 1]
    descr = row[Descr_col - 1]
    range_mode = row[Rng_mode_col - 1]
    if row[25] not in ('',):
        com = row[25]  # Only re-assign comment if NOT blank

    # Look for next run_id...
    if row[0] == 'Run Id:':
        this_run = row[1]
        print(f'\nRun: {this_run}')
        #  Clear instrument assignments, reversal & meas-no, ready for next run:
        roles.clear()
        instruments.clear()
        reversal = 0
        meas_no = 1

    """
    Build instrument assignment info.
    Ignore 'DVMT1' and 'DVMT2' roles since this info is no longer used
    in the analysis.
    """
    if role not in ('', 'Role', 'DVMT1', 'DVMT2'):
        roles.append(role)
        instruments.append(descr)

    """"
    Note range-mode for this run.
    Have enough info to write 1 record to Runs table now.
    """
    if range_mode not in ('', 'Range mode'):
        this_range_mode = range_mode
        # print(f'\tRange mode: {this_range_mode}')
        assignments = dict(zip(roles, instruments))
        # print(f'\tInstrument assignments:\n\t{assignments}')
        print(f'comment: {com}')
        Rx_name, Rs_name = extract_names(com)
        # print(f'Rx: {Rx_name}, Rs: {Rs_name}')
        headings = 'Run_Id,Comment,RS_Name,RX_Name,Range_Mode,SRC1,SRC2,DVMd,DVM12,GMH1,GMH2,GMHroom'
        values = (f" '{this_run}','{com}','{Rs_name}','{Rx_name}','{this_range_mode}',"
                  f" '{assignments['SRC1']}','{assignments['SRC2']}','{assignments['DVMd']}',"
                  f" '{assignments['DVM12']}','{assignments['GMH1']}','{assignments['GMH2']}',"
                  f" '{assignments['GMHroom']}' ")
        runs_query = f"INSERT OR REPLACE INTO Runs ({headings}) VALUES ({values});"
        curs.execute(runs_query)
        # print(runs_query)

    # Note which reversal we're on:
    if row[0] not in ('start_row',  'stop_row', 'V1_set', 'Run Id:', '',):
        # These rows have the actual data...
        if reversal < 4:
            reversal += 1
        else:  # Reset reversal count as measurement No. increments:
            reversal = 1
            meas_no += 1
        # correct date formats:
        v1_t = convert(row[15])
        v2_t = convert(row[6])
        vd_t = convert(row[12])
        headings = (f'Run_Id,Meas_No,Rev_No,V1set,V2set,n,Start_del,AZ1_del,Range_del,V1_time,V1_val,V1_sd,'
                    f'Vd_time,Vd_val,Vd_sd,V2_time,V2_val,V2_sd,GMH1,GMH2,Troom,Proom,RHroom')
        values = (f"'{this_run}',{meas_no},{reversal},{row[0]},{row[1]},{row[2]},{row[3]},{row[4]},{row[5]},"
                  f"'{v1_t}',{row[16]},{row[17]},'{vd_t}',{row[13]},{row[14]},'{v2_t}',{row[7]},{row[8]},"
                  f"{row[20]},{row[21]},{row[22]},{row[23]},{row[24]}")
        data_query = f"INSERT OR REPLACE INTO Raw_Data ({headings}) VALUES ({values});"
        # print(data_query)
        if row[25] not in ('','IGNORE'):
            curs.execute(data_query)

"""
Now repeat with 'Rlink' -> Raw_Rlink_Data tables...
"""

print('\n---------------------------------------------------------------------------------------------------------\n')

[maxrow, maxcol] = wb.ws('Rlink').size
print(f'Rlink sheet size: {maxrow} rows x {maxcol} columns.')

reading_no = 0
data_block = False
Vpos_list = []
Vneg_list = []
n_reversals = 0
absV1 = absV2 = 0
for row in wb.ws('Rlink').rows:
    # Get no of columns of data (reversals):
    if row[0] == 'N_Reversals':
        n_reversals = row[1]
        continue

    # Get number of rows of data (readings);
    if row[0] == 'N_Readings':
        n_readings = row[1]
        continue

    # Look for next run_id...
    if row[0] == 'Run Id:':
        this_run = row[1]
        # print(f'Run: {this_run}')
        data_block = False  # Not at data block yet
        continue

    # Get applied voltages:
    if row[0] == 'R1':
        absV1 = row[3]
        continue

    elif row[0] == 'R2':
        absV2 = row[3]
        continue

    # Trigger data-block reading from next row after this one:
    if row[0] == 'ΔV+':
        data_block = True
        reading_no = 1  # Reset for new data block.
        continue

    if data_block is True:
        headings = f'Run_Id,Reading_No,absV1,absV2,deltaVpos,deltaVneg'
        for i in range(0, len(row), 2):
            if row[i] == '':
                break  # Don't include contents of empty cells
            values = f" '{this_run}',{reading_no},{absV1},{absV2},{row[i]},{row[i+1]}"
            Rlink_query = f"INSERT OR REPLACE INTO Raw_Rlink_Data ({headings}) VALUES ({values});"
            curs.execute(Rlink_query)
            reading_no += 1
            print(Rlink_query)
        continue

    if row[0] == '':
        data_block = False  # If blank row, next row can't be data
        reading_no = 0
        continue

db_connection.commit()  # Assign all updates to database.
curs.close()
if db_connection:
    db_connection.close()
