import os, traceback

from PyQt6 import (
    QtWidgets as qw,
    QtGui as qg,
    QtCore as qc
)

from ratat_utils import *

def try_catch_btn(func):
    def inner(self, *args, **kwargs):
        log_i('{0}, {1}, {2}', self, args, kwargs)
        try:
            func(self, *args, **kwargs)
        except Exception as e:
            log_e(traceback.format_exc())
            msg_error(str(e))

    return inner

class RatatIcon(qg.QIcon):
    def __init__(self):
        super(RatatIcon, self).__init__()
        current_file_dir = os.path.dirname(os.path.abspath(__file__))
        for s in [16, 24, 32, 48, 256]:
            icon_path = os.path.join(current_file_dir, f"imgs/icon_{s}.png")
            self.addFile(icon_path, qc.QSize(s, s))

class MainLayout(qw.QVBoxLayout):
    def __init__(self):
        super(MainLayout, self).__init__()
        self.setContentsMargins(5, 0, 5, 0)
        self.setSpacing(0)

    def get_widget(self):
        widget = qw.QWidget()
        widget.setLayout(self)
        return widget


class TabLayout(qw.QVBoxLayout):
    def __init__(self):
        super(TabLayout, self).__init__()
        self.setSpacing(0)
        self.setContentsMargins(20,10,20,0)


class ToolboxHeader(qw.QLabel):
    def __init__(self, label):
        super(ToolboxHeader, self).__init__(label)
        self.setStyleSheet('font-size: 14px')
        self.setContentsMargins(0, 20, 0, 10)


class BtnLayout(qw.QHBoxLayout):
    def __init__(self, is_right_spacer=False):
        super(BtnLayout, self).__init__()
        self.setContentsMargins(0,5,0,10)
        self.setSpacing(10)
        self.is_right_spacer = is_right_spacer

    def add(self, title, command):
        btn = qw.QPushButton(title)
        if callable(command):
            btn.clicked.connect(command)
        self.addWidget(btn)
        return btn

    def add_tool(self, title, command, parent):
        btn = qw.QToolButton(parent=parent)
        btn.setText(title)
        if callable(command):
            btn.clicked.connect(command)
        self.addWidget(btn)
        return btn

    def __enter__(self):
        if self.is_right_spacer is not None and not self.is_right_spacer:
            self.addStretch()
        return self

    def __exit__(self, type, value, traceback):
        if self.is_right_spacer is not None and self.is_right_spacer:
            self.addStretch()



def combobox_accessor(name):
    def getter(self):
        child = self.findChild(qc.QObject, name)
        if child is not None:
            val = child.property('currentText')
        else:
            val = None
        return val

    return property(getter)

def checkbox_accessor(name):
    def getter(self):
        child = self.findChild(qc.QObject, name)
        if child is not None:
            val = child.property('checked')
        else:
            val = None
        return val

    return property(getter)

def lineedit_accessor(name):
    def getter(self):
        child = self.findChild(qc.QObject, name)
        if child is not None:
            val = child.property('text')
        else:
            val = None
        return val

    def setter(self, value):
        child = self.findChild(qc.QObject, name)
        if child is not None:
            child.setText(value)

    return property(getter, setter)
