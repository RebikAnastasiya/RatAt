import os

import mne
import matplotlib.pyplot as plt
import numpy as np
from scipy.signal import welch
from mne.minimum_norm import read_inverse_operator, compute_source_psd, compute_source_psd_epochs

from fooof import FOOOF
from fooof.sim.gen import gen_power_spectrum
from fooof.sim.utils import set_random_seed
from fooof.plts.spectra import plot_spectrum
from fooof.plts.annotate import plot_annotated_model

from openpyxl import Workbook

from ratat_utils import *

report_dir_name = 'foof_report'
r2_col_idx = 2
error_col_idx = 3
aper_offset_col_idx = 5
aper_exp_col_idx = 6
per_start_idx = 8


def get_report_worksheet():
    wb = Workbook()
    ws = wb.active
    report__append_header(ws)
    return (wb, ws)

def hack_to_support_xlwt(ws, row, col, val):
    ws.cell(row=row+1, column=col+1).value = val

def report__append_header(ws):
    hack_to_support_xlwt(ws, 0, 0, 'File')
    hack_to_support_xlwt(ws, 0, 1, 'Channel')
    hack_to_support_xlwt(ws, 0, r2_col_idx, 'R^2 of model')
    hack_to_support_xlwt(ws, 0, error_col_idx, 'Error of the fit')
    hack_to_support_xlwt(ws, 0, aper_offset_col_idx, 'Offset (apper)')
    hack_to_support_xlwt(ws, 0, aper_exp_col_idx, 'Exponent (apper)')

    hack_to_support_xlwt(ws, 0, per_start_idx, 'Periodic component data (CF, PW, BW)')

current_report_row_idx = 1

def report__append_foof_line(ws, idx, filename, channelName, fooof_obj):
    hack_to_support_xlwt(ws, idx, 0, filename)
    hack_to_support_xlwt(ws, idx, 1, channelName)
    
    [offset, exp], peak_params, r_squared, fit_error, gauss_params = fooof_obj.get_results()
    
    hack_to_support_xlwt(ws, idx, r2_col_idx, r_squared)
    hack_to_support_xlwt(ws, idx, error_col_idx, fit_error)
    hack_to_support_xlwt(ws, idx, aper_offset_col_idx, offset)
    hack_to_support_xlwt(ws, idx, aper_exp_col_idx, exp)
    
    offset_idx = 0
    for [a, b, c] in peak_params:
        hack_to_support_xlwt(ws, idx, per_start_idx + offset_idx, a)
        
        offset_idx += 1
        hack_to_support_xlwt(ws, idx, per_start_idx + offset_idx, b)
        
        offset_idx += 1
        hack_to_support_xlwt(ws, idx, per_start_idx + offset_idx, c)
        offset_idx += 2

def perorm_fooof_analysis_with_report(abs_filename, data_filename = None, filterFreq=None):
    log_i('starting FOOOF report for file {0}', abs_filename)
    
    _, filename = os.path.split(abs_filename)
    wb, ws = get_report_worksheet()
    
    raw_data = mne.io.read_raw_edf(data_filename, preload=True)
    df = raw_data.compute_psd().to_data_frame()

    if data_filename is None:
        data_filename = abs_filename
    
    # perform filters
    if filterFreq is not None:
        df = df[df['freq'] < filterFreq]
    
    # plots

    channels = raw_data.ch_names
    
    fig, axes = plt.subplots(3, len(channels), figsize=(20, 15))
    
    for idx, ch_name in zip(range(0, len(channels)), channels):
        ax = axes[0][idx]
        ax.set_title(ch_name)
        plot_spectrum(df['freq'].to_numpy(), df[ch_name].to_numpy(), log_powers=True, ax=ax)
        
        fm = FOOOF(min_peak_height=0.05, verbose=False)
        fm.fit(df['freq'].to_numpy(), df[ch_name].to_numpy())
        
        ax = axes[1][idx]
        fm.plot(ax=ax, add_legend=False)
        
        ax = axes[2][idx]
        fm.plot(plot_peaks='shade', peak_kwargs={'color' : 'green'}, ax=ax, add_legend=False)
        
        report__append_foof_line(ws, idx+1, filename, ch_name, fm)

    report_xlsx_filename = get_step_filename(abs_filename, report_dir_name, suffix='__psd', override_ext='xlsx')
    wb.save(report_xlsx_filename)
    log_i('\tFOOOF: saved xlsx: {0}', report_xlsx_filename)
    
    fig.suptitle('file: ' + filename)
    
    fig_filename = get_step_filename(abs_filename, report_dir_name, suffix='__psd', override_ext='png')
    fig.savefig(fig_filename)
    log_i('\tFOOOF: saved figure: {0}', fig_filename)
