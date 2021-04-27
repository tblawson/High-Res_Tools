# -*- coding: utf-8 -*-
"""
Calulates the DMM gain on a given range at a given nominal output voltage,
given gain correction factors from a calibration report.

The output string can be copy-pasted to the 'Parameters' sheet of an HRBC XL file.
"""
import GTC

model_sn = input('<model>_<sn>? ')
report_no = input('report S-num? ')
print('Enter an empty string to quit or\n'
      'Input Range (V), unsigned nominal readout(V), +applied V(V), -applied V(V), '
      'Exp U(V), k (in order, separated by spaces):')
while True:
    gain_line_str = input('> ')
    if gain_line_str == '':
        break
    gain_line_words = gain_line_str.split(' ')
    if len(gain_line_words) != 6:
        print('wrong number of data items!')
        continue
    # print(gain_line_words)
    g_dict = {'range': float(gain_line_words[0]),
              'nom_disp': float(gain_line_words[1]),
              'v_pos': float(gain_line_words[2]),
              'v_neg': float(gain_line_words[3]),
              'exp_u': float(gain_line_words[4]),
              'k': float(gain_line_words[5])}

    if g_dict['range'] >= 1:
        rng = int(g_dict['range'])
    else:
        rng = g_dict['range']
    if g_dict['nom_disp'] >=1:
        V_disp = int(g_dict['nom_disp'])
    else :
        V_disp = g_dict['nom_disp']

    val_p = g_dict['v_pos']
    val_n = g_dict['v_neg']
    std_u = g_dict['exp_u']/g_dict['k']
    dof = GTC.rp.k_to_dof(g_dict['k'], 95)
    Vp = GTC.ureal(val_p, std_u, dof)
    Vn = GTC.ureal(val_n, std_u, dof)
    Gav = 2*V_disp/(Vp-Vn)

    param = f'Vgain_{V_disp}r{rng}'
    label = '_'.join([model_sn, param])
    print(f'{param}\t{Gav.x: .8}\t{Gav.u: .2}\t{Gav.df}\t{label}\t{report_no}')

print('DONE')
