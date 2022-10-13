# -*- coding: utf-8 -*-
"""
Results_to_Res_Info.py - Initial version (Python 3).

Created on Tue 11/08/2020

@author: t.lawson

Populate Res_Info table with info calculated from Results table.

First, the calibration date is calculated as the mean of all measurement dates,
regardless of test voltage.

Next, the data is split into subsets by nominal test voltage.
For the most-common nominal test voltage, the mean test voltage, mean resistance and
reference temperature are calculated and total weighted least squares (WTLS) fits
are used to determine the 1st-order temperature coefficient, alpha_LV or alpha_HV -
The mean of these two values is returned as the parameter 'alpha'.
Beta is not calculated.

The reference value 'R0' is equal to R0_LV.
The reference voltage 'VRef' is equal to the value of VRef_LV.
The reference temperature 'TRef' is equal to the value of TRef_LV.

Next, alpha is used to correct all data to T = TRef. The resulting data set is subject
to another WTLS fit to determine the voltage coefficient, gamma.

Finally, all data (LV and HV) is corrected for alpha and gamma
and a final WTLS fit is used to determine the drift coefficient tau.
"""


import sqlite3
import GTC as gtc
import datetime as dt
import time
import math

T_FMT = '%Y-%m-%d %H:%M:%S'
TIME_UNC_DAYS = 0.1  # Assume 0.1 day( ~2.4 hr) uncert on measurement date.
LIMIT_MAX = 100  # Max no. of runs to return, for a given Rx.

'''
_______________________________________________________
Helper functions:
-------------------------------------------------------
'''


def av_time(time_lst, rtn_type):
    t_av = 0.0
    n = float(len(time_lst))
    for d_str in time_lst:
        t_dt = dt.datetime.strptime(d_str, T_FMT)
        t_tup = dt.datetime.timetuple(t_dt)
        t_av += time.mktime(t_tup)  # Time as float (seconds from epoch)

    # Calculate average:
    t_av /= n
    if rtn_type == 'days':
        return t_av/86400.0
    if rtn_type == 'str':
        t_av_fl = dt.datetime.fromtimestamp(t_av)
        return t_av_fl.strftime(T_FMT)  # av. time as string


def ureal_to_str(un):
    archive = gtc.pr.Archive()
    d = {un.label: un}
    archive.add(**d)
    return gtc.pr.dumps_json(archive)


def str_to_ureal(j_str, name):
    archive = gtc.pr.loads_json(j_str)
    return archive.extract(name)


'''
_______________________________________________________
-------------------------------------------------------
Main script starts here...
'''

# Set up connection to database:
test = True
Q_test_script = input('Test before running properly? (Y/N) >')
if Q_test_script.startswith('N'):
    test = False  # This is NOT a test!

db_path = input('Full Resistors.db path? (press "d" for default location) >')
if db_path == 'd':
    db_path = r'G:\My Drive\Resistors.db'  # Default location.

db_connection = sqlite3.connect(db_path)
curs = db_connection.cursor()

# User input - Rx:
hamon10m = False
Rx_name = input('Rx_name? >')
if Rx_name == 'H100M 10M':
    hamon10m = True

Rs_name = input("Preferred Rs_name(s)? (For any Rs press 'Enter') >")

'''
---------------------------------------
Select whether to analyse -
* Just results in the most recent run (hopefully more accurate
values for Cal-Date, R0, TRef, VRef. Other parameters not calculated).
OR
* All available results included (allows calculation of tau,...? ):
'''
limit_choices = {'r': 1, 'a': LIMIT_MAX}
response = input("Restrict to results from most-recent run ('r')"
                 " or use all valid results ('a')?")
assert response in limit_choices.keys(), 'Error - Invalid input!'
run_count = limit_choices[response]

'''
---------------------------------------
Extract data from Results table:
'''
if Rs_name == '':
    Rs_term = ''
else:
    Rs_term = f"AND Rs_Name='{Rs_name}'"


# Run_Id, Meas_Date, Calc_Note, Meas_No, Parameter, Value, Uncert, Dof, ExpU, k:
q_get_results = ("SELECT * FROM Results WHERE (Excluded IS NULL OR Excluded='No') AND Run_Id IN "
                 f"(SELECT Run_Id FROM Runs WHERE Rx_Name = '{Rx_name}' {Rs_term} AND "
                 "Range_Mode='FIXED' AND (Blacklist IS NULL OR Blacklist='No') "
                 f"ORDER BY Meas_Date DESC LIMIT {run_count});")
curs.execute(q_get_results)
rows = curs.fetchall()
assert len(rows) > 0, 'No measurements found - check spelling of resistor name!'
print(f"\nFound {len(rows)} processed measurements (R, T & V).")

measurements = []
param_count = 0
this_T = this_V = this_R = 0.0
for meas_row in rows:
    this_run = meas_row[0]
    this_date = meas_row[1]
    this_calc_note = meas_row[2]
    this_value = meas_row[3]
    param = meas_row[4]
    if meas_row[5] is None:
        val = 0
    else:
        val = meas_row[5]
    if meas_row[6] is None:
        unc = 0
    else:
        unc = meas_row[6]
    if meas_row[7] is None:
        df = 1e6
    else:
        df = meas_row[7]

    ureal_str = meas_row[11]

    print(f"{this_run}: \tMeas. {this_value}: ({param} = {val})")

    """
    Construct / extract GTC ureals for each Result record:
    """
    if param == 'T':
        lbl = f"{Rx_name}_T_meas={this_value}_{this_run}"
        if ureal_str is not None:
            # print('Thawing...:', lbl)
            this_T = str_to_ureal(ureal_str, lbl)
            # print(f'Label:___{this_T.label}, UID:___{this_T._node.uid}')
        else:  # Treat as fundamental ureal.
            this_T = gtc.ureal(val, unc, df, label=lbl)
        param_count += 1

    elif param == 'V':
        lbl = f"{Rx_name}_V_meas={this_value}_{this_run}"
        if ureal_str is not None:
            # print('Thawing...:', lbl)
            # print(ureal_str)
            this_V = str_to_ureal(ureal_str, lbl)
            # print(f'Label:___{this_V.label}, UID:___{this_V._node.uid}')
        else:  # Treat as fundamental ureal.
            this_V = gtc.ureal(val, unc, df, label=lbl)
        param_count += 1

    elif param == 'R':
        lbl = f"{Rx_name}_R_meas={this_value}_{this_run}"
        if ureal_str is not None:
            # print('Thawing...:', lbl)
            this_R = str_to_ureal(ureal_str, lbl)
            # print(f'Label:___{this_R.label}, UID:___{this_R._node.uid}')
        else:
            this_R = gtc.ureal(val, unc, df, label=lbl)
        param_count += 1

    if param_count == 3:
        this_meas = {'runid': this_run, 'meas': this_value,
                     'm_date': this_date, 'c_note': this_calc_note,
                     'T': this_T, 'V': this_V, 'R': this_R}
        measurements.append(this_meas)
        param_count = 0

'''
---------------------------------------
Calculate mean date:
'''
# List of dates in str format 'YYYY-MM-DD hh:mm:ss':
all_dates = [m['m_date'] for m in measurements]
mean_date_val = av_time(all_dates, 'days')  # Num days from start of epoch.
mean_date_str = av_time(all_dates, 'str')  # Date-time as a string.
mean_date_unc = TIME_UNC_DAYS
mean_date_df = len(all_dates) - 1
lbl = f'{Rx_name}_t0'
mean_date_ureal = gtc.ureal(mean_date_val, mean_date_unc, mean_date_df, label=lbl)

# Generate reference comment comprising all unique runid's.
runids = set(m['runid'] for m in measurements)
ref_comment = ";\n ".join(runids)
print('\nData extracted from runs:\n', ref_comment)

# q_get_ids = f"SELECT DISTINCT Run_Id FROM Runs WHERE Rx_name='{Rx_name}';"
# curs.execute(q_get_ids)
# id_rows = curs.fetchall()
# runids = []
# for tup in id_rows:
#     runids.append(tup[0])
# ref_comment = ", ".join(runids)

# write 'date' record to Res_Info table:
headings = 'R_Name,Parameter,Value,Uncert,DoF,Label,Ref_Comment,Ureal_Str'
values = (f"'{Rx_name}','Cal_Date','{mean_date_str}',{mean_date_unc},{mean_date_df},'{lbl}',"
          f"'{ref_comment}','{ureal_to_str(mean_date_ureal)}'")
q_date = f"INSERT OR REPLACE INTO Res_Info ({headings}) VALUES ({values});"
curs.execute(q_date)

if hamon10m:  # Include inferred value(s) for series-connected Hamon.
    lbl = 'H100M 1G' + '_t0'
    headings = 'R_Name,Parameter,Value,Uncert,DoF,Label,Ref_Comment,Ureal_Str'
    values = (f"'H100M 1G','Cal_Date','{mean_date_str}',{mean_date_unc},{mean_date_df},'{lbl}',"
              f"'{ref_comment}','{ureal_to_str(mean_date_ureal)}'")
    q_date = f"INSERT OR REPLACE INTO Res_Info ({headings}) VALUES ({values});"
    curs.execute(q_date)

'''
---------------------------------------
Separate data by test-voltage:
    * Positive voltages only,
    * FIXED range mode only,
    * No Blacklisted runs,
    * No Excluded results.
'''
testV_query = ("SELECT DISTINCT V1set FROM Raw_Data WHERE V1set>0 AND Run_Id IN "
               f"(SELECT Run_Id FROM Runs WHERE Rx_Name='{Rx_name}' AND "
               f"Range_Mode = 'FIXED' AND (Blacklist IS NULL OR Blacklist='No') AND "
               f"Run_Id NOT IN (SELECT Run_Id FROM Results WHERE Excluded='Yes') "
               f"ORDER BY Meas_Date DESC LIMIT {run_count});")
curs.execute(testV_query)
testVs = [int(row[0]) for row in curs.fetchall()]
print(f"\nFound these test-voltages: {testVs}")

# Set up structure to hold measurements:
measurements_by_testV = {}
for V in testVs:
    measurements_by_testV.update({int(V): []})

# Assign each measurement to sub-sets, based on test-V:
for m in measurements:
    print(m['runid'], f"meas_no={m['meas']}; R={m['R']}; V={m['V']}")
    nom_V = round(m['V'].x)
    for test_v in testVs:
        if nom_V == test_v:
            measurements_by_testV[test_v].append(m)

# Find largest sub-set by test-V:
most_common_testV = 0
largest_sample = 0
for test_v in sorted(testVs):  # (See next comment).
    sample_size = len(measurements_by_testV[test_v])
    print(f"Num. {test_v} V measurements:\t\t{sample_size}")
    if sample_size > largest_sample:  # Lowest test-V 'wins' in a draw.
        largest_sample = sample_size
        most_common_testV = test_v
print(f"Largest sub-set is {most_common_testV} V with {largest_sample} members.")

'''
---------------------------------------
Calculate mean T, V, R for each test-V
and calculate alpha (T-Co):
'''
params_by_testV = {}
for v in testVs:
    print(f'Measurements at {v}V:\n', measurements_by_testV[v])
    params_by_testV.update({v: {}})
    T_av = gtc.result(gtc.fn.mean([m['T'] for m in measurements_by_testV[v]]),
                      label=f'{Rx_name}_TRef')  # TRef for this test_V sample.
    V_av = gtc.result(gtc.fn.mean([m['V'] for m in measurements_by_testV[v]]),
                      label=f'{Rx_name}_VRef')  # VRef for this test_V sample.
    R_av = gtc.result(gtc.fn.mean([m['R'] for m in measurements_by_testV[v]]),
                      label=f'{Rx_name}_R0')  # R0 for this test_V sample.
    params_by_testV[v].update({'T': T_av, 'V': V_av, 'R': R_av})

    # Recalculate T's as shift from average T:
    T_rel = [gtc.result(m['T'].x - T_av) for m in measurements_by_testV[v]]

    # Find R (at mean T) and alpha [Ohm/C] at this test-V:
    R0_a, alpha_a = gtc.ta.line_fit_wtls(T_rel,
                                         [m['R'].x for m in measurements_by_testV[v]],
                                         [m['T'].u for m in measurements_by_testV[v]],
                                         [m['R'].u for m in measurements_by_testV[v]]).a_b
    # R0 = gtc.result(R0_a, label=f'{Rx_name}_R0')

    # Calculate R, alpha with type B uncerts then merge with type A result:
    R0_b, alpha_b = gtc.tb.line_fit_wtls(T_rel,
                                         [m['R'] for m in measurements_by_testV[v]],
                                         [m['T'].u for m in measurements_by_testV[v]],
                                         [m['R'].u for m in measurements_by_testV[v]]).a_b
    alpha_ab = gtc.result(gtc.ta.merge(alpha_a, alpha_b), label=f'{Rx_name} at V={v}_alpha')
    R0 = gtc.result(gtc.ta.merge(R0_a, R0_b), label=f'{Rx_name} at V={v}_R0')
    # print(f'Merged alpha_ab (at V={v}) [ohm/C]: {alpha_a} & {alpha_b} -> {alpha_ab}')
    alpha = gtc.result(alpha_ab / R0, label=f'{Rx_name} at_{v} alpha')
    params_by_testV[v].update({'alpha': alpha, 'R0': R0})

    # write records to Res_Info table for most common test-V sample:
    if v == most_common_testV:
        headings = 'R_Name,Parameter,Value,Uncert,doF,Label,Ref_Comment,Ureal_Str'
        # TRef:
        TRef = T_av
        lbl = TRef.label
        values = f"'{Rx_name}','TRef',{TRef.x},{TRef.u},{TRef.df},'{lbl}','{ref_comment}','{ureal_to_str(TRef)}'"
        q = f"INSERT OR REPLACE INTO Res_Info ({headings}) VALUES ({values});"
        curs.execute(q)

        # VRef:
        VRef = V_av
        lbl = VRef.label
        values = f"'{Rx_name}','VRef',{VRef.x},{VRef.u},{VRef.df},'{lbl}','{ref_comment}','{ureal_to_str(VRef)}'"
        q = f"INSERT OR REPLACE INTO Res_Info ({headings}) VALUES ({values});"
        curs.execute(q)

        # R0:
        R0 = R_av
        lbl = R0.label
        values = f"'{Rx_name}','R0',{R0.x},{R0.u},{R0.df},'{lbl}','{ref_comment}','{ureal_to_str(R0)}'"
        q = f"INSERT OR REPLACE INTO Res_Info ({headings}) VALUES ({values});"
        curs.execute(q)

        if hamon10m:  # Include inferred value(s) for series-connected Hamon.
            # TRef:
            lbl = 'H100M 1G' + '_TRef'
            dummy = TRef*2  # Trick GTC to create a copy of TRef...
            TRef_H1G = gtc.result(dummy/2, label=lbl)  # ...with a different label.
            values = (f"'H100M 1G','TRef',{TRef_H1G.x},{TRef_H1G.u},{TRef_H1G.df},'{lbl}',"
                      f"'{ref_comment}','{ureal_to_str(TRef_H1G)}'")
            q = f"INSERT OR REPLACE INTO Res_Info ({headings}) VALUES ({values});"
            curs.execute(q)

            # VRef:
            lbl = 'H100M 1G' + '_VRef'
            VRef_H1G = gtc.ureal(10*VRef.x, 10*VRef.u, VRef.df, label=lbl)
            values = (f"'H100M 1G','VRef',{VRef_H1G.x},{VRef_H1G.u},{VRef_H1G.df},'{lbl}',"
                      f"'{ref_comment}','{ureal_to_str(VRef_H1G)}'")
            q = f"INSERT OR REPLACE INTO Res_Info ({headings}) VALUES ({values});"
            curs.execute(q)

            # R0:
            lbl = 'H100M 1G' + '_R0'
            R0_H1G = gtc.ureal(100*R0.x, 100*R0.u, R0.df, lbl)
            values = (f"'H100M 1G','R0',{R0_H1G.x},{R0_H1G.u},{R0_H1G.df},'{lbl}'," 
                      f"'{ref_comment}','{ureal_to_str(R0_H1G)}'")
            q = f"INSERT OR REPLACE INTO Res_Info ({headings}) VALUES ({values});"
            curs.execute(q)

'''
---------------------------------------
*** ONLY do this if processing multiple runs! ***
Calculate mean alpha & write record to Res_Info table:
'''
if run_count == LIMIT_MAX:  # Process all runs
    # Define 'book-value' / parameters:
    R_0 = params_by_testV[most_common_testV]['R0']
    T_0 = params_by_testV[most_common_testV]['T']
    V_0 = params_by_testV[most_common_testV]['V']

    lbl = Rx_name + '_alpha'
    alpha = gtc.result(gtc.fn.mean([params_by_testV[v]['alpha'] for v in testVs]),
                       label=lbl)  # Units: [/deg_C]
    print(f'\nAlpha = ({alpha.x} +/- {alpha.u} /C), dof = {alpha.df}')

    # (Re-use headings from last time)
    values = f"'{Rx_name}','alpha',{alpha.x},{alpha.u},{alpha.df},'{lbl}','{ref_comment}','{ureal_to_str(alpha)}'"
    q = f"INSERT OR REPLACE INTO Res_Info ({headings}) VALUES ({values});"
    curs.execute(q)

    if hamon10m:  # Include inferred value(s) for series-connected Hamon.
        lbl = 'H100M 1G' + '_alpha'
        dummy = alpha*2  # Trick GTC to create a copy of alpha..
        alpha_H1G = gtc.result(dummy/2, label=lbl)  # ...with a different label.
        values = (f"'H100M 1G','alpha',{alpha_H1G.x},{alpha_H1G.u},{alpha_H1G.df},'{lbl}',"
                  f"'{ref_comment}','{ureal_to_str(alpha_H1G)}'")
        q = f"INSERT OR REPLACE INTO Res_Info ({headings}) VALUES ({values});"
        curs.execute(q)

    '''
    ---------------------------------------
    Correct ALL R values to T = TRef = params_by_testV[most_common_testV]['T']:
    '''
    R_vals_T_corr = [(m['R']*(1 + alpha*(m['T'] - T_0))) for m in measurements]

    '''
    ---------------------------------------
    Calculate gamma:
    '''
    # Recalculate V's as shift from average V:
    if len(testVs) > 1:
        V_av = gtc.fn.mean([m['V'] for m in measurements])
        V_rel = [m['V'] - V_av for m in measurements]

        # Fit to (R vs corrected_V) - units of gamma_ [Ohm/V] (TYPE A):
        R0_avV_a, gamma_a = gtc.ta.line_fit_wtls([V.x for V in V_rel],
                                                 [R.x for R in R_vals_T_corr],
                                                 [V.u for V in V_rel],
                                                 [R.u for R in R_vals_T_corr]).a_b

        # Fit to (R vs corrected_V) - units of gamma_ [Ohm/V] (TYPE B):
        R0_avV_b, gamma_b = gtc.tb.line_fit_wtls(V_rel,
                                                 R_vals_T_corr,
                                                 [V.u for V in V_rel],
                                                 [R.u for R in R_vals_T_corr]).a_b

        gamma_ab = gtc.ta.merge(gamma_a, gamma_b)
        lbl = f'{Rx_name}_gamma'
        gamma = gtc.result(gamma_ab/R_0, label=lbl)  # Units: [/V]
    else:  # Gamma not calculated, (assumed zero).
        gamma = gtc.ureal(0, 0, 1e6, label=lbl)
    print(f'Gamma = ({gamma.x} +/- {gamma.u} /V), dof = {gamma.df}')

    '''
    ---------------------------------------
    Write gamma record to Res_Info table IF UNCERT > 0:
    '''
    if math.isinf(gamma.df):
        df = 1e6
    else:
        df = gamma.df

    if gamma.u > 0:
        # (Re-use Res_Info headings from last time)
        lbl = Rx_name + '_gamma'
        values = f"'{Rx_name}','gamma',{gamma.x},{gamma.u},{df},'{lbl}','{ref_comment}','{ureal_to_str(gamma)}'"
        q = f"INSERT OR REPLACE INTO Res_Info ({headings}) VALUES ({values});"
        curs.execute(q)

        if hamon10m:  # Include inferred value(s) for series-connected Hamon.
            lbl = 'H100M 1G' + '_gamma'
            dummy = gamma*2  # Trick GTC to create a copy of gamma...
            gamma_H1G = gtc.result(dummy/2, label=lbl)  # ...with a different label.
            values = (f"'H100M 1G','gamma',{gamma_H1G.x/10},{gamma_H1G.u/10},{gamma_H1G.df},'{lbl}',"
                      f"'{ref_comment}','{ureal_to_str(gamma_H1G)}'")
            q = f"INSERT OR REPLACE INTO Res_Info ({headings}) VALUES ({values});"
            curs.execute(q)

    '''
    ---------------------------------------
    Correct all R values to T=T_0 and V=V_0:
    '''
    if len(testVs) <= 1:
        R_vals_TV_corr = [(m['R']*(1 + alpha*(m['T'] - T_0))) for m in measurements]
    else:
        R_vals_TV_corr = [(m['R']*(1 + alpha*(m['T'] - T_0) + gamma*(m['V'] - V_0))) for m in measurements]

    '''
    ---------------------------------------
    Calculate tau (drift rate):
    '''
    # Recalculate dates relative to mean_date (diff in days):
    mean_date_dt = dt.datetime.strptime(mean_date_str, T_FMT)

    # List of time-shifts (in days) relative to mean date:
    t_rel_days = [(
            (dt.datetime.strptime(m['m_date'], T_FMT) - mean_date_dt).days +
            (dt.datetime.strptime(m['m_date'], T_FMT) - mean_date_dt).seconds/86400
    ) for m in measurements]

    # List of time-shift-ureals (in days) relative to mean date:
    t_rel_days_un = [gtc.ureal(t, TIME_UNC_DAYS) for t in t_rel_days]

    # Fit to (R vs date) - Units of tau_ [Ohm/day] (TYPE A):
    R0_avt_a, tau_a = gtc.ta.line_fit_wtls(t_rel_days,
                                           [R.x for R in R_vals_TV_corr],
                                           [0.1 for t in t_rel_days],  # Assumed time-uncert for all measurements.
                                           [R.u for R in R_vals_TV_corr]).a_b

    # Fit to (R vs date) - Units of tau_ [Ohm/day] (TYPE B):
    R0_avt_b, tau_b = gtc.tb.line_fit_wtls(t_rel_days_un,
                                           R_vals_TV_corr,
                                           [0.1 for t in t_rel_days],  # Assumed time-uncert for all measurements.
                                           [R.u for R in R_vals_TV_corr]).a_b

    tau_ab = gtc.ta.merge(tau_a, tau_b)
    tau = gtc.result(tau_ab/R_0, label=f'{Rx_name}_tau')  # Units: [/day]
    print(f'Tau = ({tau.x} +/- {tau.u}) /day,  dof = {tau.df}')

    '''
    ---------------------------------------
    Write tau record to Res_Info table:
    '''
    # (Re-use Res_Info headings from last time)
    lbl = Rx_name + '_tau'
    values = f"'{Rx_name}','tau',{tau.x},{tau.u},{tau.df},'{lbl}','{ref_comment}','{ureal_to_str(tau)}'"
    q = f"INSERT OR REPLACE INTO Res_Info ({headings}) VALUES ({values});"
    curs.execute(q)

    if hamon10m:  # Include inferred value(s) for series-connected Hamon.
        lbl = 'H100M 1G' + '_tau'
        dummy = tau*2  # Trick GTC to create a copy of tau...
        tau_H1G = gtc.result(dummy/2, label=lbl)  # ...with a different label.
        values = f"'H100M 1G','tau',{tau_H1G.x},{tau_H1G.u},{tau_H1G.df},'{lbl}','{ref_comment}','{ureal_to_str(tau_H1G)}'"
        q = f"INSERT OR REPLACE INTO Res_Info ({headings}) VALUES ({values});"
        curs.execute(q)

'''
---------------------------------------
Tidy up:
'''
if test is False:
    db_connection.commit()  # Assign all updates to database.

curs.close()
if db_connection:
    db_connection.close()
