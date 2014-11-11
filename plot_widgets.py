from PyQt4 import QtGui, QtCore
import warnings
import numpy as np
import pyqtgraph as pg
pg.setConfigOption("useWeave", False)
from pyqtgraph.dockarea import Dock, DockArea
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt4agg import FigureCanvasQTAgg, NavigationToolbar2QTAgg

class CrosshairPlotWidget(pg.PlotWidget):
    crosshair_moved = QtCore.pyqtSignal(float, float)
    def __init__(self, parametric=False, *args, **kwargs):
        super(CrosshairPlotWidget, self).__init__(*args, **kwargs)
        self.scene().sigMouseClicked.connect(self.toggle_search)
        self.scene().sigMouseMoved.connect(self.handle_mouse_move)
        self.cross_section_enabled = False
        self.parametric = parametric
        self.search_mode = True
        self.label = None
        self.selected_point = None

    def set_data(self, data):
        if data is not None and len(data) > 0:
            self.clear()
            self.plot(data)

    def toggle_search(self, mouse_event):
        if mouse_event.double():
            if self.cross_section_enabled:
                self.hide_cross_hair()
            else:
                self.add_cross_hair()
        elif self.cross_section_enabled:
            self.search_mode = not self.search_mode
            if self.search_mode:
                self.handle_mouse_move(mouse_event.scenePos())

    def handle_mouse_move(self, mouse_event):
        if self.cross_section_enabled and self.search_mode:
            item = self.getPlotItem()
            vb = item.getViewBox()
            view_coords = vb.mapSceneToView(mouse_event)
            view_x, view_y = view_coords.x(), view_coords.y()

            best_guesses = []
            for data_item in item.items:
                if isinstance(data_item, pg.PlotDataItem):
                    xdata, ydata = data_item.xData, data_item.yData
                    index_distance = lambda i: (xdata[i]-view_x)**2 + (ydata[i] - view_y)**2
                    if self.parametric:
                        index = min(range(len(xdata)), key=index_distance)
                    else:
                        index = min(np.searchsorted(xdata, view_x), len(xdata)-1)
                        if index and xdata[index] - view_x > view_x - xdata[index - 1]:
                            index -= 1
                    pt_x, pt_y = xdata[index], ydata[index]
                    best_guesses.append(((pt_x, pt_y), index_distance(index)))

            if not best_guesses:
                return

            (pt_x, pt_y), _ = min(best_guesses, key=lambda x: x[1])
            self.selected_point = (pt_x, pt_y)
            self.v_line.setPos(pt_x)
            self.h_line.setPos(pt_y)
            self.label.setText("x=%.2e, y=%.2e" % (pt_x, pt_y))
            self.crosshair_moved.emit(pt_x, pt_y)

    def add_cross_hair(self):
        self.h_line = pg.InfiniteLine(angle=0, movable=False)
        self.v_line = pg.InfiniteLine(angle=90, movable=False)
        self.addItem(self.h_line, ignoreBounds=False)
        self.addItem(self.v_line, ignoreBounds=False)
        if self.label is None:
            self.label = pg.LabelItem(justify="right")
            self.getPlotItem().layout.addItem(self.label, 4, 1)
        self.x_cross_index = 0
        self.y_cross_index = 0
        self.cross_section_enabled = True

    def hide_cross_hair(self):
        self.removeItem(self.h_line)
        self.removeItem(self.v_line)
        self.cross_section_enabled = False


class CrossSectionImageView(pg.ImageView):
    def __init__(self, trace_size=80, **kwargs):
        kwargs['view'] = pg.PlotItem(labels=kwargs.pop('labels', None))
        super(CrossSectionImageView, self).__init__(**kwargs)
        self.view.setAspectLocked(lock=False)
        self.search_mode = False
        self.signals_connected = False
        self.set_histogram(False)
        histogram_action = QtGui.QAction('Histogram', self)
        histogram_action.setCheckable(True)
        histogram_action.triggered.connect(self.set_histogram)
        self.scene.contextMenu.append(histogram_action)

        self.ui.histogram.gradient.loadPreset('thermal')
        try:
            self.connect_signal()
        except RuntimeError:
            warnings.warn('Scene not set up, cross section signals not connected')

        self.y_cross_index = 0
        self.x_cross_index = 0
        self.h_cross_section_widget = CrosshairPlotWidget()
        self.h_cross_section_widget.add_cross_hair()
        self.h_cross_section_widget.search_mode = False
        self.h_cross_section_widget_data = self.h_cross_section_widget.plot([0,0])
        self.h_line = pg.InfiniteLine(pos=0, angle=0, movable=False)
        self.view.addItem(self.h_line, ignoreBounds=False)

        self.v_cross_section_widget = CrosshairPlotWidget()
        self.v_cross_section_widget.add_cross_hair()
        self.v_cross_section_widget.search_mode = False
        self.v_cross_section_widget_data = self.v_cross_section_widget.plot([0,0])
        self.v_line = pg.InfiniteLine(pos=0, angle=90, movable=False)
        self.view.addItem(self.v_line, ignoreBounds=False)

        self.h_cross_section_widget.crosshair_moved.connect(lambda x, _: self.set_position(x=x))
        self.v_cross_section_widget.crosshair_moved.connect(lambda y, _: self.set_position(y=y))

    def set_data(self, data):
        self.setImage(data)

    def setLabels(self, xlabel="X", ylabel="Y", zlabel="Z"):
        self.plot_item.setLabels(bottom=(xlabel,), left=(ylabel,))
        self.h_cross_section_widget.plotItem.setLabels(bottom=xlabel, left=zlabel)
        self.v_cross_section_widget.plotItem.setLabels(bottom=ylabel, left=zlabel)
        self.ui.histogram.item.axis.setLabel(text=zlabel)

    def setImage(self, *args, **kwargs):
        if 'pos' in kwargs:
            self._x0, self._y0 = kwargs['pos']
        else:
            self._x0, self._y0 = 0, 0
        if 'scale' in kwargs:
            self._xscale, self._yscale = kwargs['scale']
        else:
            self._xscale, self._yscale = 1, 1

        if self.imageItem.image is not None:
            (min_x, max_x), (min_y, max_y) = self.imageItem.getViewBox().viewRange()
            mid_x, mid_y = (max_x + min_x)/2., (max_y + min_y)/2.
        else:
            mid_x, mid_y = 0, 0

        self.h_line.setPos(mid_y)
        self.v_line.setPos(mid_x)

        super(CrossSectionImageView, self).setImage(*args, **kwargs)
        self.update_cross_section()

    def set_histogram(self, visible):
        self.ui.histogram.setVisible(visible)
        self.ui.roiBtn.setVisible(visible)
        self.ui.normBtn.setVisible(visible)

    def connect_signal(self):
        """This can only be run after the item has been embedded in a scene"""
        if self.signals_connected:
            warnings.warn("")
        if self.imageItem.scene() is None:
            raise RuntimeError('Signal can only be connected after it has been embedded in a scene.')
        self.imageItem.scene().sigMouseClicked.connect(self.toggle_search)
        self.imageItem.scene().sigMouseMoved.connect(self.handle_mouse_move)
        self.timeLine.sigPositionChanged.connect(self.update_cross_section)
        self.signals_connected = True

    def toggle_search(self, mouse_event):
        if mouse_event.double():
            return
        self.search_mode = not self.search_mode
        if self.search_mode:
            self.handle_mouse_move(mouse_event.scenePos())

    def handle_mouse_move(self, mouse_event):
        if self.search_mode:
            view_coords = self.imageItem.getViewBox().mapSceneToView(mouse_event)
            view_x, view_y = view_coords.x(), view_coords.y()
            self.set_position(view_x, view_y)

    def set_position(self, x=None, y=None):
        if x is None:
            x = self.v_line.getXPos()
        if y is None:
            y = self.h_line.getYPos()
        item_coords = self.imageItem.getViewBox().mapFromViewToItem(self.imageItem, QtCore.QPointF(x, y))
        #item_coords = self.imageItem.mapFromScene(mouse_event)
        item_x, item_y = item_coords.x(), item_coords.y()
        max_x, max_y = self.imageItem.image.shape
        if item_x < 0 or item_x > max_x or item_y < 0 or item_y > max_y:
            return
        self.v_line.setPos(x)
        self.h_line.setPos(y)
        #(min_view_x, max_view_x), (min_view_y, max_view_y) = self.imageItem.getViewBox().viewRange()
        self.x_cross_index = max(min(int(item_x), max_x-1), 0)
        self.y_cross_index = max(min(int(item_y), max_y-1), 0)
        z_val = self.imageItem.image[self.x_cross_index, self.y_cross_index]
        self.update_cross_section()
        #self.text_item.setText("x=%.2e, y=%.2e, z=%.2e" % (view_x, view_y, z_val))

    def update_cross_section(self):
        nx, ny = self.imageItem.image.shape
        x0, y0, xscale, yscale = self._x0, self._y0, self._xscale, self._yscale
        xdata = np.linspace(x0, x0+(xscale*(nx-1)), nx)
        ydata = np.linspace(y0, y0+(yscale*(ny-1)), ny)
        zval = self.imageItem.image[self.x_cross_index, self.y_cross_index]
        self.h_cross_section_widget_data.setData(xdata, self.imageItem.image[:, self.y_cross_index])
        self.h_cross_section_widget.v_line.setPos(xdata[self.x_cross_index])
        self.h_cross_section_widget.h_line.setPos(zval)
        self.v_cross_section_widget_data.setData(ydata, self.imageItem.image[self.x_cross_index, :])
        self.v_cross_section_widget.v_line.setPos(ydata[self.y_cross_index])
        self.v_cross_section_widget.h_line.setPos(zval)

class MoviePlotWidget(CrossSectionImageView):
    def __init__(self, *args, **kwargs):
        super(MoviePlotWidget, self).__init__(*args, **kwargs)
        self.play_button = QtGui.QPushButton("Play")
        self.stop_button = QtGui.QPushButton("Stop")
        self.stop_button.hide()
        self.play_timer = QtCore.QTimer()
        self.play_timer.setInterval(50)
        self.play_timer.timeout.connect(self.increment)
        self.play_button.clicked.connect(self.play_timer.start)
        self.play_button.clicked.connect(self.play_button.hide)
        self.play_button.clicked.connect(self.stop_button.show)
        self.stop_button.clicked.connect(self.play_timer.stop)
        self.stop_button.clicked.connect(self.play_button.show)
        self.stop_button.clicked.connect(self.stop_button.hide)

    def setImage(self, array, *args, **kwargs):
        super(MoviePlotWidget, self).setImage(array, *args, **kwargs)
        self.tpts = len(array)

    def increment(self):
        self.setCurrentIndex((self.currentIndex + 1) % self.tpts)


class CloseableDock(Dock):
    def __init__(self, name, *args, **kwargs):
        super(CloseableDock, self).__init__(name, *args, **kwargs)
        style = QtGui.QStyleFactory().create("windows")
        icon = style.standardIcon(QtGui.QStyle.SP_TitleBarCloseButton)
        button = QtGui.QPushButton(icon, "", self)
        button.clicked.connect(self.close)
        button.setGeometry(0, 0, 20, 20)
        button.raise_()
        self.closeClicked = button.clicked

    def close(self):
        self.setParent(None)
        self.closed = True
        if self._container is not self.area.topContainer:
            self._container.apoptose()

class CrossSectionDock(CloseableDock):
    def __init__(self, name, **kwargs):
        widget = self.widget = kwargs['widget'] = CrossSectionImageView()
        super(CrossSectionDock, self).__init__(name, **kwargs)
        self.cross_section_enabled = False
        self.closeClicked.connect(self.hide_cross_section)
        self.h_cross_dock = CloseableDock(name='x trace', widget=widget.h_cross_section_widget, area=self.area)
        self.v_cross_dock = CloseableDock(name='y trace', widget=widget.v_cross_section_widget, area=self.area)
        widget.imageItem.scene().sigMouseClicked.connect(self.handle_mouse_click)
        widget.removeItem(widget.h_line)
        widget.removeItem(widget.v_line)
        widget.search_mode = False
        self.cross_section_enabled = False

    def set_data(self, array):
        self.widget.setImage(array)

    def toggle_cross_section(self):
        if self.cross_section_enabled:
            self.hide_cross_section()
        else:
            self.add_cross_section()

    def hide_cross_section(self):
        if self.cross_section_enabled:
            self.widget.removeItem(self.widget.h_line)
            self.widget.removeItem(self.widget.v_line)
            #self.ui.graphicsView.removeItem(self.text_item)
            self.cross_section_enabled = False

            self.h_cross_dock.close()
            self.v_cross_dock.close()

    def add_cross_section(self):
        image_item = self.widget.imageItem
        if image_item.image is not None:
            (min_x, max_x), (min_y, max_y) = image_item.getViewBox().viewRange()
            mid_x, mid_y = (max_x + min_x)/2., (max_y + min_y)/2.
        else:
            mid_x, mid_y = 0, 0
        self.widget.addItem(self.widget.h_line, ignoreBounds=False)
        self.widget.addItem(self.widget.v_line, ignoreBounds=False)
        self.x_cross_index = 0
        self.y_cross_index = 0
        self.cross_section_enabled = True
        #self.text_item = pg.LabelItem(justify="right")
        #self.img_view.ui.gridLayout.addWidget(self.text_item, 2, 1, 1, 2)
        #self.img_view.ui.graphicsView.addItem(self.text_item)#, 2, 1)
        #self.widget.layout().addItem(self.text_item, 4, 1)
        #self.cs_layout.addItem(self.label, 2, 1) #TODO: Find a way of displaying this label
        self.search_mode = True

        self.area.addDock(self.h_cross_dock)
        self.area.addDock(self.v_cross_dock, position='right', relativeTo=self.h_cross_dock)
        self.cross_section_enabled = True

    def handle_mouse_click(self, mouse_event):
        if mouse_event.double():
            self.toggle_cross_section()

class BackendSwitchableDock(CloseableDock):
    def __init__(self, *args, **kwargs):
        super(BackendSwitchableDock, self).__init__(*args, **kwargs)
        style = QtGui.QStyleFactory().create("windows")
        icon = style.standardIcon(QtGui.QStyle.SP_BrowserReload)
        switch_button = QtGui.QPushButton(icon, "", self)
        switch_button.clicked.connect(lambda: self.widgets[0].toggle_backend())
        switch_button.setGeometry(20, 0, 20, 20)
        switch_button.raise_()

class MPLPlotWidget(QtGui.QWidget):
    def __init__(self):
        super(MPLPlotWidget, self).__init__()
        layout = QtGui.QVBoxLayout(self)
        fig = Figure()
        self.axes = fig.add_subplot(111)
        self.axes.hold(False)
        self.canvas = FigureCanvasQTAgg(fig)
        self.navbar = NavigationToolbar2QTAgg(self.canvas, self)
        layout.addWidget(self.canvas)
        layout.addWidget(self.navbar)
        #self.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Expanding)

    def set_data(self, data):
        self.axes.plot(data)

class MPLImageView(MPLPlotWidget):
    def set_data(self, data):
        self.axes.imshow(data, interpolation='nearest', aspect='auto')


class BackendSwitchablePlot(QtGui.QWidget):
    MPLWidget = MPLPlotWidget
    PGWidget = CrosshairPlotWidget
    def __init__(self):
        super(BackendSwitchablePlot, self).__init__()
        layout = QtGui.QVBoxLayout(self)
        self.widget = self.MPLWidget()
        layout.addWidget(self.widget)
        self.is_mpl = True
        self._data = None

    def set_data(self, data):
        self._data = data
        self.widget.set_data(data)

    def toggle_backend(self):
        self.widget.setParent(None)
        if self.is_mpl:
            self.widget = self.PGWidget()
        else:
            self.widget = self.MPLWidget()
        self.is_mpl = not self.is_mpl
        if self._data is not None:
            self.widget.set_data(self._data)
        self.layout().addWidget(self.widget)

class BackendSwitchableImageView(BackendSwitchablePlot):
    MPLWidget = MPLImageView
    PGWidget = CrossSectionImageView


if __name__ == '__main__':
    import sys
    import numpy as np
    app = QtGui.QApplication([])
    w = DockArea()
    w1 = CrosshairPlotWidget()
    w1.set_data(np.sin(np.linspace(0, 10, 100)))
    d = CloseableDock("Crosshair Plot", widget=w1)
    w.addDock(d)
    d2 = CrossSectionDock("Cross Section Dock")
    xs, ys = np.mgrid[-500:500, -500:500]/100.
    rs = np.sqrt(xs**2 + ys**2)
    d2.set_data(rs)
    w.addDock(d2)
    #w2 = CrossSectionImageView()
    #w2.set_data(rs)
    #ts, xs, ys = np.mgrid[0:100, -50:50, -50:50]/20.
    #zs = np.sinc(xs**2 + ys**2 + ts)
    #w2 = MoviePlotWidget()
    #w2.set_data(zs)
    #l.addWidget(w2)
    #l.addWidget(w2.play_button)
    #l.addWidget(w2.stop_button)
    #l.addWidget(w2.h_cross_section_widget)
    #l.addWidget(w2.v_cross_section_widget)
    w.show()
    sys.exit(app.exec_())
