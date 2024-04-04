import os, json, logging, collections, argparse
import mne
import matplotlib as mpl, matplotlib.pyplot as plt

from PyQt6 import (
    QtWidgets as qw,
    QtGui as qg,
    QtCore as qc
)

# globals
PARSED_ARGS = dict()

####################################################################################################
# log
####################################################################################################


def init_application():
    parser = argparse.ArgumentParser(description='mne Toolbox')
    parser.add_argument('-d', '--dir', help='directory to open automatically', required=False, default=None)
    parser.add_argument('-f', '--file', help='specific file to open', required=False, default=None)
    parser.add_argument('-l', '--log', help='log level', required=False, default='info')
    args = vars(parser.parse_args())

    for k, v in args.items():
        PARSED_ARGS[k] = v

    # NOTE: dir has more priority over file
    if PARSED_ARGS['file'] is not None and PARSED_ARGS['dir'] is not None:
        PARSED_ARGS['file'] = None

    str_to_log_level_map = dict(
        info = logging.INFO,
        debug = logging.DEBUG,
        warning = logging.WARNING,
        error = logging.ERROR,
    )
    log_level = str_to_log_level_map.get(PARSED_ARGS['log'].lower(), logging.INFO)

    configure_logging(log_level)

    log_i('configured logging level {0}', log_level)

    # configure plotting
    plt_backend = 'Qt5Agg'
    plt.style.use('seaborn-v0_8-notebook')
    mpl.rcParams["backend"] = plt_backend

    log_i('starting loading libraries...')


ratat_logger = None


def configure_logging(level):
    global ratat_logger
    FORMAT = '[{levelname:<8}] {asctime} // {message}'
    logging.basicConfig(format=FORMAT, level=level, style='{')
    logging.setLogRecordFactory(StrFormatLogRecord)
    ratat_logger = logging.getLogger('APP')

def log_i(msg, *args, **kwargs):
    ratat_logger.info(msg, *args, **kwargs)

def log_d(msg, *args, **kwargs):
    ratat_logger.debug(msg, *args, **kwargs)

def log_w(msg, *args, **kwargs):
    ratat_logger.warning(msg, *args, **kwargs)

def log_e(msg, *args, **kwargs):
    ratat_logger.error(msg, *args, **kwargs)

class StrFormatLogRecord(logging.LogRecord):
    """
    Drop-in replacement for ``LogRecord`` that supports ``str.format``.
    """

    def getMessage(self):
        msg = str(self.msg)
        if self.args:
            try:
                msg = msg % ()
            except TypeError:
                # Either or the two is expected indicating there's
                # a placeholder to interpolate:
                #
                # - not all arguments converted during string formatting
                # - format requires a mapping" expected
                #
                # If would've been easier if Python printf-style behaved
                # consistently for "'' % (1,)" and "'' % {'foo': 1}". But
                # it raises TypeError only for the former case.
                msg = msg % self.args
            else:
                # There's special case of first mapping argument. See
                # duner init of logging.LogRecord.
                if isinstance(self.args, collections.abc.Mapping):
                    msg = msg.format(**self.args)
                else:
                    msg = msg.format(*self.args)

        return msg

####################################################################################################
# settings
####################################################################################################


config_file_path = 'config.json'


class SettingState:
    def __init__(self):
        self.default = dict(
            min_freq_input = 0.6,
            max_freq_input = 40.0,
            plot_scalings_input = 2e-3,
            wl_freq_min = 1,
            wl_freq_max = 15,
            wl_freq_step = 0.25,
            wl_n_cycles = 8
        )

        for key, value in self.default.items():
            setattr(self, key, value)

    def set_from_string_dict(self, values):
        for key, default_value in self.default.items():
            new_value = values.get(key, None)

            if new_value is None:
                continue

            val = None
            if type(default_value) is int:
                val = int(new_value)
            elif type(default_value) is float:
                val = float(new_value)

            if val is None:
                continue

            setattr(self, key, val)


    def load_from_json(self):
        if not os.path.exists(config_file_path):
            return

        with open(config_file_path, 'r') as config_file:
            data = json.load(config_file)
            for key, value in data.items():
                setattr(self, key, value)

    def save_to_json(self):
        data = dict()
        for key, value in self.default.items():
            data[key] = getattr(self, key)

        with open(config_file_path, 'w') as fp:
            json.dump(data, fp)


def get_step_filename(abs_filename, directory, suffix=None, override_ext=None):
    head, tail = os.path.split(abs_filename)

    if directory is not None:
        resultDir = os.path.join(head, directory)
    else:
        resultDir = head

    if not os.path.exists(resultDir):
        os.mkdir(resultDir)

    file_parts = tail.split('.')
    ext = file_parts[-1]
    if override_ext:
        ext = override_ext

    filename_without_ext = '.'.join(file_parts[:-1])
    if suffix:
        filename_without_ext += suffix

    result = os.path.join(resultDir, filename_without_ext + '.' + ext)
    return result

####################################################################################################
# mne
####################################################################################################

def read_mne_rawdata(fullname):
    if fullname.endswith('.bdf'):
        rawdata = mne.io.read_raw_bdf(fullname, preload=True)
    elif fullname.endswith('.edf'):
        rawdata = mne.io.read_raw_edf(fullname, preload=True)
    else:
        raise Exception(f'Failed to parse file extension from file [{fullname}]. Allowed extensions [edf, bdf]')

    return rawdata


####################################################################################################
# UI
####################################################################################################

def bind_property(objectName, propertyName):
    def getter(self):
        return self.findChild(qc.QObject, objectName).property(propertyName)

    def setter(self, value):
        self.findChild(qc.QObject, objectName).setProperty(propertyName, value)

    return property(getter, setter)

ExceptionWindow = None
def set_exception_window(window):
    global ExceptionWindow
    ExceptionWindow = window

def set_window_default_icon(window):
    current_file_dir = os.path.dirname(os.path.abspath(__file__))
    window.iconbitmap(os.path.join(current_file_dir, "imgs/icon.ico"))

def execute_destroy(obj):
    if obj is None:
        return

    destroy_fn = getattr(obj, 'destroy', None)
    if callable(destroy_fn):
        destroy_fn()

def add_top_labeled_entry(widget, label, default_value):
    layout = qw.QVBoxLayout()
    layout.setContentsMargins(0,0,0,0)
    layout.setSpacing(0)

    label = qw.QLabel(label)
    layout.addWidget(label)

    entry = qw.QLineEdit()
    layout.addWidget(entry)
    entry.setText(str(default_value))

    layout.addStretch()

    widget.addLayout(layout)

    return entry

def msg_success(message, title='Done'):
    qw.QMessageBox.information(
        ExceptionWindow,
        title,
        message,
        buttons = qw.QMessageBox.StandardButton.Ok,
        defaultButton = qw.QMessageBox.StandardButton.Ok,
    )

def msg_warning(message, title='Warning'):
    qw.QMessageBox.warning(
        ExceptionWindow,
        title,
        message,
        buttons = qw.QMessageBox.StandardButton.Ok,
        defaultButton = qw.QMessageBox.StandardButton.Ok,
    )

def msg_error(text):
    qw.QMessageBox.critical(
        ExceptionWindow,
        "Error!",
        text,
        buttons = qw.QMessageBox.StandardButton.Ok,
        defaultButton = qw.QMessageBox.StandardButton.Ok,
    )

def app_run_main_window(app, mainWindow):
    set_exception_window(mainWindow)

    log_i('starting application')
    with open('style.css') as f:
        mainWindow.setStyleSheet(f.read())

    mainWindow.show()
    app.exec()
