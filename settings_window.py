from PyQt4.QtCore import QObject, pyqtSignal, QThread, Qt
from PyQt4.QtGui import QApplication, QMainWindow
import sys


def run(widget_class, settings=None, ui_version=1, **kwargs):
    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    if settings is not None:
        window = SettingsWindow(settings, ui_version)
        window.setCentralWidget(widget_class(**kwargs))
        window.setWindowTitle(window.centralWidget().windowTitle())
        window.restore_from_settings()

    else:
        window = widget_class(**kwargs)

    window.show()
    app.setQuitOnLastWindowClosed(True)
    sys.exit(app.exec_())

class SettingsWindow(QMainWindow):
    def __init__(self, settings, ui_version):
        super(SettingsWindow, self).__init__()
        self.settings = settings
        self.ui_version = ui_version

    def restore_from_settings(self):
        self.restoreGeometry(self.settings.value("geometry").toByteArray())
        self.restoreState(self.settings.value("state").toByteArray(), self.ui_version)

    def closeEvent(self, ev):
        if self.settings is not None:
            self.settings.setValue("geometry", self.saveGeometry())
            self.settings.setValue("state", self.saveState(self.ui_version))

        widget = self.centralWidget()
        del widget
        return super(SettingsWindow, self).closeEvent(ev)

class Worker(QObject):
    finished = pyqtSignal(name="finished")
    def __init__(self, *args):
        super(Worker, self).__init__()
        self.args = args

    def start(self):
        self.output = self.process(*self.args)
        self.finished.emit()

def run_in_thread(fn, args):
    worker = Worker(*args)
    worker.process = fn
    thread = QThread()
    worker.moveToThread(thread)
    app = QApplication.instance()
    app.connect(thread, Qt.SIGNAL('started()'), worker.start)
    app.connect(worker, Qt.SIGNAL('finished()'), thread.quit)
    app.connect(worker, Qt.SIGNAL('finished()'), thread.deleteLater)
    return worker, thread
