import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QListWidget, QTreeView, QFileSystemModel, QSplitter, QFileDialog, QLabel, QTextEdit
from PyQt5.QtCore import QDir, Qt, QSortFilterProxyModel, QStorageInfo
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor
import sys
import pyexifinfo as pex
import json

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Meta Data Viewer")
        self.setGeometry(100, 100, 800, 600)

        self.filepath_input = QLineEdit()
        self.filepath_input.textChanged.connect(self.update_metadata)
        self.select_button = QPushButton("Select")
        self.select_button.clicked.connect(self.open_file_dialog)

        self.input_layout = QHBoxLayout()
        self.input_layout.addWidget(self.filepath_input, 1)
        self.input_layout.addWidget(self.select_button, 0)

        self.file_system_model = QFileSystemModel()
        self.file_system_model.setRootPath('/')

        self.sidebar = QListWidget()
        self.update_drives()
        self.sidebar.itemClicked.connect(self.change_directory)

        self.tree = QTreeView()
        self.tree.setModel(self.file_system_model)
        self.tree.setHeaderHidden(True)
        for i in range(1, self.file_system_model.columnCount()):
            self.tree.hideColumn(i)
        self.tree.clicked.connect(self.select_file)
        self.tree.selectionModel().currentChanged.connect(self.select_file)

        self.layout_left = QVBoxLayout()
        self.layout_left.addWidget(self.sidebar)
        self.layout_left.addWidget(self.tree)

        self.widget_left = QWidget()
        self.widget_left.setLayout(self.layout_left)

        self.selected_file_label = QLabel()

        self.metadata_display = QTextEdit()
        self.metadata_display.setReadOnly(True)

        self.layout_right = QVBoxLayout()
        self.layout_right.addWidget(self.selected_file_label)
        self.layout_right.addWidget(self.metadata_display)

        self.widget_right = QWidget()
        self.widget_right.setLayout(self.layout_right)

        self.splitter = QSplitter()
        self.splitter.addWidget(self.widget_left)
        self.splitter.addWidget(self.widget_right)

        self.main_layout = QVBoxLayout()
        self.main_layout.addLayout(self.input_layout)
        self.main_layout.addWidget(self.splitter)

        self.main_widget = QWidget()
        self.main_widget.setLayout(self.main_layout)

        self.setCentralWidget(self.main_widget)

    def open_file_dialog(self):
        file_dialog = QFileDialog()
        file_path = file_dialog.getOpenFileName()
        self.filepath_input.setText(file_path[0])
        self.update_metadata()

    def update_metadata(self):
        file_path = self.filepath_input.text()
        self.selected_file_label.setText(f"Selected file: {os.path.basename(file_path)}")
        metadata = self.get_metadata(file_path)
        self.display_metadata(metadata)

    def update_drives(self):
        self.sidebar.clear()
        for drive in QStorageInfo.mountedVolumes():
            self.sidebar.addItem(drive.rootPath())

    def change_directory(self, item):
        self.tree.setRootIndex(self.file_system_model.index(item.text()))

    def select_file(self, index):
        file_path = self.file_system_model.filePath(index)
        self.filepath_input.setText(file_path)
        self.update_metadata()

    @staticmethod
    def get_metadata(file_path):
        try:
            metadata = pex.get_json(file_path)
            for data in metadata:
                if 'SourceFile' in data:
                    del data['SourceFile']
                if 'File:Directory' in data:
                    del data['File:Directory']
                if 'File:FileName' in data:
                    del data['File:FileName']
            return metadata
        except Exception as e:
            return [{"error": str(e)}]

    def display_metadata(self, metadata):
        self.metadata_display.clear()
        cursor = self.metadata_display.textCursor()
        cursor.movePosition(QTextCursor.Start)

        key_format = QTextCharFormat()
        key_format.setForeground(QColor("#9CDBFE"))

        value_format = QTextCharFormat()
        value_format.setForeground(QColor("#DBDBA9"))

        for data in metadata:
            for key, value in data.items():
                cursor.insertText(key, key_format)
                cursor.insertText(": ", key_format)
                cursor.insertText(str(value), value_format)
                cursor.insertText("\n", value_format)

def main():
    app = QApplication(sys.argv)

    mainWin = MainWindow()
    mainWin.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
