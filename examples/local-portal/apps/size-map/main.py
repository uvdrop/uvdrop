"""Size Map — fat folders jump out as a colorful treemap."""
from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QRectF, Qt, QThread, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QLinearGradient
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui_shell import format_steps, maximize_qt

PALETTE = [
    "#FF6B6B", "#FFD93D", "#6BCB77", "#4D96FF", "#C77DFF",
    "#FF8E53", "#00C2A8", "#F72585", "#90E0EF", "#B8F2E6",
]
STEPS = ("フォルダを選ぶ", "地図で確認", "塊をクリックして潜る")


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


@dataclass
class Node:
    name: str
    path: Path
    size: int
    is_dir: bool


def dir_size(path: Path, depth: int = 0, max_depth: int = 8) -> int:
    total = 0
    try:
        for child in path.iterdir():
            try:
                if child.is_symlink():
                    continue
                if child.is_file():
                    total += child.stat().st_size
                elif child.is_dir() and depth < max_depth:
                    total += dir_size(child, depth + 1, max_depth)
            except (OSError, PermissionError):
                continue
    except (OSError, PermissionError):
        return total
    return total


def scan_children(folder: Path) -> list[Node]:
    nodes: list[Node] = []
    try:
        entries = list(folder.iterdir())
    except (OSError, PermissionError) as exc:
        raise RuntimeError(str(exc)) from exc
    for child in entries:
        try:
            if child.is_symlink():
                continue
            if child.is_file():
                nodes.append(Node(child.name, child, child.stat().st_size, False))
            elif child.is_dir():
                nodes.append(Node(child.name + "/", child, dir_size(child), True))
        except (OSError, PermissionError):
            continue
    nodes.sort(key=lambda n: n.size, reverse=True)
    for n in nodes:
        if n.size <= 0:
            n.size = 1
    return nodes


def squarify(nodes: list[Node], rect: QRectF) -> list[tuple[Node, QRectF, str]]:
    """Simple row-based treemap."""
    if not nodes or rect.width() <= 1 or rect.height() <= 1:
        return []
    total = sum(n.size for n in nodes) or 1
    items: list[tuple[Node, QRectF, str]] = []
    x, y = rect.x(), rect.y()
    remaining = list(nodes)
    color_i = 0
    horizontal = rect.width() >= rect.height()

    while remaining:
        # take a row until aspect gets worse
        row: list[Node] = []
        row_size = 0
        side = rect.height() if horizontal else rect.width()
        length = rect.width() if horizontal else rect.height()

        best = None
        for n in remaining:
            trial = row + [n]
            trial_size = row_size + n.size
            row_len = length * (trial_size / total)
            worst = 0.0
            for t in trial:
                h = side * (t.size / trial_size) if trial_size else 0
                if h <= 0 or row_len <= 0:
                    continue
                aspect = max(row_len / h, h / row_len)
                worst = max(worst, aspect)
            if best is None or worst <= best:
                row = trial
                row_size = trial_size
                best = worst
            else:
                break

        row_len = length * (row_size / total)
        cursor = y if not horizontal else x
        for n in row:
            slice_len = side * (n.size / row_size) if row_size else 0
            if horizontal:
                r = QRectF(x, cursor, row_len, slice_len)
                cursor += slice_len
            else:
                r = QRectF(cursor, y, slice_len, row_len)
                cursor += slice_len
            items.append((n, r.adjusted(2, 2, -2, -2), PALETTE[color_i % len(PALETTE)]))
            color_i += 1
            remaining.remove(n)

        if horizontal:
            x += row_len
            rect = QRectF(x, y, max(0, rect.right() - x), rect.height())
        else:
            y += row_len
            rect = QRectF(x, y, rect.width(), max(0, rect.bottom() - y))
        total = sum(n.size for n in remaining) or 1
        horizontal = rect.width() >= rect.height()
    return items


class ScanWorker(QThread):
    done = Signal(list)
    failed = Signal(str)

    def __init__(self, folder: Path) -> None:
        super().__init__()
        self.folder = folder

    def run(self) -> None:
        try:
            self.done.emit(scan_children(self.folder))
        except Exception as exc:  # noqa: BLE001
            self.failed.emit(str(exc))


class TreemapView(QWidget):
    drilled = Signal(Path)

    def __init__(self) -> None:
        super().__init__()
        self.nodes: list[Node] = []
        self.layout_items: list[tuple[Node, QRectF, str]] = []
        self.setMinimumHeight(460)
        self.setMouseTracking(True)
        self._hover: Node | None = None

    def set_nodes(self, nodes: list[Node]) -> None:
        self.nodes = nodes
        self._relayout()
        self.update()

    def resizeEvent(self, event) -> None:  # noqa: N802
        super().resizeEvent(event)
        self._relayout()

    def _relayout(self) -> None:
        self.layout_items = squarify(self.nodes, QRectF(0, 0, self.width(), self.height()))

    def paintEvent(self, _event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0, QColor("#0B1020"))
        grad.setColorAt(1, QColor("#151A2E"))
        p.fillRect(self.rect(), grad)

        if not self.layout_items:
            p.setPen(QColor("#6B7A99"))
            font = QFont("Yu Gothic UI", 16)
            p.setFont(font)
            p.drawText(self.rect(), Qt.AlignCenter, "フォルダを選ぶと、容量の地図がここに広がります")
            return

        for node, rect, color in self.layout_items:
            path = QPainterPath()
            path.addRoundedRect(rect, 14, 14)
            c = QColor(color)
            if self._hover is node:
                c = c.lighter(120)
            p.fillPath(path, c)
            p.setPen(QColor(0, 0, 0, 40))
            p.drawPath(path)

            if rect.width() < 70 or rect.height() < 48:
                continue
            p.setPen(QColor("#101018"))
            title = QFont("Yu Gothic UI", 12, QFont.Bold)
            body = QFont("Yu Gothic UI", 11)
            p.setFont(title)
            name = node.name if len(node.name) < 28 else node.name[:25] + "…"
            p.drawText(rect.adjusted(12, 10, -12, -10), Qt.AlignTop | Qt.AlignLeft, name)
            p.setFont(body)
            p.drawText(rect.adjusted(12, 32, -12, -10), Qt.AlignTop | Qt.AlignLeft, human(node.size))

    def mouseMoveEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        hover = None
        for node, rect, _ in self.layout_items:
            if rect.contains(pos):
                hover = node
                break
        if hover is not self._hover:
            self._hover = hover
            self.update()

    def mousePressEvent(self, event) -> None:  # noqa: N802
        pos = event.position()
        for node, rect, _ in self.layout_items:
            if rect.contains(pos) and node.is_dir:
                self.drilled.emit(node.path)
                return


class SizeMapWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Size Map")
        self.resize(1120, 740)
        self.setStyleSheet(
            """
            QMainWindow, QWidget { background: #0B1020; color: #E8EEFF; }
            QLabel#hero { font-size: 30px; font-weight: 800; color: #FFD93D; }
            QLabel#sub { color: #8FA0C0; font-size: 14px; }
            QPushButton {
                background: #4D96FF; color: white; border: none; border-radius: 14px;
                padding: 12px 20px; font-size: 14px; font-weight: 700;
            }
            QPushButton:hover { background: #6AABFF; }
            QPushButton#ghost {
                background: transparent; border: 1px solid #2A3555; color: #E8EEFF;
            }
            QLabel#steps {
                background: #151A2E; color: #FFD93D; border-radius: 12px;
                padding: 12px 16px; font-size: 13px; font-weight: 700;
            }
            QLabel#status {
                background: #151A2E; color: #E8EEFF; border-radius: 12px;
                padding: 12px 16px; font-size: 14px;
            }
            """
        )
        self.folder: Path | None = None
        self.stack: list[Path] = []
        self.worker: ScanWorker | None = None

        root = QWidget()
        self.setCentralWidget(root)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(12)

        hero = QLabel("Size Map")
        hero.setObjectName("hero")
        layout.addWidget(hero)
        sub = QLabel("全文検索はしない。大きい場所が、地図みたいに一目でわかる。")
        sub.setObjectName("sub")
        layout.addWidget(sub)

        self._steps = QLabel(format_steps(STEPS, 1))
        self._steps.setObjectName("steps")
        layout.addWidget(self._steps)
        self._status = QLabel("次: 「フォルダを選ぶ」— 大きい塊が地図として広がります")
        self._status.setObjectName("status")
        self._status.setWordWrap(True)
        layout.addWidget(self._status)

        top = QHBoxLayout()
        pick = QPushButton("フォルダを選ぶ")
        pick.clicked.connect(self.pick)
        up = QPushButton("一つ上へ")
        up.setObjectName("ghost")
        up.clicked.connect(self.go_up)
        self.path_label = QLabel("未選択")
        self.path_label.setStyleSheet("color:#8FA0C0;")
        top.addWidget(pick)
        top.addWidget(up)
        top.addWidget(self.path_label, stretch=1)
        layout.addLayout(top)

        self.headline = QLabel("一番重いものを、大きく見せる")
        self.headline.setStyleSheet("font-size:22px; font-weight:700; color:#FF6B6B;")
        layout.addWidget(self.headline)

        self.view = TreemapView()
        self.view.drilled.connect(self.drill)
        layout.addWidget(self.view, stretch=1)

    def pick(self) -> None:
        path = QFileDialog.getExistingDirectory(self, "スキャンするフォルダ")
        if path:
            self.stack = [Path(path)]
            self.load(Path(path))

    def go_up(self) -> None:
        if len(self.stack) > 1:
            self.stack.pop()
            self.load(self.stack[-1])
        elif self.folder and self.folder.parent != self.folder:
            parent = self.folder.parent
            self.stack = [parent]
            self.load(parent)

    def drill(self, path: Path) -> None:
        self.stack.append(path)
        self.load(path)

    def load(self, folder: Path) -> None:
        self.folder = folder
        self.path_label.setText(str(folder))
        self._steps.setText(format_steps(STEPS, 2))
        self._status.setText("スキャン中…（大きいフォルダは少し待ちます）")
        self.headline.setText("計測中…")
        if self.worker and self.worker.isRunning():
            self.worker.wait(100)
        self.worker = ScanWorker(folder)
        self.worker.done.connect(self._on_done)
        self.worker.failed.connect(self._on_fail)
        self.worker.start()

    def _on_done(self, nodes: list[Node]) -> None:
        self.view.set_nodes(nodes)
        if not nodes:
            self.headline.setText("中身が空、または読めませんでした")
            self._status.setText("次: 別のフォルダを試してください")
            return
        top = nodes[0]
        self.headline.setText(f"最重量  {top.name}  —  {human(top.size)}")
        total = sum(n.size for n in nodes)
        self._steps.setText(format_steps(STEPS, 3))
        self._status.setText(
            f"{len(nodes)} 項目 ／ 合計 {human(total)} — 次: 色の塊をクリックして中へ潜る"
        )

    def _on_fail(self, msg: str) -> None:
        QMessageBox.warning(self, "読めない", msg)
        self._status.setText(msg)


def main() -> int:
    app = QApplication(sys.argv)
    win = SizeMapWindow()
    win.show()
    maximize_qt(win)
    print("uvdrop-portal-ok size-map", flush=True)
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
