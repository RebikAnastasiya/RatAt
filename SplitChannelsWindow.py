import os

from PyQt6 import (
    QtWidgets as qw,
    QtGui as qg,
    QtCore as qc
)

from ratat_utils import *
from ratat_widgets import *


class SplitChannelsWindow(qw.QMainWindow):

    left_file_suffix = lineedit_accessor('LeftPartialName')
    right_file_suffix = lineedit_accessor('RightPartialName')

    def __init__(self, settings, main_filename, rawdata, on_close):
        super(SplitChannelsWindow, self).__init__()

        self.Settings = settings
        self.MainFilename = main_filename
        self.rawdata = rawdata
        self.on_close = on_close

        self.init_window()
        self.init_elements()

    def init_window(self):
        self.setWindowTitle('MNE Toolbox // Split')
        self.resize(450, 400)
        self.setWindowIcon(RatatIcon())

    def init_elements(self):
        main_layout = MainLayout()

        with BtnLayout(True) as blt:
            blt.add('Save split files', self.event__save_split_files)
            blt.add('Split left even', self.event__split_left_even)

            blt.add('Close', self.event__close)
            main_layout.addLayout(blt)

        panes = qw.QHBoxLayout()
        main_layout.addLayout(panes)

        left_pane = qw.QVBoxLayout()
        panes.addLayout(left_pane, 6)

        centeral_pane = qw.QVBoxLayout()
        centeral_pane.setContentsMargins(15, 0, 15, 0)
        panes.addLayout(centeral_pane, 1)

        right_pane = qw.QVBoxLayout()
        panes.addLayout(right_pane, 6)

        w = qw.QPushButton('>')
        w.clicked.connect(self.event__move_channels_right)
        centeral_pane.addWidget(w)

        w = qw.QPushButton('<')
        w.clicked.connect(self.event__move_channels_left)
        centeral_pane.addWidget(w)

        centeral_pane.addStretch()

        w = qw.QLineEdit(self)
        w.setObjectName('LeftPartialName')
        w.setText('_1')
        left_pane.addWidget(w)

        w = qw.QLineEdit(self)
        w.setObjectName('RightPartialName')
        w.setText('_2')
        right_pane.addWidget(w)

        w = qw.QListWidget(self)
        w.setObjectName('LeftChannels')
        w.addItems(self.rawdata.ch_names)
        w.setSelectionMode(qw.QAbstractItemView.SelectionMode.MultiSelection)
        left_pane.addWidget(w)

        w = qw.QListWidget(self)
        w.setObjectName('RightChannels')
        w.setSelectionMode(qw.QAbstractItemView.SelectionMode.MultiSelection)
        right_pane.addWidget(w)

        self.setCentralWidget(main_layout.get_widget())

    def get_pane_channels(self, child, only_selected):
        if only_selected:
            items = child.selectedItems()
        else:
            items = []
            for x in range(child.count()):
                items.append(child.item(x))

        ch_names = [c.text() for c in items]
        return ch_names

    def get_left_channels(self, only_selected=False):
        child = self.findChild(qc.QObject, 'LeftChannels')
        assert child is not None, 'left channel tab is none'
        return self.get_pane_channels(child, only_selected)

    def get_right_channels(self, only_selected=False):
        child = self.findChild(qc.QObject, 'RightChannels')
        assert child is not None, 'right channel tab is none'
        return self.get_pane_channels(child, only_selected)


    def set_right_channels(self, new_items):
        child = self.findChild(qc.QObject, 'RightChannels')
        assert child is not None, 'right channel tab is none'
        child.clear()
        child.addItems(new_items)

    def set_left_channels(self, new_items):
        child = self.findChild(qc.QObject, 'LeftChannels')
        assert child is not None, 'left channel tab is none'
        child.clear()
        child.addItems(new_items)

    def event__split_left_even(self):
        full_left_channels = self.get_left_channels()
        right_channels = self.get_right_channels()

        left_channels = full_left_channels[:len(full_left_channels) // 2]
        right_channels = right_channels + full_left_channels[len(full_left_channels) // 2:]

        self.set_left_channels(left_channels)
        self.set_right_channels(right_channels)

    def event__close(self):
        self.close()

    def event__save_split_files(self):
        left_channels = self.get_left_channels()
        right_channels = self.get_right_channels()

        left_filename = get_step_filename(self.MainFilename, None, self.left_file_suffix, 'edf')
        right_filename = get_step_filename(self.MainFilename, None, self.right_file_suffix, 'edf')

        assert left_filename != right_filename, f'File names cant be equal [{left_filename}] and [{right_filename}]'

        rawdata_left = self.rawdata.copy().drop_channels(left_channels)
        rawdata_right = self.rawdata.copy().drop_channels(right_channels)

        mne.export.export_raw(left_filename, rawdata_left, overwrite=True)
        mne.export.export_raw(right_filename, rawdata_right, overwrite=True)

        log_i('\tcreated files\n\t  {0}\n\t  {1}', left_filename, right_filename)

        msg_success('Done', 'Split is done')

    def event__move_channels_right(self):
        selected_left_channels = self.get_left_channels(True)
        right_channels = self.get_right_channels() + selected_left_channels
        left_channels = list(set(self.get_left_channels()) - set(selected_left_channels))

        self.set_left_channels(left_channels)
        self.set_right_channels(right_channels)

    def event__move_channels_left(self):
        selected_right_channels = self.get_right_channels(True)
        left_channels = self.get_left_channels() + selected_right_channels
        right_channels = list(set(self.get_right_channels()) - set(selected_right_channels))

        self.set_left_channels(left_channels)
        self.set_right_channels(right_channels)


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

    w = SplitChannelsWindow(s, abs_filename, rawdata, None)
    app_run_main_window(app, w)
