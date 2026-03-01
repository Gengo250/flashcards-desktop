from __future__ import annotations

import sys
from PySide6 import QtWidgets

from flashcards_app.core.db import Database
from flashcards_app.core.logging_config import configure_logging
from flashcards_app.ui.main_window import MainWindow


def main() -> None:
    configure_logging()

    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("Flashcards Desktop")
    app.setOrganizationName("LocalStudy")

    db = Database.default()
    db.initialize_schema()

    window = MainWindow(db=db)
    window.show()

    sys.exit(app.exec())