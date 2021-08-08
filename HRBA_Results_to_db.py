# -*- coding: utf-8 -*-
"""
HRBA_Results_to_db.py - Initial version (Python 3).

Created on Fri 7/08/2020

@author: t.lawson

Extract all HRBA-analysed results from 'Results' sheet of an HRBC / HRBA Excel file
and transfer information to Resistors.db >Results and >Uncert_Contribs tables.
"""

import pylightxl as xl
import sqlite3


"""
---------------------------------------
            Helper functions:
---------------------------------------
"""


def convert_date_fmt(t_str):
    """
    Convert date string.
    :param t_str: str in form 'dd/mm/YYYY HH:MM:SS'
    :return: str in form 'YYYY-mm-dd HH:MM:SS'
    """
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
if db_path == 'd':
    db_path = r'G:\My Drive\Resistors.db'  # Default location.
db_connection = sqlite3.connect(db_path)
curs = db_connection.cursor()

test = True
response = input('Is this just a test (Y/N)? >')
if response.startswith('N'):
    test = False

# Connect to XL file (E.g: r'G:\My Drive\TechProcDev\E052_Py3\HRBC_test_Py3.xlsx'):
filename = input('Full XL path/filename? >')
wb = xl.readxl(filename, ('Results',))

[maxrow, maxcol] = wb.ws('Results').size
print(f'Results sheet size: {maxrow} rows x {maxcol} columns.')

this_analysis_note = ''
this_run = ''
first_meas_block = False
next_meas_block = False
meas_no = 0

meas_date = ''
Vtest_val = Vtest_unc = Vtest_df = 0
T_val = T_unc = T_df = 0
R_val = R_unc = R_df = R_expu = 0

global_row_count = 0  # Row count within entire sheet.
run_row_count = 0
meas_row_count = 0

print("Getting rows from 'Results' sheet...")
for row in wb.ws('Results').rows:  # Step through rows and gather info...
    # print(row)
    global_row_count += 1
    if row[0].startswith('Processed'):  # Start of new run...
        run_row_count = 1  # Row count within 1 run. Reset here.
        this_analysis_note = row[0]
        meas_no = 1  # Set / reset measurement number
        print(f'\nAnalysis note:\t{this_analysis_note}')
        continue

    if row[2] == 'Run Id:':  # ... start of new run (still)
        run_row_count += 1
        this_run = row[3]
        print(f'RUN ID:\t{this_run}')
        continue

    if row[0] == 'Name':  # 1st Actual data block starts NEXT row.
        run_row_count += 1
        meas_row_count = 0  # Reset row count within 1 meas-data block (excludes any headings).
        first_meas_block = True
        continue

    if first_meas_block is True or next_meas_block is True:
        """
        We're now in a block of data relating to a single measurement.
        'first_meas_block == True' means we're in the 1st measurement;
        'next_meas_block == True' means we're in a subsequent measurement.
        """
        run_row_count += 1
        meas_row_count += 1
        print(f'In measurement block {meas_no}')

        # Write budget line to Uncert_Contribs table:
        if row[12] == 'inf':  # dof
            df = 1e6
        else:
            df = row[12]
        if row[10] != '' and row[14] > 0:  # Only include non-empty lines & non-zero contributions.
            headings = 'Run_id,Meas_No,Quantity_Label,Value,Uncert,DoF,Sens_Co,U_Contrib'
            values = (f"'{this_run}',{meas_no},'{row[9]}',{row[10]},{row[11]},{df},"
                      f"{row[13]},{row[14]}")
            budget_query = f"INSERT OR REPLACE INTO Uncert_Contribs ({headings}) VALUES ({values});"
            curs.execute(budget_query)
            print(f'Writing budget line for {row[9]}')

        if meas_row_count == 1:  # Must be on first row of this measurement block.
            Vtest_val = row[1]
            meas_date = convert_date_fmt(row[2])
            # print(f'meas_date:\n{meas_date}')
            T_val = row[3]
            R_val, R_unc, R_df, R_expu = row[4:8]
            continue
        elif meas_row_count == 2:  # Must be on 2nd row of this measurement block.
            Vtest_unc = row[1]
            T_unc = row[3]
            continue
        elif meas_row_count == 3:  # Must be on 3rd row of this measurement block.
            Vtest_df = row[1]
            T_df = row[3]
            """
            Write measurement info to Results table.
            """
            headings = 'Run_id,Meas_Date,Analysis_Note,Meas_No,Parameter,Value,Uncert,DoF,ExpU'
            for key, val in {'V': [Vtest_val, Vtest_unc, Vtest_df, 'NULL'],
                             'T': [T_val, T_unc, T_df, 'NULL'],
                             'R': [R_val, R_unc, R_df, R_expu]}.items():
                values = (f"'{this_run}','{meas_date}','{this_analysis_note}',"
                          f"{meas_no},'{key}',{val[0]},{val[1]},{val[2]},{val[3]}")
                result_query = f"INSERT OR REPLACE INTO Results ({headings}) VALUES ({values});"
                print('Values:', values)
                curs.execute(result_query)
                print(f'Writing data for meas_no {meas_no} ({meas_row_count} rows)')

            """
            Update Runs table with mean Meas_Date & Analysis_Note
            """
            runs_query = (f"UPDATE OR REPLACE Runs SET Meas_Date='{meas_date}', Analysis_Note='{this_analysis_note}' "
                          f"WHERE Run_Id = '{this_run}';")
            curs.execute(runs_query)
            print(f'Updating Runs table: meas_date - {meas_date}; {this_analysis_note}.')

        if row[10] == '':  # Value column
            """
            We've reached the blank row between data blocks, so the
            next measurement's data block starts next row.
            """
            first_meas_block = False
            next_meas_block = True
            print(f'END OF MEASUREMENT for meas_no {meas_no}.\n')
            meas_row_count = 0
            run_row_count = 0
            meas_no += 1
    else:
        continue
# tidy up:
if test is False:
    print('\nCommitting changes to db...')
    db_connection.commit()  # Assign all updates to database.

curs.close()
if db_connection:
    db_connection.close()
