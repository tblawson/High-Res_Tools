# -*- coding: utf-8 -*-


import pylightxl as xl


filename = r'G:\My Drive\TechProcDev\E052_TeraOhm-prep\HRBC_Tera-prep_copy.xlsx'
wb = xl.readxl(filename, ('Results',))

n = 0
for row in wb.ws('Results').rows:
    n += 1
    print(f'{n}\t{row}')
    if n > 3 and row[9] == '':
        print(f'Printed {n} rows')
        break
