import os

from PyQt6 import (
    QtWidgets as qw,
    QtGui as qg,
    QtCore as qc
)

from ratat_utils import *
from ratat_widgets import *

class SettingsWindow(qw.QMainWindow):
    def __init__(self, settings, on_close):
        super(SettingsWindow, self).__init__()

        self.Settings = settings
        self.on_close = on_close

        self.init_window()

        self.init_elements()

    def init_window(self):
        self.setWindowTitle('MNE Toolbox // Settings')
        self.resize(350, 400)
        self.setWindowIcon(RatatIcon())

    def init_elements(self):
        main_layout = MainLayout()

        # tabs

        tabs = qw.QTabWidget(self)
        main_layout.addWidget(tabs, 1)

        filter_tab = qw.QWidget()
        filter_tab.setLayout(TabLayout())
        tabs.addTab(filter_tab, 'Filter')

        wavelet_tab = qw.QWidget()
        wavelet_tab.setLayout(TabLayout())
        tabs.addTab(wavelet_tab, 'Wavelet')

        self.inputs = dict(
            # filter
            min_freq_input = add_top_labeled_entry(filter_tab.layout(), "Min filter freq", 0.5),
            max_freq_input = add_top_labeled_entry(filter_tab.layout(), "Max filter freq", 40.0),
            plot_scalings_input = add_top_labeled_entry(filter_tab.layout(), "Plot scaling", 2e-3),

            # wavelets
            wl_freq_min = add_top_labeled_entry(wavelet_tab.layout(), "Frequency min", 1),
            wl_freq_max = add_top_labeled_entry(wavelet_tab.layout(), "Frequency max", 15),
            wl_freq_step = add_top_labeled_entry(wavelet_tab.layout(), "Frequency step", 0.25),
            wl_n_cycles = add_top_labeled_entry(wavelet_tab.layout(), "n_cycles", 8),
        )

        filter_tab.layout().addStretch()
        wavelet_tab.layout().addStretch()

        for key, widget in self.inputs.items():
            val = getattr(self.Settings, key, None)
            if val:
                widget.setText(str(val))

        # buttons

        with BtnLayout(False) as btn_layout:
            btn_layout.add('Close', self.event__close)
            btn_layout.add('Save', self.event__save)
            main_layout.addLayout(btn_layout)

        self.setCentralWidget(main_layout.get_widget())

    @try_catch_btn
    def event__close(self, *args, **kwargs):
        self.close()

        if callable(self.on_close):
            self.on_close()

    @try_catch_btn
    def event__save(self, *args, **kwargs):
        values = {
            k: w.text()
            for k, w in self.inputs.items()
        }

        self.Settings.set_from_string_dict(values)
        self.Settings.save_to_json()

        self.close()

        if callable(self.on_close):
            self.on_close()


if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication

    init_application()

    app = QApplication(sys.argv)
    s = SettingState()
    s.load_from_json()
    w = SettingsWindow(s, None)
    app_run_main_window(app, w)
