from PyQt4.QtGui import QWidget, QGridLayout, QGroupBox, QDoubleSpinBox, QValidator, QSpinBox, QHBoxLayout, QLabel, \
    QVBoxLayout, QPushButton, QApplication, QLineEdit, QFileDialog
import numpy as np


class Labelled(QWidget):
    def __init__(self, name, widget, parent=None):
        super(Labelled, self).__init__(parent)
        layout = QHBoxLayout(self)
        layout.addWidget(QLabel(name))
        layout.addWidget(widget)

class SciDoubleSpinBox(QDoubleSpinBox):
    def __init__(self, init=None, min=None, max=None, step=None, parent=None):
        super(SciDoubleSpinBox, self).__init__(parent)
        self.setRange(-1e100, 1e100)
        if min is not None:
            self.setMinimum(min)
        if max is not None:
            self.setMaximum(max)
        if step is not None:
            self.setSingleStep(step)
        if init is not None:
            self.setValue(init)

    def validate(self, s, pos):
        s = str(s)
        try:
            float(s)
            return QValidator.Acceptable, pos
        except ValueError:
            if s.startswith('-'):
                s.replace('-', '', 1)
            if s.lower().replace('e', '', 1).isdigit():
                return QValidator.Intermediate, pos
            return QValidator.Invalid, pos

    def textFromValue(self, val):
        return '{:g}'.format(val)

    def valueFromText(self, s):
        return float(s)

class ArrayWidget(QGroupBox):
    def __init__(self, name=None, start=0, stop=10, step=1, min=None, max=None, max_steps=None, parent=None):
        super(ArrayWidget, self).__init__(name, parent)
        layout = QGridLayout(self)
        self.start_widget = SciDoubleSpinBox(start, min, max)
        self.stop_widget = SciDoubleSpinBox(stop, min, max)
        self.step_widget = SciDoubleSpinBox(step)
        self.count_widget = QSpinBox()
        self.count_widget.setMinimum(2)
        if max_steps is not None:
            self.count_widget.setMaximum(max_steps)
        layout.addWidget(Labelled("Start", self.start_widget), 0, 0)
        layout.addWidget(Labelled("Stop", self.stop_widget), 0, 1)
        layout.addWidget(Labelled("Step", self.step_widget), 1, 0)
        layout.addWidget(Labelled("Count", self.count_widget), 1, 1)

        self.step_widget.editingFinished.connect(self.set_count_from_step)
        self.start_widget.editingFinished.connect(self.set_step_from_count)
        self.stop_widget.editingFinished.connect(self.set_step_from_count)
        self.count_widget.editingFinished.connect(self.set_step_from_count)

    def set_count_from_step(self):
        start = self.start_widget.value()
        stop = self.stop_widget.value()
        step = self.step_widget.value()
        if step == 0:
            return
        count = int((stop - start) / step) + 1
        self.count_widget.setValue(count)

    def set_step_from_count(self):
        start = self.start_widget.value()
        stop = self.stop_widget.value()
        count = self.count_widget.value()
        step = (stop - start) / (count - 1)
        self.step_widget.setValue(step)

    def get_array(self):
        start = self.start_widget.value()
        stop = self.stop_widget.value()
        step = self.step_widget.value()
        return np.arange(start, stop, step)

class FileWidget(QWidget):
    def __init__(self, path="", parent=None):
        super(FileWidget, self).__init__(parent)
        layout = QHBoxLayout(self)
        browse_button = QPushButton("File Path")
        self.line_edit = QLineEdit(path)
        layout.addWidget(browse_button)
        layout.addWidget(self.line_edit)
        browse_button.clicked.connect(self.set_path)

    def set_path(self):
        self.line_edit.setText(QFileDialog.getSaveFileName())

    def get_path(self):
        return self.line_edit.text()

class H5FileWidget(QWidget):
    def __init__(self, path="", parent=None):
        super(FileWidget, self).__init__(parent)
        layout = QVBoxLayout(self)
        self.file_widget = FileWidget(path)
        dataset_button = QPushButton("Dataset")
        self.line_edit = QLineEdit(path)
        layout.addWidget(dataset_button)
        layout.addWidget(self.line_edit)
        dataset_button.clicked.connect(self.set_dataset)

    def set_dataset(self):
        self.line_edit.setText(QFileDialog.getSaveFileName())

    def get_path(self):
        return self.line_edit.text()

if __name__ == '__main__':
    app = QApplication([])
    w = QWidget()
    l = QVBoxLayout(w)
    aw = ArrayWidget('Test Array', 0, 100, 5, 1e-5, 1e9)
    b = QPushButton("Get Array")
    def print_array():
        print aw.get_array()
    b.clicked.connect(print_array)
    l.addWidget(aw)
    l.addWidget(b)
    w.show()
    app.exec_()




