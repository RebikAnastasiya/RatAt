import os

from PyQt6 import (
    QtWidgets as qw,
    QtGui as qg,
    QtCore as qc
)
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.backends.backend_qtagg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.backend_bases import key_press_handler as mpl_key_press_handler

from ratat_utils import *
from ratat_widgets import *

class BadEditorWindow(qw.QMainWindow):
    def __init__(self, settings, rawdata, on_close):
        super(BadEditorWindow, self).__init__()

        self.Settings = settings
        self.rawdata = rawdata
        self.on_close = on_close

        self.init_window()

        self.init_elements()

    def closeEvent(self, event):
        # NOTE: this is hack
        plt.close()


    def init_window(self):
        self.setWindowTitle('MNE Toolbox // Bad editor')
        self.showMaximized()
        # self.resize(350, 400)
        self.setWindowIcon(RatatIcon())

    def init_elements(self):
        main_layout = MainLayout()

        figure = self.rawdata.plot(scalings=self.Settings.plot_scalings_input, show=False)

        self.canvas = FigureCanvasQTAgg(figure)
        self.canvas.mpl_connect('key_press_event', self.on_key_press)
        self.canvas.setFocusPolicy(qc.Qt.FocusPolicy.StrongFocus)

        with BtnLayout(None) as btn_layout:
            toolbox = NavigationToolbar(self.canvas, self)
            self.toolbox = toolbox
            btn_layout.addWidget(toolbox)

            btn_layout.add('Cancel', self.event__close)
            btn_layout.add('Save BADs as filtered', self.event__save)
            main_layout.addLayout(btn_layout)

        main_layout.addWidget(self.canvas)

        self.setCentralWidget(main_layout.get_widget())

    def on_key_press(self, event):
        mpl_key_press_handler(event, self.canvas, self.toolbox)


    @try_catch_btn
    def event__close(self, *args, **kwargs):
        self.close()

        if callable(self.on_close):
            self.on_close(False)


    @try_catch_btn
    def event__save(self, *args, **kwargs):
        self.close()

        if callable(self.on_close):
            self.on_close(True)


# TODO: add main init
