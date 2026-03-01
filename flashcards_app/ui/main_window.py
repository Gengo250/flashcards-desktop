from __future__ import annotations

import logging
from pathlib import Path

from PySide6 import QtCore, QtWidgets, QtGui

from flashcards_app.core.csv_importer import read_cards_from_csv
from flashcards_app.core.db import Database
from flashcards_app.repos.card_repo import CardRepository
from flashcards_app.repos.deck_repo import DeckRepository
from flashcards_app.services.errors import CsvFormatError
from flashcards_app.services.study_session import StudySession
from flashcards_app.ui.styles import DARK_QSS
from flashcards_app.ui.flashcard_widget import FlashcardWidget

log = logging.getLogger("ui.main_window")


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, db: Database) -> None:
        super().__init__()
        self.db = db
        self.decks = DeckRepository(db)
        self.cards = CardRepository(db)

        self.setWindowTitle("Flashcards Desktop")
        self.resize(1100, 650)

        self._session: StudySession | None = None
        self._current_deck_id: int | None = None

        # atalhos (mantém referência para não serem coletados)
        self._sc_space: QtGui.QShortcut | None = None
        self._sc_1: QtGui.QShortcut | None = None
        self._sc_2: QtGui.QShortcut | None = None
        self._sc_3: QtGui.QShortcut | None = None
        self._sc_4: QtGui.QShortcut | None = None

        self._build_ui()
        self._load_decks()

    def _build_ui(self) -> None:
        self.setStyleSheet(DARK_QSS)

        root = QtWidgets.QWidget()
        self.setCentralWidget(root)

        layout = QtWidgets.QHBoxLayout(root)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(14)

        splitter = QtWidgets.QSplitter(QtCore.Qt.Orientation.Horizontal)
        layout.addWidget(splitter)

        # -------------------------
        # Left panel: decks
        # -------------------------
        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        left_layout.setSpacing(10)

        title = QtWidgets.QLabel("Pastas de estudo")
        title.setStyleSheet("font-size: 18px; font-weight: 700;")
        left_layout.addWidget(title)

        self.deck_list = QtWidgets.QListWidget()
        self.deck_list.currentItemChanged.connect(self._on_deck_selected)
        left_layout.addWidget(self.deck_list, 1)

        btn_row = QtWidgets.QHBoxLayout()
        self.btn_add_deck = QtWidgets.QPushButton("Nova pasta")
        self.btn_del_deck = QtWidgets.QPushButton("Excluir")
        self.btn_add_deck.clicked.connect(self._add_deck)
        self.btn_del_deck.clicked.connect(self._delete_deck)
        btn_row.addWidget(self.btn_add_deck)
        btn_row.addWidget(self.btn_del_deck)
        left_layout.addLayout(btn_row)

        self.btn_import = QtWidgets.QPushButton("Importar CSV para esta pasta")
        self.btn_import.clicked.connect(self._import_csv_into_current_deck)
        left_layout.addWidget(self.btn_import)

        self.btn_study = QtWidgets.QPushButton("Estudar")
        self.btn_study.clicked.connect(self._start_study)
        left_layout.addWidget(self.btn_study)

        splitter.addWidget(left)
        left.setMinimumWidth(320)

        # -------------------------
        # Right panel: stacked (cards table / study)
        # -------------------------
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.setSpacing(10)

        header_row = QtWidgets.QHBoxLayout()
        self.lbl_deck = QtWidgets.QLabel("Selecione uma pasta")
        self.lbl_deck.setStyleSheet("font-size: 18px; font-weight: 700;")
        header_row.addWidget(self.lbl_deck)
        header_row.addStretch(1)
        self.lbl_count = QtWidgets.QLabel("")
        header_row.addWidget(self.lbl_count)
        right_layout.addLayout(header_row)

        self.stack = QtWidgets.QStackedWidget()
        right_layout.addWidget(self.stack, 1)

        # Page 0: cards table
        cards_page = QtWidgets.QWidget()
        cards_layout = QtWidgets.QVBoxLayout(cards_page)

        self.table = QtWidgets.QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Nº", "Pergunta", "Resposta"])
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setAlternatingRowColors(False)
        cards_layout.addWidget(self.table, 1)

        hint = QtWidgets.QLabel("Dica: importe um CSV e depois clique em Estudar.")
        hint.setStyleSheet("color: #a8b0d4;")
        cards_layout.addWidget(hint)

        self.stack.addWidget(cards_page)

        # Page 1: study view
        study_page = QtWidgets.QWidget()
        study_layout = QtWidgets.QVBoxLayout(study_page)
        study_layout.setSpacing(12)

        top_row = QtWidgets.QHBoxLayout()
        self.lbl_progress = QtWidgets.QLabel("0/0")
        self.lbl_progress.setStyleSheet("color: #a8b0d4;")
        top_row.addWidget(self.lbl_progress)
        top_row.addStretch(1)
        self.btn_back = QtWidgets.QPushButton("Voltar para lista")
        self.btn_back.clicked.connect(self._back_to_list)
        top_row.addWidget(self.btn_back)
        study_layout.addLayout(top_row)

        # Flashcard “estilo carta”
        self.flashcard = FlashcardWidget()
        self.flashcard.flipped.connect(self._on_flashcard_flipped)
        study_layout.addWidget(self.flashcard, 1)

        # Botão para virar
        self.btn_show = QtWidgets.QPushButton("Virar carta (Espaço)")
        self.btn_show.clicked.connect(self._toggle_answer)
        study_layout.addWidget(self.btn_show)

        # Avaliação
        rate_row = QtWidgets.QHBoxLayout()
        self.btn_again = QtWidgets.QPushButton("Again (1)")
        self.btn_hard = QtWidgets.QPushButton("Hard (2)")
        self.btn_good = QtWidgets.QPushButton("Good (3)")
        self.btn_easy = QtWidgets.QPushButton("Easy (4)")
        for b in (self.btn_again, self.btn_hard, self.btn_good, self.btn_easy):
            b.setEnabled(False)
        self.btn_again.clicked.connect(lambda: self._rate("again"))
        self.btn_hard.clicked.connect(lambda: self._rate("hard"))
        self.btn_good.clicked.connect(lambda: self._rate("good"))
        self.btn_easy.clicked.connect(lambda: self._rate("easy"))
        rate_row.addWidget(self.btn_again)
        rate_row.addWidget(self.btn_hard)
        rate_row.addWidget(self.btn_good)
        rate_row.addWidget(self.btn_easy)
        study_layout.addLayout(rate_row)

        self.lbl_stats = QtWidgets.QLabel("")
        self.lbl_stats.setStyleSheet("color: #a8b0d4;")
        study_layout.addWidget(self.lbl_stats)

        # Atalhos de teclado (mantendo referência e contexto correto)
        self._sc_space = QtGui.QShortcut(QtGui.QKeySequence("Space"), study_page)
        self._sc_1 = QtGui.QShortcut(QtGui.QKeySequence("1"), study_page)
        self._sc_2 = QtGui.QShortcut(QtGui.QKeySequence("2"), study_page)
        self._sc_3 = QtGui.QShortcut(QtGui.QKeySequence("3"), study_page)
        self._sc_4 = QtGui.QShortcut(QtGui.QKeySequence("4"), study_page)

        for sc in (self._sc_space, self._sc_1, self._sc_2, self._sc_3, self._sc_4):
            sc.setContext(QtCore.Qt.ShortcutContext.WidgetWithChildrenShortcut)

        self._sc_space.activated.connect(self._toggle_answer)
        self._sc_1.activated.connect(lambda: self._rate("again"))
        self._sc_2.activated.connect(lambda: self._rate("hard"))
        self._sc_3.activated.connect(lambda: self._rate("good"))
        self._sc_4.activated.connect(lambda: self._rate("easy"))

        self.stack.addWidget(study_page)

        # IMPORTANTÍSSIMO: anexar o painel direito ao splitter
        splitter.addWidget(right)
        splitter.setStretchFactor(0, 0)  # esquerda
        splitter.setStretchFactor(1, 1)  # direita ocupa mais

        self._set_controls_enabled(False)

    def _set_controls_enabled(self, enabled: bool) -> None:
        self.btn_import.setEnabled(enabled)
        self.btn_del_deck.setEnabled(enabled)
        self.btn_study.setEnabled(enabled)

    # -------------------------
    # Decks
    # -------------------------
    def _load_decks(self) -> None:
        self.deck_list.clear()
        decks = self.decks.list_all()
        for d in decks:
            item = QtWidgets.QListWidgetItem(d.name)
            item.setData(QtCore.Qt.ItemDataRole.UserRole, d.id)
            self.deck_list.addItem(item)

        if decks:
            self.deck_list.setCurrentRow(0)
        else:
            self._current_deck_id = None
            self.lbl_deck.setText("Crie uma pasta para começar")
            self.lbl_count.setText("")
            self.table.setRowCount(0)
            self._set_controls_enabled(False)

    def _on_deck_selected(self, current: QtWidgets.QListWidgetItem | None, _prev) -> None:
        if not current:
            self._current_deck_id = None
            self._set_controls_enabled(False)
            return

        deck_id = int(current.data(QtCore.Qt.ItemDataRole.UserRole))
        self._current_deck_id = deck_id
        self.lbl_deck.setText(current.text())
        self._set_controls_enabled(True)
        self._refresh_cards_table()

    def _add_deck(self) -> None:
        name, ok = QtWidgets.QInputDialog.getText(self, "Nova pasta", "Nome da pasta (ex.: Sistemas Operacionais):")
        if not ok:
            return
        try:
            self.decks.create(name)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Não foi possível criar a pasta.\n\n{e}")
            log.exception("create deck failed")
            return
        self._load_decks()

    def _delete_deck(self) -> None:
        if self._current_deck_id is None:
            return
        deck_name = self.lbl_deck.text()
        resp = QtWidgets.QMessageBox.question(
            self,
            "Confirmar exclusão",
            f"Excluir a pasta '{deck_name}' e TODOS os cards dentro?\n\nIsso não pode ser desfeito.",
        )
        if resp != QtWidgets.QMessageBox.StandardButton.Yes:
            return

        try:
            self.decks.delete(self._current_deck_id)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Não foi possível excluir.\n\n{e}")
            log.exception("delete deck failed")
            return
        self._load_decks()

    # -------------------------
    # Cards table
    # -------------------------
    def _refresh_cards_table(self) -> None:
        if self._current_deck_id is None:
            self.table.setRowCount(0)
            return

        cards = self.cards.list_by_deck(self._current_deck_id)
        self.lbl_count.setText(f"{len(cards)} cards")

        self.table.setRowCount(len(cards))
        for i, c in enumerate(cards):
            n = "" if c.number is None else str(c.number)
            q = c.question if len(c.question) <= 120 else c.question[:120] + "…"
            a = c.answer if len(c.answer) <= 120 else c.answer[:120] + "…"
            self.table.setItem(i, 0, QtWidgets.QTableWidgetItem(n))
            self.table.setItem(i, 1, QtWidgets.QTableWidgetItem(q))
            self.table.setItem(i, 2, QtWidgets.QTableWidgetItem(a))

        self.table.resizeColumnsToContents()

    # -------------------------
    # Import CSV
    # -------------------------
    def _import_csv_into_current_deck(self) -> None:
        if self._current_deck_id is None:
            return

        # abrir por padrão na pasta data do projeto
        project_root = Path(__file__).resolve().parents[2]  # .../flashcards-desktop
        default_dir = project_root / "data"
        start_dir = str(default_dir) if default_dir.exists() else str(Path.home())

        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Selecionar CSV de flashcards",
            start_dir,
            "CSV (*.csv);;Todos os arquivos (*.*)",
        )
        if not file_path:
            return

        try:
            rows = read_cards_from_csv(Path(file_path))
            inserted = self.cards.insert_many(
                self._current_deck_id,
                [(r.number, r.question, r.answer) for r in rows],
            )
        except CsvFormatError as e:
            QtWidgets.QMessageBox.warning(self, "CSV inválido", str(e))
            return
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Erro", f"Falha ao importar.\n\n{e}")
            log.exception("import csv failed")
            return

        QtWidgets.QMessageBox.information(self, "Importação concluída", f"Foram importados {inserted} cards.")
        self._refresh_cards_table()

    # -------------------------
    # Study
    # -------------------------
    def _start_study(self) -> None:
        if self._current_deck_id is None:
            return

        cards = self.cards.list_by_deck(self._current_deck_id)
        if not cards:
            QtWidgets.QMessageBox.information(self, "Sem cards", "Essa pasta ainda não tem cards.")
            return

        self._session = StudySession(cards=cards, shuffle=True)
        self.stack.setCurrentIndex(1)
        self._render_study_card()

    def _on_flashcard_flipped(self, showing_back: bool) -> None:
        """
        Callback quando a animação termina.
        Só habilita as avaliações quando estiver no verso (resposta visível).
        """
        if not self._session:
            return

        if showing_back:
            for b in (self.btn_again, self.btn_hard, self.btn_good, self.btn_easy):
                b.setEnabled(True)
            self.btn_show.setText("Virar para pergunta (Espaço)")
        else:
            for b in (self.btn_again, self.btn_hard, self.btn_good, self.btn_easy):
                b.setEnabled(False)
            self.btn_show.setText("Virar carta (Espaço)")

    def _back_to_list(self) -> None:
        self._session = None
        self.stack.setCurrentIndex(0)
        self.lbl_stats.setText("")
        self._refresh_cards_table()

    def _toggle_answer(self) -> None:
        if not self._session:
            return

        target_back = not self.flashcard.showing_back()

        # enquanto anima, bloqueia as avaliações
        for b in (self.btn_again, self.btn_hard, self.btn_good, self.btn_easy):
            b.setEnabled(False)

        self.flashcard.flip(to_back=target_back)

    def _rate(self, rating: str) -> None:
        if not self._session:
            return
        self._session.rate_and_next(rating)
        self._render_study_card()

    def _render_study_card(self) -> None:
        if not self._session:
            return

        card = self._session.current()
        self.lbl_progress.setText(self._session.progress_text())

        if card is None:
            s = self._session.stats
            self.flashcard.set_content(
                number="",
                front="Sessão finalizada ✅",
                back="Você zerou a pilha de revisão desta pasta.",
            )
            self.flashcard.set_show_back(False)
            self.btn_show.setEnabled(False)
            for b in (self.btn_again, self.btn_hard, self.btn_good, self.btn_easy):
                b.setEnabled(False)
            self.lbl_stats.setText(f"Again: {s.again} | Hard: {s.hard} | Good: {s.good} | Easy: {s.easy}")
            return

        self.btn_show.setEnabled(True)

        numero = "" if card.number is None else str(card.number)
        self.flashcard.set_content(
            number=numero,
            front=card.question,
            back=card.answer,
        )
        self.flashcard.set_show_back(False)

        # rating só quando estiver no verso
        for b in (self.btn_again, self.btn_hard, self.btn_good, self.btn_easy):
            b.setEnabled(False)

        self.btn_show.setText("Virar carta (Espaço)")

        s = self._session.stats
        self.lbl_stats.setText(f"Again: {s.again} | Hard: {s.hard} | Good: {s.good} | Easy: {s.easy}")