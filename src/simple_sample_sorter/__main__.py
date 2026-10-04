import sys

from PySide6 import QtWidgets

from views.example_view import MyWidget


def main() -> None:
    app = QtWidgets.QApplication(sys.argv)

    widget = MyWidget()
    widget.resize(800, 600)
    widget.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
