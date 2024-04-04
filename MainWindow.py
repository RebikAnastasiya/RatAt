import os

from PyQt6.QtWidgets import (
    QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QStackedLayout,
    QFileDialog,
    QPushButton, QLabel, QMenu,
    QTreeView, QAbstractItemView
)
from PyQt6 import QtGui, QtCore

import mne
import pandas as pd
import numpy as np

from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

from matplotlib import pyplot as plt, widgets as pltw
import matplotlib as mpl

from ratat_utils import *
from ratat_widgets import *
import ratat_fooof as rfooof

from SettingsWindow import SettingsWindow
from BadEditorWindow import BadEditorWindow
from PowerDensityWindow import PowerDensityWindow
from WaveletWindow import WaveletWindow
from SplitChannelsWindow import SplitChannelsWindow

class MainWindow(QMainWindow):
    def __init__(self, default_dir=None):
        super(MainWindow, self).__init__()

        self.Settings = SettingState()
        self.Settings.load_from_json()

        self.current_window = None

        self.init_window()

        # self.start_debug_css_update()

        self.init_elements()

        if default_dir is not None:
            for fpath in os.listdir(default_dir):
                self.add_tree_view_file(os.path.join(default_dir, fpath))

    def init_window(self):
        self.setWindowTitle("MNE Toolbox")
        self.resize(700, 400)
        self.setWindowIcon(RatatIcon())

    def set_style_sheet(self):
        log_i('update css ...')
        with open('style.css') as f:
            style = f.read()
            self.setStyleSheet(style)
            if self.current_window:
                self.current_window.setStyleSheet(style)


    def start_debug_css_update(self):
        self.checkThreadTimer = QtCore.QTimer(self)
        self.checkThreadTimer.setInterval(1000) #.5 seconds
        self.checkThreadTimer.timeout.connect(self.set_style_sheet)
        self.checkThreadTimer.start()

    def init_elements(self):
        main_layout = MainLayout()

        with BtnLayout(True) as btn_layout:
            btn_layout.add('Load files', self.event__open_load_files_dialog)
            btn_layout.add('Settings', self.event__open_settings)
            main_layout.addLayout(btn_layout)

        self.init_tree_view(main_layout)

        main_layout.addStretch()

        self.setCentralWidget(main_layout.get_widget())

    def init_tree_view(self, main_layout):
        self.btns_for_table_rows = []
        self.btns_for_only_filtered = []

        main_layout.addWidget(QLabel('EDF files'))

        with BtnLayout(True) as btn_layout:
            main_layout.addLayout(btn_layout)

            btn_layout.add('Filter and place BADs', self.event__filter_and_place_bads)

            # tools buttons

            btn = btn_layout.add('Tools', None)
            btn.setObjectName('DropdownButton')
            dropdown_menu = QMenu(parent=self)
            dropdown_menu.aboutToHide.connect(lambda: btn.repaint())

            action = QtGui.QAction('View filtered data', parent=self)
            action.setIconVisibleInMenu(False)
            action.triggered.connect(self.event__view_filtered_data)
            dropdown_menu.addAction(action)

            action = QtGui.QAction('Power Density Specra (PSD)', parent=self)
            action.setIconVisibleInMenu(False)
            action.triggered.connect(self.event__psd)
            dropdown_menu.addAction(action)

            action = QtGui.QAction('Wavelet', parent=self)
            action.setIconVisibleInMenu(False)
            action.triggered.connect(self.event__wavelet)
            dropdown_menu.addAction(action)

            btn.setMenu(dropdown_menu)
            btn.setCheckable(True)

            # reports

            btn = btn_layout.add('Report', None)
            btn.setObjectName('DropdownButton')
            dropdown_menu = QMenu(parent=self)

            action = QtGui.QAction('FOOOF', parent=self)
            action.setIconVisibleInMenu(False)
            action.triggered.connect(self.event__fooof)
            dropdown_menu.addAction(action)

            btn.setMenu(dropdown_menu)

            # edits

            btn = btn_layout.add('Edit', None)
            btn.setObjectName('DropdownButton')
            dropdown_menu = QMenu(parent=self)

            action = QtGui.QAction('Split files for TWO rats', parent=self)
            action.setIconVisibleInMenu(False)
            action.triggered.connect(self.event__split_files_for_two_rats)
            dropdown_menu.addAction(action)

            btn.setMenu(dropdown_menu)

        # layout

        view = QTreeView()
        self.FileTreeView = view
        view.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        view.setUniformRowHeights(True)

        self.FileModel = QtGui.QStandardItemModel()
        self.FileModel.setHorizontalHeaderLabels(['Abs file', 'File', 'Filtered'])
        view.setModel(self.FileModel)

        view.setTreePosition(-1)
        view.setColumnHidden(0, True)

        header = view.header()

        header.setSectionResizeMode(1, qw.QHeaderView.ResizeMode.Stretch)
        header.setStretchLastSection(False)

        main_layout.addWidget(view, 1)

    def add_tree_view_file(self, abs_filename):
        if not any(abs_filename.endswith(ext) for ext in ['.bdf', '.edf']):
            return

        _, filename = os.path.split(abs_filename)

        filtered_file_name = self.get_edf_filtered_file_name(abs_filename)
        is_filtered = 1 if os.path.exists(filtered_file_name) else 0

        self.add_model_item(abs_filename, filename, is_filtered)

    def add_model_item(self, abs_filename, filename, is_filtered):
        child1 = QtGui.QStandardItem(filename)
        child1.setEditable(False)

        child2 = QtGui.QStandardItem('True' if is_filtered else 'False')
        child2.setEditable(False)

        child3 = QtGui.QStandardItem(abs_filename)
        child3.setEditable(False)

        self.FileModel.appendRow([child3, child1, child2])

    def clear_treeview(self):
        rowCount = self.FileModel.rowCount()
        if rowCount > 0:
            self.FileModel.removeRows(0, rowCount)

    def get_edf_filtered_file_name(self, filename):
        resultDirName = '01_filtered'
        head, tail = os.path.split(filename)
        resultDir = os.path.join(head, resultDirName)

        if not os.path.exists(resultDir):
            os.mkdir(resultDir)

        resultFileName = os.path.join(
            resultDir, tail.replace('.bdf', '__F.edf')
        )
        return resultFileName

    def get_current_items(self):
        selectedItems = []
        selectedIndexes = self.FileTreeView.selectedIndexes()

        if selectedIndexes:
            selected_rows = ({
                idx.row(): 1
                for idx in selectedIndexes
            }).keys()
            for row in selected_rows:
                selectedItems.append(
                    (row, self.FileModel.item(row, 0).text())
                )

        return selectedItems

    def get_current_fullname(self):
        result = (None, None)
        items = self.get_current_items()
        if items:
            result = items[0]

        return result

    def close_current_window(self):
        set_exception_window(self)
        if self.current_window is not None:
            self.current_window.close()
            self.current_window = None

    def show_current_window(self):
        if self.current_window is not None:
            set_exception_window(self.current_window)
            self.current_window.setStyleSheet(self.styleSheet())
            self.current_window.show()

    @try_catch_btn
    def event__open_load_files_dialog(self, *args, **kwargs):
        '''
        doc: https://doc.qt.io/qtforpython-5/PySide2/QtWidgets/QFileDialog.html#PySide2.QtWidgets.PySide2.QtWidgets.QFileDialog.getOpenFileName
        '''
        selected_files, current_filter = QFileDialog.getOpenFileNames(
            self,
            'Select bdf/edf files', # caption
            os.getcwd(), # dir
            "EDF/BDF (*.bdf *.edf)", # filter
        )

        self.clear_treeview()

        for abs_filename in selected_files:
            self.add_tree_view_file(abs_filename)

        self.FileTreeView.resizeColumnToContents(0)

    @try_catch_btn
    def event__open_settings(self, *args, **kwargs):
        self.current_window = SettingsWindow(self.Settings, None)
        self.current_window.setStyleSheet(self.styleSheet())
        self.current_window.show()

    @try_catch_btn
    def event__filter_and_place_bads(self, *args, **kwargs):
        row, fullname = self.get_current_fullname()
        assert fullname is not None, 'item not selected'

        log_i('\tfile name: {0}', fullname)

        rawdata = read_mne_rawdata(fullname)

        # TODO: move to settings: drop_channels_default: 'Accelerometer'
        channels_to_remove = ['Accelerometer']

        if len(channels_to_remove) > 0:
            log_i('\tremoving channels: {0}', ', '.join(channels_to_remove))
            rawdata.drop_channels(channels_to_remove, on_missing='ignore')

        rawdata = rawdata.filter(
            self.Settings.min_freq_input,
            self.Settings.max_freq_input,
            phase='zero'
        )

        self.current_window = BadEditorWindow(
            self.Settings,
            rawdata,
            lambda isOk: self.callback__save_filtered_with_bads(isOk, rawdata, row, fullname)
        )

        self.show_current_window()

    @try_catch_btn
    def callback__save_filtered_with_bads(self, isOk, rawdata, row, filename, *args, **kwargs):
        if isOk:
            filtered_file_name = self.get_edf_filtered_file_name(filename)
            log_i('saving data to file: %s', filtered_file_name)

            mne.export.export_raw(filtered_file_name, rawdata, overwrite=True)

            item = QtGui.QStandardItem('True')
            self.FileModel.setItem(row, 2, item)
        else:
            # NOTE: do nothing
            pass

        self.close_current_window()

    @try_catch_btn
    def event__view_filtered_data(self, *args, **kwargs):
        row, fullname = self.get_current_fullname()
        assert fullname is not None, 'item not selected'

        filtered_file_name = self.get_edf_filtered_file_name(fullname)
        rawdata = mne.io.read_raw_edf(filtered_file_name, preload=True)
        rawdata.plot(scalings=self.Settings.plot_scalings_input)
        plt.show()


    @try_catch_btn
    def event__psd(self, *args, **kwargs):
        self.close_current_window()

        row, fullname = self.get_current_fullname()

        filtered_file_name = self.get_edf_filtered_file_name(fullname)
        rawdata = mne.io.read_raw_edf(filtered_file_name, preload=True)

        self.current_window = PowerDensityWindow(
            self.Settings, fullname, rawdata, self.close_current_window
        )

        self.show_current_window()

    @try_catch_btn
    def event__wavelet(self, *args, **kwargs):
        self.close_current_window()

        row, fullname = self.get_current_fullname()

        filtered_file_name = self.get_edf_filtered_file_name(fullname)
        rawdata = mne.io.read_raw_edf(filtered_file_name, preload=True)

        self.current_window = WaveletWindow(
            self.Settings, rawdata, self.close_current_window
        )

        self.show_current_window()

    @try_catch_btn
    def event__fooof(self, *args, **kwargs):
        row, fullname = self.get_current_fullname()
        filtered_file_name = self.get_edf_filtered_file_name(fullname)
        
        rfooof.perorm_fooof_analysis_with_report(fullname, filtered_file_name)
        
        msg_success('FOOOF report is done')

    @try_catch_btn
    def event__split_files_for_two_rats(self, *args, **kwargs):
        self.close_current_window()

        row, fullname = self.get_current_fullname()

        rawdata = read_mne_rawdata(fullname)

        self.current_window = SplitChannelsWindow(
            self.Settings, fullname, rawdata, self.close_current_window
        )

        self.show_current_window()
