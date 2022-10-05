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


def correct_auto2iv(name):
    """
    Correct I-V resistor names from old 'Auto <value> format.
    :param name: Resistor name
    :return: R name in correct format
    """
    if name.startswith('Auto'):
        # E.g. name = 'Auto 10M'
        val_str = name.split()[1]  # '10M'
        name = f'I-V{val_str} {val_str}'  # e.g 'I-V10M 10M'
    return name

def extract_names(comment):
    """
    Extract resistor names from comment.
    Parse first part of comment for resistor names.
    Names must appear immediately after the strings 'R1: ' and 'R2: ' and
    immediately before the string ' monitored by GMH'.
    """
    assert comment.find('R1: ') >= 0, f'R1 name not found in comment! -\t{comment}'
    assert comment.find('R2: ') >= 0, f'R2 name not found in comment! -\t{comment}'
    r1_name = comment[comment.find('R1: ') + 4:comment.find(' monitored by GMH')]
    r2_name = comment[comment.find('R2: ') + 4:comment.rfind(' monitored by GMH')]
    """
    Create I-V alias -
    Resistor names should follow the '<name> <value>' convention,
    where <name> is unique (e.g Serial No.) and <value> is the nominal decade value 
    with a multiplying suffix (e.g. '10M' or '100k').
    
    The I-V resistors have previously been named according to the convention:
    'Auto <value>' which fails to uniquely identify each resistor, so occurrences
    of this older style should be corrected. 
    """
    r1_name = correct_auto2iv(r1_name)
    r2_name = correct_auto2iv(r2_name)
    return r1_name, r2_name


def convert(t_str):
    """
    Convert date & time format from 'dd\mm\yyyy HH:MM:SS'
    to 'yyyy-mm-dd HH:MM:SS'
    :param t_str: date & time as a string
    :return: converted string as described above or -1 on error.
    """
    if t_str in ('', 't', 'V1', 'Vd1', 'V2'):  # Ignore headings.
        return t_str
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


def db_connect():
    # Connect to Resistors database:
    db_path = input('Full Resistors.db path? (press "d" for default location) >')
    if db_path == 'd':
        db_path = r'G:\My Drive\Resistors.db'  # Default location.
    db_connection = sqlite3.connect(db_path)
    return db_connection


def xl_connect():
    # Is the data from a single-dvm run?
    is_singledvm = input('Single-DVM data? (y/n)?')
    if is_singledvm in ('y', 'Y', 'yes', 'Yes'):
        is_singledvm = True
    else:
        is_singledvm = False

    # Connect to XL file (E.g: r'G:\My Drive\TechProcDev\E052_Py3\HRBC_test_Py3.xlsx'):
    filename = input('Full XL path/filename? >')
    if is_singledvm:
        return xl.readxl(filename, ('Data',)), is_singledvm, filename
    else:
        return xl.readxl(filename, ('Data', 'Rlink')), is_singledvm, filename

"""
-------------------------------------------------------------------------------------
                          Main script starts here...
-------------------------------------------------------------------------------------
"""
# Set up connections to database. # and XL file...
db_connection = db_connect()
curs = db_connection.cursor()

wb, is_singledvm, xl_file = xl_connect()

"""
-------------------------------------------------------------------------------------
Start with 'Data' sheet -> Runs & Raw_Data tables...
"""
[maxrow, maxcol] = wb.ws('Data').size
print(f'\nData sheet size: {maxrow} rows x {maxcol} columns.')

Role_col = xl.pylightxl.utility_columnletter2num('AC')
Descr_col = xl.pylightxl.utility_columnletter2num('AD')
Rng_mode_col = xl.pylightxl.utility_columnletter2num('AE')
if is_singledvm is True:
    comment_col = xl.pylightxl.utility_columnletter2num('AB')
    DVM_null = 'DVM'
    DVM_src = 'DVM'
else:
    comment_col = xl.pylightxl.utility_columnletter2num('Z')
    DVM_null = 'DVMd'
    DVM_src = 'DVM12'

roles = []
instruments = []
reversal = 0
meas_no = 1
this_run = ''
com = ''

# Start working through Data sheet row by row...
for row in wb.ws('Data').rows:

    if row[0] in ('start_row', 'stop_row', 'V1_set',):
        continue

    # Look for next run_id...
    if row[0] == 'Run Id:':
        this_run = row[1]
        print(f'\nRun: \t{this_run}')
        #  Clear instrument assignment lists, reversal & meas-no, ready for next run:
        roles.clear()
        instruments.clear()
        reversal = 0
        meas_no = 1
        continue

    # Start gathering instrument assignments:
    role = row[Role_col - 1]
    descr = row[Descr_col - 1]
    nom_range_mode = row[Rng_mode_col - 1]  # '', 'Range mode', 'FIXED' or 'AUTO'
    if role == 'DVM12':
        range_mode = nom_range_mode  # 'FIXED' or 'AUTO'
    if row[comment_col - 1] not in ('', 'Comment'):  # row[comment_col-1].startswith('R')
        prev_com = com
        com = row[comment_col - 1]  # Only re-assign comment if NOT blank or 'Comment'
        if com != prev_com:  # Only print comment if it's changed from last time
            print(f'Comment: \t{com}')

    """
    Build instrument assignment info.
    Ignore 'DVMT1' and 'DVMT2' roles since this info is no longer used
    in the analysis.
    """
    if role not in ('', 'Role', 'DVMT1', 'DVMT2', 'switchbox'):
        roles.append(role)
        instruments.append(descr)

    """"
    Note range-mode for this run.
    Have enough info to write 1 record to Runs table now.
    (Assumes 10 role assignment rows.)
    """
    if len(roles) == 7:  # Only recording 7/10 roles - ignore DVMT1, DVMT2 and switchbox.
        assignments = dict(zip(roles, instruments))
        print(assignments)
        Rx_name, Rs_name = extract_names(com)
        # print(f'Rx: {Rx_name}, Rs: {Rs_name}')
        headings = f'Run_Id,Comment,RS_Name,RX_Name,Range_Mode,SRC1,SRC2,DVMd,DVM12,GMH1,GMH2,GMHroom,Source_File'
        values = (f" '{this_run}','{com}','{Rs_name}','{Rx_name}','{range_mode}',"
                  f" '{assignments['SRC1']}','{assignments['SRC2']}','{assignments[DVM_null]}',"
                  f" '{assignments[DVM_src]}','{assignments['GMH1']}','{assignments['GMH2']}',"
                  f" '{assignments['GMHroom']}','{xl_file}'")
        runs_query = f"INSERT OR REPLACE INTO Runs ({headings}) VALUES ({values});"
        curs.execute(runs_query)
        # print(runs_query)

    """
    ---------------------------------------------------------------------------------
    -----------------Next section is for *non* SINGLE-DVM files ONLY:----------------
    """
    if is_singledvm is False:  # Only add records to Raw_Data table if NOT a single-DVM run.
        # Note which reversal we're on:
        if row[0] not in ('start_row',  'stop_row', 'V1_set', 'Run Id:', '',):
            # These rows have the actual data...
            if reversal < 4:
                reversal += 1
            else:  # Reset reversal count as measurement No. increments:
                reversal = 1
                meas_no += 1
            print(f'Processing run {this_run}:\n\tmeas. {meas_no}, reversal {reversal}.')
            # input('Press any key to continue with analysis.')
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
            if row[25] not in ('', 'IGNORE',):  # comment
                curs.execute(data_query)
        # End of data row selector
    # End of single-DVM filter

"""
Now repeat with 'Rlink' -> Raw_Rlink_Data table...
"""
print('\n---------------------------------------------------------------------------------------------------\n')
print('Reading Rlink data...')

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
        print(f'\nRun: {this_run}')
        data_block = False  # Not at data block yet
        continue  # Ignore comment and date rows - this info is obtained elsewhere.

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
                break  # Don't include empty cells

            values = f" '{this_run}',{reading_no},{absV1},{absV2},{row[i]},{row[i+1]}"
            Rlink_query = f"INSERT OR REPLACE INTO Raw_Rlink_Data ({headings}) VALUES ({values});"
            curs.execute(Rlink_query)
            reading_no += 1
            print('.', end='')
        continue

    if row[0] == '':
        data_block = False  # If blank row, next row can't be data
        reading_no = 0
        continue
#  End of R_link row loop

db_connection.commit()  # Assign all updates to database.
curs.close()
if db_connection:
    db_connection.close()
