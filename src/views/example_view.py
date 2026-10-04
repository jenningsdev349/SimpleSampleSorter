from PySide6 import QtCore, QtWidgets


class MyWidget(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        self.button = QtWidgets.QPushButton("Select")
        self.text = QtWidgets.QLabel("Select Sample Import Folder:",
                                     alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

        self.main_layout = QtWidgets.QVBoxLayout(self)
        self.main_layout.addWidget(self.text)
        self.main_layout.addWidget(self.button)
