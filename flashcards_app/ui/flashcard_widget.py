from __future__ import annotations

import math
from dataclasses import dataclass

from PySide6 import QtCore, QtGui, QtWidgets


@dataclass(frozen=True)
class FlashcardContent:
    number: str
    front: str
    back: str


class FlashcardWidget(QtWidgets.QWidget):
    """
    Widget desenhado na mão para parecer uma carta (baralho)
    com animação de virada (flip) para mostrar frente/verso.
    """

    flipped = QtCore.Signal(bool)  # True = mostrando verso

    def __init__(self, parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)

        self._content = FlashcardContent(number="", front="", back="")
        self._show_back = False

        # 0.0 -> 1.0 representa o progresso do flip
        self._flip_progress = 0.0
        self._flip_target_back = False
        self._mid_swapped = False

        self._anim = QtCore.QPropertyAnimation(self, b"flipProgress")
        self._anim.setDuration(420)
        self._anim.setEasingCurve(QtCore.QEasingCurve.Type.InOutCubic)
        self._anim.finished.connect(self._on_anim_finished)

        self.setMinimumSize(460, 420)
        self.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)

    def set_content(self, number: str, front: str, back: str) -> None:
        self._content = FlashcardContent(number=number, front=front, back=back)
        self._show_back = False
        self._flip_progress = 0.0
        self.update()

    def showing_back(self) -> bool:
        return self._show_back

    def set_show_back(self, show_back: bool) -> None:
        self._show_back = bool(show_back)
        self._flip_progress = 0.0
        self.update()

    def flip(self, to_back: bool) -> None:
        if self._anim.state() == QtCore.QAbstractAnimation.State.Running:
            return

        self._flip_target_back = bool(to_back)
        self._mid_swapped = False
        self._flip_progress = 0.0

        self._anim.stop()
        self._anim.setStartValue(0.0)
        self._anim.setEndValue(1.0)
        self._anim.start()

    @QtCore.Property(float)
    def flipProgress(self) -> float:
        return float(self._flip_progress)

    @flipProgress.setter
    def flipProgress(self, value: float) -> None:
        self._flip_progress = float(value)

        # troca o conteúdo no “meio” do flip
        if (not self._mid_swapped) and self._flip_progress >= 0.5:
            self._show_back = self._flip_target_back
            self._mid_swapped = True

        self.update()

    def _on_anim_finished(self) -> None:
        # garante estado final consistente
        self._flip_progress = 0.0
        self._mid_swapped = False
        self.update()
        self.flipped.emit(self._show_back)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.RenderHint.TextAntialiasing, True)

        w = self.width()
        h = self.height()

        # Carta: proporção aproximada de baralho (poker): width/height ~ 0.714
        ratio = 0.72
        max_w = w * 0.92
        max_h = h * 0.92

        card_w = min(max_w, max_h * ratio)
        card_h = card_w / ratio
        if card_h > max_h:
            card_h = max_h
            card_w = card_h * ratio

        rect = QtCore.QRectF((w - card_w) / 2, (h - card_h) / 2, card_w, card_h)
        radius = min(card_w, card_h) * 0.06

        # Flip: escala horizontal simulando rotação no eixo Y
        # cos(pi * t) vai de 1 -> 0 -> -1 (usamos abs para escala)
        t = self._flip_progress
        scale_x = abs(math.cos(math.pi * t))
        scale_x = max(scale_x, 0.03)  # evita sumir totalmente

        # Perspectiva leve (efeito “3D” fake, mas bonito)
        skew = math.sin(math.pi * t) * 0.06

        painter.save()
        cx = rect.center().x()
        cy = rect.center().y()
        painter.translate(cx, cy)
        transform = QtGui.QTransform()
        transform.shear(skew if math.cos(math.pi * t) >= 0 else -skew, 0.0)
        painter.setTransform(transform, True)
        painter.scale(scale_x, 1.0)
        painter.translate(-cx, -cy)

        # sombra (desenhada)
        shadow_rect = rect.translated(0, 8)
        shadow_path = QtGui.QPainterPath()
        shadow_path.addRoundedRect(shadow_rect, radius, radius)
        painter.fillPath(shadow_path, QtGui.QColor(0, 0, 0, 110))

        # fundo e borda (frente/verso com estilos diferentes)
        card_path = QtGui.QPainterPath()
        card_path.addRoundedRect(rect, radius, radius)

        if self._show_back:
            grad = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
            grad.setColorAt(0.0, QtGui.QColor("#1a2140"))
            grad.setColorAt(1.0, QtGui.QColor("#12162b"))
            border = QtGui.QColor("#3c4ea0")
            accent = QtGui.QColor("#9fb0ff")
        else:
            grad = QtGui.QLinearGradient(rect.topLeft(), rect.bottomRight())
            grad.setColorAt(0.0, QtGui.QColor("#1b1f33"))
            grad.setColorAt(1.0, QtGui.QColor("#0f111a"))
            border = QtGui.QColor("#2a2f45")
            accent = QtGui.QColor("#e6e6e6")

        painter.fillPath(card_path, QtGui.QBrush(grad))
        pen = QtGui.QPen(border)
        pen.setWidthF(2.0)
        painter.setPen(pen)
        painter.drawPath(card_path)

        # faixa superior sutil (estilo “carta premium”)
        top_band = QtCore.QRectF(rect.left(), rect.top(), rect.width(), rect.height() * 0.14)
        band_path = QtGui.QPainterPath()
        band_path.addRoundedRect(top_band, radius, radius)
        painter.fillPath(band_path, QtGui.QColor(255, 255, 255, 18))

        # número (canto superior esquerdo)
        num = self._content.number.strip()
        if num:
            painter.setPen(QtGui.QColor(255, 255, 255, 160))
            font = painter.font()
            font.setPointSize(12)
            font.setBold(True)
            painter.setFont(font)
            painter.drawText(
                QtCore.QRectF(rect.left() + 18, rect.top() + 14, rect.width() * 0.4, 30),
                QtCore.Qt.AlignmentFlag.AlignLeft | QtCore.Qt.AlignmentFlag.AlignVCenter,
                f"#{num}",
            )

        # Título (FRONT / BACK)
        painter.setPen(QtGui.QColor(255, 255, 255, 160))
        font = painter.font()
        font.setPointSize(11)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(
            QtCore.QRectF(rect.left(), rect.top() + 12, rect.width(), 30),
            QtCore.Qt.AlignmentFlag.AlignHCenter | QtCore.Qt.AlignmentFlag.AlignVCenter,
            "RESPOSTA" if self._show_back else "PERGUNTA",
        )

        # texto principal
        pad = rect.width() * 0.08
        text_rect = rect.adjusted(pad, rect.height() * 0.20, -pad, -pad)

        text = self._content.back if self._show_back else self._content.front
        painter.setPen(accent)

        # fonte adaptativa simples (quanto maior o texto, menor a fonte)
        base = 18
        if len(text) > 220:
            base = 13
        elif len(text) > 140:
            base = 15
        elif len(text) > 80:
            base = 16

        font = painter.font()
        font.setPointSize(base)
        font.setBold(False)
        painter.setFont(font)

        option = QtGui.QTextOption()
        option.setWrapMode(QtGui.QTextOption.WrapMode.WordWrap)
        option.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)

        painter.drawText(text_rect, text, option)

        painter.restore()