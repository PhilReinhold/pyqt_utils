from PyQt4 import QtGui
from PyQt4.Qt import Qt
import h5py


class H5File(QtGui.QStandardItemModel):
    def __init__(self, file=None):
        super(H5File, self).__init__()
        if file is not None:
            self.set_file(file)

    def set_file(self, file):
        self.file = file
        self.clear()
        self.setColumnCount(2)
        for k in file.keys():
            item = h5_dispatch(file[k])
            self.invisibleRootItem().appendRow(item)

    def refresh(self):
        filename = self.file.filename
        self.file.close()
        self.set_file(h5py.File(filename))


def h5_dispatch(item):
    if isinstance(item, h5py.Group):
        return H5ItemName(item)
    else:
        return H5DatasetRow(item).columns


class H5Item(QtGui.QStandardItem):
    def __init__(self, group, row=None, text=""):
        super(H5Item, self).__init__(str(text))
        self.group = group
        self.row = row
        self.fullname = group.name
        self.name = group.name.split('/')[-1]
        self.marked_junk = False

        for k in group.attrs.keys():
            if k in ('DIMENSION_SCALE', 'DIMENSION_LIST', 'CLASS', 'NAME', 'REFERENCE_LIST'):
                # These are set by h5py for axis handling
                continue
            if k == "__JUNK__":
                self.marked_junk = group.attrs[k]
            self.appendRow(H5AttrRow(k, group).columns)

        if isinstance(group, h5py.Group):
            for k in group.keys():
                items = h5_dispatch(group[k])
                self.appendRow(items)

    def data(self, role):
        if role == Qt.BackgroundRole and self.row and self.row.plot is not None:
            return QtGui.QBrush(QtGui.QColor(255, 0, 0, 127))
        else:
            return super(H5Item, self).data(role)

    def is_junk(self):
        p = self.parent()
        if p is None:
            return self.marked_junk
        return self.marked_junk or p.is_junk()


class H5ItemName(H5Item):
    def __init__(self, group, row=None):
        #name = group.name.split('/')[-1]
        super(H5ItemName, self).__init__(group, row)
        self.setText(str(self.name))

    def setData(self, value, role):
        if role != Qt.EditRole:
            return super(H5ItemName, self).setData(value, role)
        v = value.toString()
        if v:
            self.set_name(v)

    def set_name(self, name):
        name = str(name)
        if name == self.name:
            return
        if self.parent() is None:
            parent_group = self.group.file
        else:
            parent_group = self.parent().group
        parent_group[name] = self.group
        self.group = parent_group[name]
        del parent_group[self.name]
        self.name = name
        self.setText(name)
        self.emitDataChanged()

    def flags(self):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable


class H5DatasetRow(object):
    def __init__(self, dataset):
        self.name = H5ItemName(dataset, self)
        self.shape = H5Item(dataset, self, text=str(dataset.shape))
        self.shape.setEditable(False)
        self.plot = None
        self.columns = [self.name, self.shape]

class H5AttrItem(QtGui.QStandardItem):
    def __init__(self, key, group, row, text=""):
        super(H5AttrItem, self).__init__(text)
        self.key = key
        self.row = row
        self.value = str(group.attrs[key])
        self.fullname = group.name + '/' + key
        self.name = key

    def data(self, role):
        if role == Qt.BackgroundRole:
            return QtGui.QBrush(QtGui.QColor(0xed, 0xe6, 0xa4, 127))
        else:
            return super(H5AttrItem, self).data(role)

    def flags(self):
        return Qt.ItemIsEnabled | Qt.ItemIsSelectable | Qt.ItemIsEditable

    def is_junk(self):
        return self.parent().is_junk()


class H5AttrKey(H5AttrItem):
    def __init__(self, key, group, row):
        super(H5AttrKey, self).__init__(key, group, row, text=str(key))

    def setData(self, value, role):
        if role != Qt.EditRole:
            return super(H5AttrKey, self).setData(value, role)
        attr_val = self.group.attrs[self.key]
        del self.group.attrs[self.key]
        self.key = str(value.toString())
        self.group.attrs[self.key] = attr_val


class H5AttrValue(H5AttrItem):
    def __init__(self, key, group, row):
        #value = str(group.attrs[key])
        super(H5AttrValue, self).__init__(key, group, row)
        self.setText(self.value)

    def setData(self, value, role):
        if role != Qt.EditRole:
            return super(H5AttrValue, self).setData(value, role)
        if value.canConvert(int):
            v = value.toInt()
        elif value.canConvert(float):
            v = value.toFloat()
        else:
            v = str(value.toString())
        self.group.attrs[self.key] = v


class H5AttrRow(object):
    def __init__(self, key, dataset):
        self.name = H5AttrKey(key, dataset, self)
        self.value = H5AttrValue(key, dataset, self)
        self.columns = [self.name, self.value]

class H5View(QtGui.QTreeView):
    def __init__(self):
        super(H5View, self).__init__()
        self.resizeColumnToContents(0)
        self.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.setEditTriggers(QtGui.QAbstractItemView.EditKeyPressed)
        expand_action = QtGui.QAction("Expand All", self)
        expand_action.triggered.connect(self.expandAll)
        self.addAction(expand_action)

        collapse_action = QtGui.QAction("Collapse All", self)
        collapse_action.triggered.connect(self.collapseAll)
        self.addAction(collapse_action)

class TreeFilterModel(QtGui.QSortFilterProxyModel):
    def __init__(self, **kwargs):
        super(TreeFilterModel, self).__init__(**kwargs)
        self.matching_items = []

    def itemFromIndex(self, idx):
        return self.sourceModel().itemFromIndex(self.mapToSource(idx))

    def set_matches(self, matches):
        matches = set(matches)
        old_matches = None
        root = self.sourceModel().invisibleRootItem()
        while matches != old_matches:
            old_matches = matches
            matches = matches.union({i.parent() for i in old_matches})
            matches = matches.difference({None, root})
        self.matching_items = matches
        self.invalidateFilter()

    def filterAcceptsRow(self, src_i, src_parent_index):
        this_parent = self.sourceModel().itemFromIndex(src_parent_index)
        if this_parent:
            this_item = this_parent.child(src_i)
        else:
            this_index = self.sourceModel().index(src_i, 0)
            this_item = self.sourceModel().itemFromIndex(this_index)
        return self.filter_accepts_item(this_item)

    def filter_accepts_item(self, item):
        return item in self.matching_items


class RecursiveFilterModel(TreeFilterModel):
    attrs_visible = False
    junk_visible = False
    term_string = ""

    def setSourceModel(self, model):
        super(RecursiveFilterModel, self).setSourceModel(model)
        model.modelReset.connect(self.source_model_changed)

    def get_matches(self, t):
        items = self.sourceModel().findItems("", Qt.MatchContains | Qt.MatchRecursive)
        x = [i for i in items if t in i.fullname]
        return x
        #return [i for i in items if t in i.fullname]
        #return self.sourceModel().findItems(t, Qt.MatchContains | Qt.MatchRecursive)

    def toggle_attrs_visible(self, checked):
        self.attrs_visible = checked
        self.invalidateFilter()

    def toggle_junk_visible(self, checked):
        self.junk_visible = checked
        self.invalidateFilter()

    def source_model_changed(self):
        self.set_match_term(self.term_string)

    def set_match_term(self, term_string):
        # Match all words
        self.term_string = term_string
        matches = [set(self.get_matches(t)) for t in str(term_string).split()]
        m0 = set(self.get_matches(""))
        self.set_matches(m0.intersection(*matches))

    def filter_accepts_item(self, item):
        if not self.attrs_visible and isinstance(item, H5AttrItem):
            return False
        if not self.junk_visible and item.is_junk():
            return False
        return super(RecursiveFilterModel, self).filter_accepts_item(item)

class SearchableH5View(QtGui.QWidget):
    def __init__(self, model):
        super(SearchableH5View, self).__init__()
        layout = QtGui.QVBoxLayout(self)
        match_model = RecursiveFilterModel()
        match_model.setSourceModel(model)
        match_model.set_match_term("")
        self.tree_view = H5View()
        self.tree_view.setModel(match_model)
        layout.addWidget(self.tree_view)
        self.search_box = QtGui.QLineEdit()
        layout.addWidget(self.search_box)
        self.search_box.textChanged.connect(match_model.set_match_term)

