import os

from PyQt6 import (
    QtWidgets as qw,
    QtGui as qg,
    QtCore as qc
)

import mne, pandas as pd, numpy as np

from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

import matplotlib.pyplot as plt
import matplotlib.widgets as plt_w
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backend_bases import key_press_handler as mpl_key_press_handler

from ratat_utils import *
from ratat_widgets import *

MIN_ALLOWED_DURATION_IN_SECONDS = 0.5
PAGE_LENGTH = 10

class WaveletWindow(qw.QMainWindow):
    xmin = 0
    xmax = 0
    x_scale = 0

    current_channel = combobox_accessor('CurrentChannel')
    new_mark_name = lineedit_accessor('NewMarkName')

    current_marks_page = 1
    marks = dict()
    raw_data_label_counters = dict()

    current_selection_span = None
    ax_wavelet__CB = None

    def closeEvent(self, event):
        # NOTE: this is hack
        plt.close()

    def __init__(self, settings, rawdata, on_close=None, *args, **kwargs):
        super(WaveletWindow, self).__init__()

        self.Settings = settings
        self.rawdata = rawdata
        self.on_close = on_close

        self.freq_min = settings.wl_freq_min
        self.freq_max = settings.wl_freq_max
        self.freq_step = settings.wl_freq_step
        self.n_cycles = settings.wl_n_cycles


        rawdata_label_counters = dict()
        for idx, onset in enumerate(self.rawdata.annotations.onset):
            description = self.rawdata.annotations.description[idx]

            if description.startswith('BAD_'):
                continue

            if description not in rawdata_label_counters:
                rawdata_label_counters[description] = 0

            if rawdata_label_counters[description] != 0:
                label = description + str(rawdata_label_counters[description])
            else:
                label = description

            rawdata_label_counters[description] += 1

            if label in self.marks:
                continue

            duration = self.rawdata.annotations.duration[idx]
            self.marks[label] = (label, onset, onset + duration)


        self.init_window()
        self.init_plots()
        self.init_elements()

        self.render_chart()

    def init_window(self):
        self.setWindowTitle('MNE Toolbox // Wavelet')
        self.showMaximized()
        self.setWindowIcon(RatatIcon())

    def init_plots(self):
        fig, ax = plt.subplot_mosaic(
            [
                ['lines', 'lines'],
                ['wavelet', 'psd'],
            ],
            width_ratios=[1, 1],
            layout='constrained',
        )

        self.fig = fig
        self.ax_lines = ax['lines']
        self.ax_wavelet = ax['wavelet']
        self.ax_psd = ax['psd']


    def init_elements(self):
        main_layout = MainLayout()
        chart_layout = qw.QHBoxLayout()
        control_layout = qw.QVBoxLayout()
        control_layout.setContentsMargins(10,5,10,10)

        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.mpl_connect('key_press_event', self.event__on_key_press)
        self.canvas.setFocusPolicy(qc.Qt.FocusPolicy.StrongFocus)

        self.toolbox = NavigationToolbar(self.canvas, self)
        main_layout.addWidget(self.toolbox)

        control_layout.addWidget(ToolboxHeader('Current channel'))
        self.setCentralWidget(main_layout.get_widget())

        cb = qw.QComboBox(self)
        for ch in self.rawdata.ch_names:
            cb.addItem(ch, ch)
        cb.setCurrentIndex(0)
        cb.setObjectName('CurrentChannel')
        cb.currentIndexChanged.connect(self.render_chart)
        control_layout.addWidget(cb)

        control_layout.addWidget(ToolboxHeader('Add label'))
        with BtnLayout(None) as layout:
            i = qw.QLineEdit(self)
            i.setObjectName('NewMarkName')
            layout.addWidget(i)
            layout.add('Append', self.event__add_mark)
            control_layout.addLayout(layout)

        control_layout.addWidget(ToolboxHeader('Marks'))

        self.mark_widget = qw.QWidget()
        control_layout.addWidget(self.mark_widget)

        self.render_marks()

        control_layout.addStretch()

        main_layout.addLayout(chart_layout)
        chart_layout.addLayout(control_layout, stretch=1)
        chart_layout.addWidget(self.canvas, stretch=5)

        self.setCentralWidget(main_layout.get_widget())

    def render_marks(self):
        # clear layout

        current_layout = self.mark_widget.layout()
        if current_layout:
            qw.QWidget().setLayout(current_layout)

        new_mark_layout = qw.QVBoxLayout()

        while new_mark_layout.count():
            child = new_mark_layout.takeAt(0)
            widgetToRemove = child.widget()
            if widgetToRemove:
                new_mark_layout.removeWidget(widgetToRemove)
                widgetToRemove.setParent(None)

        ordered_values = sorted(self.marks.values(), key=lambda x: x[1])

        total_value_len = len(ordered_values)
        if total_value_len > PAGE_LENGTH:
            total_pages = np.ceil(total_value_len / PAGE_LENGTH)
            ordered_values = ordered_values[
                ((self.current_marks_page - 1) * PAGE_LENGTH):((self.current_marks_page) * PAGE_LENGTH)
            ]

            with BtnLayout(None) as blt:
                blt.addWidget(qw.QLabel(f"[{int(self.current_marks_page)}/{int(total_pages)}]"))
                blt.addStretch()
                if self.current_marks_page > 1:
                    blt.add('<', self.event__mark_prev_page)

                if self.current_marks_page < total_pages:
                    blt.add('>', self.event__mark_next_page)

                new_mark_layout.addLayout(blt)

        for mark_label, minVal, maxVal in ordered_values:
            with BtnLayout(None) as blt:
                duration = maxVal - minVal

                blt.addWidget(qw.QLabel(f"{mark_label} ({duration:.2f}s)"))

                blt.addStretch()

                closure_label = mark_label
                log_i('label: {0}', closure_label)
                blt.add('V', lambda *args, label=closure_label: self.event__show_mark(label))
                
                btn = blt.add('X', lambda *args, label=closure_label: self.event__remove_mark(label))
                btn.setStyleSheet('background: red; color: white; font-weight: bold;')

                new_mark_layout.addLayout(blt)

        new_mark_layout.addWidget(qw.QLabel(f"Total items: {total_value_len}"))

        self.mark_widget.setLayout(new_mark_layout)

    def render_chart(self):
        d, t = self.rawdata[self.current_channel]
        self.ax_lines.clear()

        self.span = plt_w.SpanSelector(
            self.ax_lines, self.event__span_selection_event_listener,
            'horizontal', props=dict(facecolor='blue', alpha=0.5)
        )

        for label, min_val, max_val in self.marks.values():
            self.ax_lines.axvspan(min_val, max_val, facecolor='violet', alpha=0.2)

        for idx, onset in enumerate(self.rawdata.annotations.onset):
            description = self.rawdata.annotations.description[idx]

            if not description.startswith('BAD_'):
                continue

            duration = self.rawdata.annotations.duration[idx]
            self.ax_lines.axvspan(onset, onset + duration, facecolor='red', alpha=0.1)

        self.ax_lines.plot(t, d[0])

        self.render_selection()
        self.render_wavelet_chart()

        self.canvas.draw()

    def render_selection(self):
        if self.current_selection_span:
            self.current_selection_span.remove()
            self.current_selection_span = None

        if self.xmin == 0 and self.xmax == 0:
            return

        self.current_selection_span = self.ax_lines.axvspan(self.xmin, self.xmax, facecolor='red', alpha=0.3, edgecolor="green")

    def render_wavelet_chart(self):
        self.ax_wavelet.clear()
        self.ax_psd.clear()

        if not self.current_selection_span:
            return

        d = self.rawdata.copy().pick(
            picks=[self.current_channel]
        ).crop(tmin=self.xmin, tmax=self.xmax)

        e = mne.make_fixed_length_epochs(d, duration=self.xmax - self.xmin, preload=True, reject_by_annotation=True)

        if len(e) == 0:
            log_w('selected range cant contain bad channels')
            msg_error('Failed to build epochs from selection')
            return

        frequencies = np.arange(self.freq_min, self.freq_max, self.freq_step)
        n_cycles = self.n_cycles

        try:
            power = mne.time_frequency.tfr_morlet(
                e, n_cycles=n_cycles,
                return_itc=False, freqs=frequencies,
                average = True
            )
            colorbar = self.ax_wavelet__CB
            if colorbar is None:
                colorbar = True
            power.plot([self.current_channel], axes=self.ax_wavelet, cmap=('nipy_spectral', True), colorbar=colorbar, show=False)
            self.ax_wavelet__CB = self.ax_wavelet.CB
        except ValueError as e:
            msg_warning(str(e))
            log_w('ValueError: {0}', str(e))
            pass

        psd = d.compute_psd()

        psd.plot(axes=self.ax_psd, dB=False, amplitude=True, show=False)

    def set_selection_span(self, xmin, xmax):
        if self.xmin > self.xmax:
            self.xmin, self.xmax = xmax, xmin
        else:
            self.xmin, self.xmax = xmin, xmax

        duration = self.xmax - self.xmin
        log_i('selected duration [in seconds: {0}]', duration)

        if duration < 0.1:
            log_w('duration is really small [{0}], removed', duration)
            self.xmin, self.xmax, duration = 0, 0, 0

        if duration != 0 and duration < MIN_ALLOWED_DURATION_IN_SECONDS:
            msg_warning(f'selected duration [{duration}] is to small')
            self.xmin, self.xmax = 0, 0

        self.render_selection()
        self.render_wavelet_chart()

        self.canvas.draw()

    @try_catch_btn
    def event__span_selection_event_listener(self, xmin, xmax, *args, **kwags):
        self.set_selection_span(xmin, xmax)

    @try_catch_btn
    def event__add_mark(self, *args, **kwags):
        if self.xmin == 0 and self.xmax == 0:
            log_w('interval is not specified')
            msg_warning('Span is not selectd')
            return

        if len(self.new_mark_name) == 0:
            log_w('mark label is zero length')
            msg_warning('Mark label is empty')
            return

        self.marks[self.new_mark_name] = (self.new_mark_name, self.xmin, self.xmax)

        self.ax_lines.axvspan(self.xmin, self.xmax, facecolor='green', alpha=0.1, edgecolor="green", label=self.new_mark_name)

        self.render_marks()
        self.xmin, self.xmax = 0, 0
        self.current_selection_span.remove()
        self.current_selection_span = None

        self.canvas.draw()

    @try_catch_btn
    def event__mark_next_page(self, *args, **kwags):
        self.current_marks_page += 1
        self.render_marks()

    @try_catch_btn
    def event__mark_prev_page(self, *args, **kwags):
        self.current_marks_page -= 1
        self.render_marks()

    @try_catch_btn
    def event__remove_mark(self, label, *args, **kwags):
        del self.marks[label]

        self.render_marks()
        self.render_chart()

    @try_catch_btn
    def event__show_mark(self, label, *args, **kwags):
        assert label in self.marks, f'Label for mark [{label}] nor found'

        mark_label, min_val, max_val = self.marks[label]
        self.set_selection_span(min_val, max_val)
        self.new_mark_name = mark_label

    def event__on_key_press(self, event, *args, **kwags):
        mpl_key_press_handler(event, self.canvas, self.toolbox)




if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication

    init_application()

    abs_filename = PARSED_ARGS['file']

    assert abs_filename is not None, '--file argument has to be specified'

    app = QApplication(sys.argv)
    s = SettingState()
    s.load_from_json()

    rawdata = read_mne_rawdata(abs_filename)

    w = WaveletWindow(s, rawdata, None)

    app_run_main_window(app, w)
