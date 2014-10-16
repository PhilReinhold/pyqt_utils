import os
import h5py
import sys
from dataserver import dataserver_helpers
from h5_widgets import H5File, H5View
from PyQt4.QtGui import QWidget, QGridLayout, QGroupBox, QDoubleSpinBox, QValidator, QSpinBox, QHBoxLayout, QLabel, \
    QVBoxLayout, QPushButton, QApplication, QLineEdit, QFileDialog, QDialog, QAbstractItemView, QDialogButtonBox, \
    QFormLayout, QSizePolicy
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
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)

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

class IntSpinBox(QSpinBox):
    def __init__(self, init=None, min=None, max=None, step=None, parent=None):
        super(IntSpinBox, self).__init__(parent)
        self.setRange(-sys.maxint, sys.maxint)
        if init is not None:
            self.setValue(init)
        if min is not None:
            self.setMinimum(min)
        if max is not None:
            self.setMaximum(max)
        if step is not None:
            self.setSizeIncrement(step)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)

class ArrayWidget(QGroupBox):
    def __init__(self, name=None, start=0, stop=10, step=1, min=None, max=None, max_steps=None, parent=None):
        super(ArrayWidget, self).__init__(name, parent)
        layout = QGridLayout(self)
        self.start_widget = SciDoubleSpinBox(start, min, max)
        self.stop_widget = SciDoubleSpinBox(stop, min, max)
        self.step_widget = SciDoubleSpinBox(step)
        self.count_widget = IntSpinBox(min=2, max=max_steps)
        layout.addWidget(Labelled("Start", self.start_widget), 0, 0)
        layout.addWidget(Labelled("Stop", self.stop_widget), 0, 1)
        layout.addWidget(Labelled("Step", self.step_widget), 1, 0)
        layout.addWidget(Labelled("Count", self.count_widget), 1, 1)

        self.step_widget.editingFinished.connect(self.set_count_from_step)
        self.start_widget.editingFinished.connect(self.set_step_from_count)
        self.stop_widget.editingFinished.connect(self.set_step_from_count)
        self.count_widget.editingFinished.connect(self.set_step_from_count)

        layout.setSpacing(0)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)

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

class FileWidget(QGroupBox):
    def __init__(self, path="", name="", parent=None, confirm_overwrite=False):
        super(FileWidget, self).__init__(name, parent)
        layout = QFormLayout(self)
        browse_button = QPushButton("File Path")
        self.filename_edit = QLineEdit(path)
        layout.addRow(browse_button, self.filename_edit)
        browse_button.clicked.connect(self.set_path)
        self.dialog_options = QFileDialog.Options()
        if not confirm_overwrite:
            self.dialog_options |= QFileDialog.DontConfirmOverwrite

        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.Fixed)

    def set_path(self):
        path = self.get_path()
        if not os.path.isdir(path):
            path = os.path.dirname(path)
        new_path = QFileDialog.getSaveFileName(directory=path, options=self.dialog_options)
        self.filename_edit.setText(new_path)

    def get_path(self):
        return str(self.filename_edit.text())

class H5FileWidget(FileWidget):
    def __init__(self, path="", parent=None):
        super(H5FileWidget, self).__init__(path)
        dataset_button = QPushButton("Dataset")
        self.dataset_edit = QLineEdit()
        self.layout().addRow(dataset_button, self.dataset_edit)
        dataset_button.clicked.connect(self.set_dataset)

    def set_dataset(self):
        dialog = QDialog()
        layout = QVBoxLayout(dialog)
        model = H5File(h5py.File(self.get_path()))
        tree_view = H5View()
        tree_view.setModel(model)
        tree_view.setSelectionMode(QAbstractItemView.SingleSelection)
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(tree_view)
        layout.addWidget(button_box)
        if dialog.exec_():
            self.dataset_edit.setText(tree_view.selected_path()[1:])

    def get_file(self):
        f = h5py.File(self.get_path())
        return dataserver_helpers.resolve_path(f, str(self.dataset_edit.text()))


if __name__ == '__main__':
    app = QApplication([])
    w = QWidget()
    l = QVBoxLayout(w)
    aw = ArrayWidget('Test Array', 0, 100, 5, 1e-5, 1e9)
    b = QPushButton("Get Array")
    hfw = H5FileWidget("C:\_Data")
    b2 = QPushButton("Get File")
    def print_array():
        print aw.get_array()
    def print_file():
        print hfw.get_file()
    b.clicked.connect(print_array)
    b2.clicked.connect(print_file)
    l.addWidget(aw)
    l.addWidget(b)
    l.addWidget(hfw)
    l.addWidget(b2)
    w.show()
    app.exec_()




