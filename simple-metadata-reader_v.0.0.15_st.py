import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton, QLineEdit, QListWidget, QTreeView, QFileSystemModel, QSplitter, QFileDialog, QLabel, QTextEdit, QMessageBox, QDialog, QDesktopWidget, QSizePolicy, QGraphicsOpacityEffect
from PyQt5.QtCore import QDir, Qt, QSortFilterProxyModel, QStorageInfo, QMimeData, QTimer, QRect, QPropertyAnimation, QEasingCurve, QParallelAnimationGroup
from PyQt5.QtGui import QTextCursor, QTextCharFormat, QColor
import sys
import pyexifinfo as pex
import json

class ToastNotification(QDialog):
    def __init__(self, message):
        super(ToastNotification, self).__init__()

        self.setWindowFlags(self.windowFlags() | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.Tool)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 150); color: white; font-size: 16px; padding: 10px; border-radius: 10px;")

        layout = QVBoxLayout()
        self.label = QLabel(message)
        self.label.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)
        layout.addWidget(self.label)
        self.setLayout(layout)

        self.adjustSize()
        desktop = QDesktopWidget()
        screen_rect = desktop.screenGeometry(desktop.primaryScreen())
        self.move(screen_rect.width() - self.width() - 10, screen_rect.height() - self.height() - 10)

        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self.animation_group = QParallelAnimationGroup(self)
        self.move_animation = QPropertyAnimation(self, b"geometry")
        self.opacity_animation = QPropertyAnimation(self.opacity_effect, b"opacity")

        self.move_animation.setDuration(300)  # Длительность анимации перемещения вверх в миллисекундах
        self.move_animation.setEasingCurve(QEasingCurve.Linear)  # Кривая анимации перемещения вверх
        self.move_animation.setStartValue(QRect(self.x(), self.y(), self.width(), self.height()))
        self.move_animation.setEndValue(QRect(self.x(), self.y() - self.height(), self.width(), self.height()))

        self.opacity_animation.setDuration(300)  # Длительность анимации затухания в миллисекундах
        self.opacity_animation.setEasingCurve(QEasingCurve.OutCubic)  # Кривая анимации затухания
        self.opacity_animation.setStartValue(1.0)  # Начальная прозрачность
        self.opacity_animation.setEndValue(0.0)  # Конечная прозрачность

        self.animation_group.addAnimation(self.move_animation)
        self.animation_group.addAnimation(self.opacity_animation)
        self.animation_group.finished.connect(self.hide)

    def show_notification(self):
        self.show()
        QTimer.singleShot(1000, self.animation_group.start)

class MainWindow(QMainWindow):
    def __init__(self):
        super(MainWindow, self).__init__()

        self.setWindowTitle("Meta Data Viewer Pre-Alfa")
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

        self.drive_model = QFileSystemModel()
        
        #All below is the new code from 20.07.2023
        self.drive_model.setRootPath('/Volumes')  # Set root path to '/Volumes'
        self.sidebar = QTreeView()
        self.sidebar.setModel(self.drive_model)
        self.sidebar.setHeaderHidden(True)
        for i in range(1, self.drive_model.columnCount()):
            self.sidebar.hideColumn(i)
        self.sidebar.clicked.connect(self.change_directory)
        
        #This added to set '/Volumes' as the start directory
        self.sidebar.setRootIndex(self.drive_model.index('/Volumes'))
        #End of new code added 20.07.2023

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

        self.selected_file_layout = QHBoxLayout()
        self.selected_file_label = QLabel()
        self.copy_button = QPushButton("Copy")
        self.copy_button.clicked.connect(self.copy_metadata)
        self.selected_file_layout.addWidget(self.selected_file_label)
        self.selected_file_layout.addWidget(self.copy_button)

        self.metadata_display = QTextEdit()
        self.metadata_display.setReadOnly(True)

        self.layout_right = QVBoxLayout()
        self.layout_right.addLayout(self.selected_file_layout)
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
        # Add the user's home directory
        self.sidebar.addItem(os.path.expanduser("~"))
        for drive in QStorageInfo.mountedVolumes():
            self.sidebar.addItem(drive.rootPath())
    
    #All below is the new code from 20.07.2023
    def change_directory(self, index):
        new_root_path = self.drive_model.filePath(index)
        self.file_system_model.setRootPath(new_root_path)
        self.tree.setRootIndex(self.file_system_model.index(new_root_path)) #End of new code added 20.07.2023



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

    def copy_metadata(self):
        metadata_text = self.metadata_display.toPlainText()
        mime_data = QMimeData()
        mime_data.setText(metadata_text)
        QApplication.clipboard().setMimeData(mime_data)

        toast = ToastNotification("Copied")
        toast.show_notification()

def main():
    app = QApplication(sys.argv)

    mainWin = MainWindow()
    mainWin.show()

    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
