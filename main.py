from ratat_utils import *

init_application()

import sys
from PyQt6.QtWidgets import QApplication

from MainWindow import MainWindow


if os.name == 'nt':
    import ctypes
    myappid = 'mycompany.myproduct.subproduct.version' # arbitrary string
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

def main():
    '''main application loop'''

    app = QApplication(sys.argv)
    window = MainWindow(
        default_dir = PARSED_ARGS['dir']
    )

    app_run_main_window(app, window)

def create_icons():
    '''create icons from 256x256 for application'''
    from PIL import Image

    icon_file = 'imgs/icon_256.png'
    img = Image.open(icon_file)
    for s in [16, 24, 32, 48]:
        new_img = img.resize((s, s))
        new_img.save(f"imgs/icon_{s}.png")


if __name__ == '__main__':
    main()
    # create_icons()
