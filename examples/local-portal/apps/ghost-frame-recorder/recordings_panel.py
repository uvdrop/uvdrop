"""Companion panel listing recorded takes."""
from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class RecordingsPanel(QDockWidget):
    def __init__(self, output_dir: Path, parent: QMainWindow | None = None) -> None:
        super().__init__("録画一覧", parent)
        self.output_dir = output_dir
        self.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)

        container = QWidget()
        layout = QVBoxLayout(container)

        self.path_label = QLabel(str(output_dir))
        self.path_label.setWordWrap(True)
        layout.addWidget(self.path_label)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        row = QHBoxLayout()
        self.btn_refresh = QPushButton("更新")
        self.btn_rename = QPushButton("名前変更")
        self.btn_delete = QPushButton("削除")
        self.btn_open = QPushButton("フォルダを開く")
        self.btn_save_as = QPushButton("名前を付けて保存")
        for btn in (self.btn_refresh, self.btn_rename, self.btn_delete, self.btn_open, self.btn_save_as):
            row.addWidget(btn)
        layout.addLayout(row)

        self.setWidget(container)

        self.btn_refresh.clicked.connect(self.refresh)
        self.btn_rename.clicked.connect(self.rename_selected)
        self.btn_delete.clicked.connect(self.delete_selected)
        self.btn_open.clicked.connect(self.open_folder)
        self.btn_save_as.clicked.connect(self.save_as_copy)

        self.refresh()

    def refresh(self) -> None:
        self.list_widget.clear()
        if not self.output_dir.exists():
            return
        files = sorted(
            (
                p
                for p in self.output_dir.iterdir()
                if p.suffix.lower() in {".mp4", ".wav", ".avi"}
            ),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        for path in files:
            item = QListWidgetItem(path.name)
            item.setData(Qt.UserRole, str(path))
            self.list_widget.addItem(item)

    def add_take(self, path: str) -> None:
        item = QListWidgetItem(Path(path).name)
        item.setData(Qt.UserRole, path)
        self.list_widget.insertItem(0, item)

    def _selected_path(self) -> Path | None:
        item = self.list_widget.currentItem()
        if item is None:
            return None
        return Path(item.data(Qt.UserRole))

    def rename_selected(self) -> None:
        path = self._selected_path()
        if path is None:
            return
        stem = path.stem
        new_stem, ok = _prompt_text(None, "名前変更", "新しいファイル名（拡張子なし）:", stem)
        if not ok or not new_stem.strip():
            return
        target = path.with_name(new_stem.strip() + path.suffix)
        if target.exists():
            QMessageBox.warning(self, "名前変更", "同名ファイルが既にあります。")
            return
        path.rename(target)
        self.refresh()

    def delete_selected(self) -> None:
        path = self._selected_path()
        if path is None:
            return
        answer = QMessageBox.question(self, "削除", f"{path.name} を削除しますか？")
        if answer != QMessageBox.Yes:
            return
        path.unlink(missing_ok=True)
        # remove sidecars with same stem
        for sibling in path.parent.glob(path.stem + ".*"):
            if sibling != path:
                sibling.unlink(missing_ok=True)
        self.refresh()

    def open_folder(self) -> None:
        import os
        import subprocess

        self.output_dir.mkdir(parents=True, exist_ok=True)
        if hasattr(os, "startfile"):
            os.startfile(self.output_dir)  # type: ignore[attr-defined]
        else:
            subprocess.run(["xdg-open", str(self.output_dir)], check=False)

    def save_as_copy(self) -> None:
        path = self._selected_path()
        if path is None:
            return
        dest, _ = QFileDialog.getSaveFileName(self, "名前を付けて保存", str(path))
        if not dest:
            return
        shutil.copy2(path, dest)


def _prompt_text(parent, title: str, label: str, text: str):  # noqa: ANN001
    from PySide6.QtWidgets import QInputDialog

    return QInputDialog.getText(parent, title, label, text=text)
