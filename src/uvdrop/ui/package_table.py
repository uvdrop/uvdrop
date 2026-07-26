"""Spreadsheet-style grid for package allow / block lists.

Behaves like a small worksheet: click a cell to edit, Tab / Enter to move,
Ctrl+A for select-all, and Ctrl+V to paste a block copied out of Excel
(extra rows are created automatically — even for 1000+ lines).
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk

from uvdrop.i18n import t
from uvdrop.package_spec import (
    PackageRule,
    describe_rule,
    parse_pasted_table,
    validate_rule,
)

COLUMNS = ("name", "version")

_EDIT_IGNORED_KEYS = {
    "Shift_L",
    "Shift_R",
    "Control_L",
    "Control_R",
    "Alt_L",
    "Alt_R",
    "Caps_Lock",
    "Escape",
    "Tab",
    "Return",
    "Up",
    "Down",
    "Left",
    "Right",
    "Prior",
    "Next",
    "Home",
    "End",
}


class PackageSheet(ttk.Frame):
    """Editable two-column sheet returning `PackageRule` rows."""

    MIN_ROWS = 8

    def __init__(
        self,
        master: tk.Misc,
        *,
        ui_font: str = "Segoe UI",
        mono_font: str = "Consolas",
        rows: int = 8,
        on_help: object | None = None,
    ) -> None:
        super().__init__(master)
        self.ui_font = ui_font
        self.mono_font = mono_font
        self.MIN_ROWS = max(4, rows)
        self._editor: ttk.Entry | None = None
        self._edit_cell: tuple[str, str] | None = None
        self._focus_col = "name"
        self._on_help = on_help

        style = ttk.Style(self)
        style.configure("Sheet.Treeview", rowheight=26, font=(mono_font, 10))
        style.configure("Sheet.Treeview.Heading", font=(ui_font, 10, "bold"))

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=tk.X)
        ttk.Button(toolbar, text=t("sheet.add_row"), command=self._append_row_and_focus).pack(
            side=tk.LEFT
        )
        ttk.Button(toolbar, text=t("sheet.del_row"), command=self.delete_selected).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        ttk.Button(toolbar, text=t("sheet.select_all"), command=self.select_all).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        ttk.Button(toolbar, text=t("sheet.paste"), command=self.paste_clipboard).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        ttk.Button(toolbar, text=t("sheet.copy"), command=self.copy_selection).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        ttk.Button(toolbar, text=t("sheet.clear_all"), command=self.clear_all).pack(
            side=tk.LEFT, padx=(6, 0)
        )
        if on_help is not None:
            ttk.Button(toolbar, text=t("sheet.version_guide"), command=on_help).pack(  # type: ignore[arg-type]
                side=tk.RIGHT
            )

        wrap = ttk.Frame(self)
        wrap.pack(fill=tk.BOTH, expand=True, pady=(6, 0))
        self.tree = ttk.Treeview(
            wrap,
            columns=COLUMNS,
            show="tree headings",
            height=rows,
            selectmode="extended",
            style="Sheet.Treeview",
        )
        self.tree.heading("#0", text="")
        self.tree.column("#0", width=48, minwidth=42, stretch=False, anchor=tk.E)
        self.tree.heading("name", text=t("sheet.col_name"))
        self.tree.column("name", width=230, minwidth=140, stretch=True)
        self.tree.heading("version", text=t("sheet.col_version"))
        self.tree.column("version", width=170, minwidth=110, stretch=False)
        self.tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        scroll = ttk.Scrollbar(wrap, orient=tk.VERTICAL, command=self.tree.yview)
        scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.tag_configure("odd", background="#f6f9f7")
        self.tree.tag_configure("bad", foreground="#a3392b")

        self._status = tk.StringVar(value=t("sheet.hint"))
        ttk.Label(
            self,
            textvariable=self._status,
            foreground="#69796f",
            wraplength=520,
            justify=tk.LEFT,
        ).pack(anchor=tk.W, pady=(6, 0))

        self.tree.bind("<Button-1>", self._on_click)
        self.tree.bind("<Double-1>", self._on_double_click)
        self.tree.bind("<Return>", self._on_return)
        self.tree.bind("<Tab>", self._on_tab)
        self.tree.bind("<Delete>", self._on_delete)
        self.tree.bind("<BackSpace>", self._on_backspace)
        self.tree.bind("<Key>", self._on_key)
        self.tree.bind("<Control-a>", lambda _e: (self.select_all(), "break")[1])
        self.tree.bind("<Control-A>", lambda _e: (self.select_all(), "break")[1])
        self.tree.bind("<Control-v>", lambda _e: (self.paste_clipboard(), "break")[1])
        self.tree.bind("<Control-V>", lambda _e: (self.paste_clipboard(), "break")[1])
        self.tree.bind("<Control-c>", lambda _e: (self.copy_selection(), "break")[1])
        self.tree.bind("<Control-C>", lambda _e: (self.copy_selection(), "break")[1])
        self.tree.bind("<<TreeviewSelect>>", lambda _e: self._update_status())

        self._ensure_min_rows()

    # --- rows -------------------------------------------------------------

    def _items(self) -> list[str]:
        return list(self.tree.get_children())

    def _renumber(self) -> None:
        for i, item in enumerate(self._items(), start=1):
            tags: tuple[str, ...] = ("odd",) if i % 2 else ()
            name, version = (list(self.tree.item(item, "values")) + ["", ""])[:2]
            if str(name).strip() and not validate_rule(str(version)).ok:
                tags = tags + ("bad",)
            self.tree.item(item, text=str(i), tags=tags)

    def problems(self) -> list[str]:
        """Rows whose version rule uvdrop cannot use, as readable messages."""
        out: list[str] = []
        for item in self._items():
            name, version = (list(self.tree.item(item, "values")) + ["", ""])[:2]
            name, version = str(name).strip(), str(version).strip()
            if not name:
                continue
            check = validate_rule(version)
            if not check.ok:
                out.append(f"{name}: {version} — {check.message}")
        return out

    def _update_status(self) -> None:
        bad = self.problems()
        if bad:
            head = (
                bad[0]
                if len(bad) == 1
                else t("sheet.bad_more", first=bad[0], n=len(bad) - 1)
            )
            self._status.set(t("sheet.bad_rules", head=head))
            return
        item = self._current_item()
        if item:
            version = self._cell_value(item, "version")
            name = self._cell_value(item, "name").strip()
            if name:
                self._status.set(f"{name}: {describe_rule(version)}")
                return
        self._status.set(
            t("sheet.hint")
        )

    def _insert_blank(self) -> str:
        return self.tree.insert("", tk.END, values=("", ""))

    def append_row(self, name: str = "", version: str = "") -> str:
        item = self.tree.insert("", tk.END, values=(name, version))
        self._renumber()
        return item

    def _append_row_and_focus(self) -> None:
        item = self.append_row()
        self.tree.selection_set(item)
        self.tree.focus(item)
        self.tree.see(item)
        self._focus_col = "name"
        self._begin_edit(item, "name")

    def _ensure_min_rows(self) -> None:
        while len(self._items()) < self.MIN_ROWS:
            self._insert_blank()
        self._renumber()

    def _ensure_capacity(self, count: int) -> None:
        """Grow the sheet so it has at least `count` rows (no renumber yet)."""
        missing = count - len(self._items())
        for _ in range(max(0, missing)):
            self._insert_blank()

    def _is_blank(self, item: str) -> bool:
        return not any(str(v).strip() for v in self.tree.item(item, "values"))

    def select_all(self) -> None:
        self._commit_edit()
        items = [i for i in self._items() if not self._is_blank(i)] or self._items()
        if items:
            self.tree.selection_set(items)
            self.tree.focus(items[0])
            self.tree.see(items[0])

    def delete_selected(self) -> None:
        self._cancel_edit()
        selected = list(self.tree.selection())
        if not selected:
            return
        for item in selected:
            self.tree.delete(item)
        self._ensure_min_rows()
        self._renumber()

    def clear_all(self) -> None:
        self._cancel_edit()
        for item in self._items():
            self.tree.delete(item)
        self._ensure_min_rows()

    # --- public API -------------------------------------------------------

    def set_rules(self, rules: list[PackageRule]) -> None:
        self._cancel_edit()
        for item in self._items():
            self.tree.delete(item)
        for rule in rules:
            self.tree.insert("", tk.END, values=(rule.name, rule.version or "*"))
        self._ensure_min_rows()

    def get_rules(self) -> list[PackageRule]:
        self._commit_edit()
        out: list[PackageRule] = []
        seen: set[str] = set()
        for item in self._items():
            name, version = (list(self.tree.item(item, "values")) + ["", ""])[:2]
            rule = PackageRule(name=str(name), version=str(version)).normalized()
            if not rule.name or rule.name in seen:
                continue
            seen.add(rule.name)
            out.append(rule)
        return out

    def add_row(self, name: str = "", version: str = "*") -> None:
        self.append_row(name, version)

    # --- clipboard --------------------------------------------------------

    def copy_all(self) -> None:
        self.copy_selection(prefer_all=True)

    def copy_selection(self, *, prefer_all: bool = False) -> None:
        self._commit_edit()
        selected = list(self.tree.selection())
        if prefer_all or not selected:
            targets = [i for i in self._items() if not self._is_blank(i)]
        else:
            targets = [i for i in selected if not self._is_blank(i)]
            if not targets:
                targets = [i for i in self._items() if not self._is_blank(i)]
        lines = ["\t".join(str(v) for v in self.tree.item(item, "values")) for item in targets]
        self.clipboard_clear()
        self.clipboard_append("\n".join(lines))

    def paste_clipboard(self) -> None:
        try:
            text = self.clipboard_get()
        except tk.TclError:
            return
        self.paste_text(text)

    def paste_text(self, text: str) -> None:
        """Fill cells from a spreadsheet block, starting at the active cell.

        Missing rows are created automatically (safe for large pastes).
        """
        rows = parse_pasted_table(text)
        if not rows:
            return
        self._cancel_edit()

        items = self._items()
        selection = self.tree.selection()
        if selection:
            start_index = items.index(selection[0])
        else:
            start_index = 0
            for i, item in enumerate(items):
                if self._is_blank(item):
                    start_index = i
                    break
            else:
                start_index = len(items)

        start_col = COLUMNS.index(self._focus_col) if self._focus_col in COLUMNS else 0
        needed = start_index + len(rows)
        self._ensure_capacity(needed)
        items = self._items()

        pasted_ids: list[str] = []
        for offset, cells in enumerate(rows):
            item = items[start_index + offset]
            values = (list(self.tree.item(item, "values")) + ["", ""])[:2]
            for col_offset, value in enumerate(cells):
                col_index = start_col + col_offset
                if col_index < len(COLUMNS):
                    values[col_index] = value
            self.tree.item(item, values=tuple(values))
            pasted_ids.append(item)

        self._ensure_min_rows()
        self._renumber()
        self._update_status()
        if pasted_ids:
            self.tree.selection_set(pasted_ids)
            self.tree.focus(pasted_ids[0])
            self.tree.see(pasted_ids[-1])
            self.tree.see(pasted_ids[0])

    # --- editing ----------------------------------------------------------

    def _cell_value(self, item: str, column: str) -> str:
        values = (list(self.tree.item(item, "values")) + ["", ""])[:2]
        return str(values[COLUMNS.index(column)])

    def _set_cell(self, item: str, column: str, value: str) -> None:
        values = (list(self.tree.item(item, "values")) + ["", ""])[:2]
        values[COLUMNS.index(column)] = value
        self.tree.item(item, values=tuple(values))

    def _begin_edit(self, item: str, column: str, initial: str | None = None) -> None:
        self._commit_edit()
        self.tree.selection_set(item)
        self.tree.focus(item)
        self.tree.see(item)
        self.update_idletasks()
        col_id = f"#{COLUMNS.index(column) + 1}"
        bbox = self.tree.bbox(item, col_id)
        if not bbox:
            return
        x, y, w, h = bbox
        editor = ttk.Entry(self.tree, font=(self.mono_font, 10))
        editor.place(x=x, y=y, width=w, height=h)
        editor.insert(0, initial if initial is not None else self._cell_value(item, column))
        editor.select_range(0, tk.END)
        editor.icursor(tk.END)
        editor.focus_set()
        editor.bind("<Return>", lambda _e: self._finish_edit(move="down"))
        editor.bind("<Tab>", lambda _e: self._finish_edit(move="right"))
        editor.bind("<Escape>", lambda _e: self._cancel_edit_and_focus())
        editor.bind("<FocusOut>", lambda _e: self._commit_edit())
        self._editor = editor
        self._edit_cell = (item, column)
        self._focus_col = column

    def _commit_edit(self) -> None:
        if self._editor is None or self._edit_cell is None:
            return
        item, column = self._edit_cell
        value = self._editor.get().strip()
        editor, self._editor, self._edit_cell = self._editor, None, None
        editor.destroy()
        if self.tree.exists(item):
            self._set_cell(item, column, value)
            self._renumber()
            self._update_status()

    def _cancel_edit(self) -> None:
        if self._editor is None:
            return
        editor, self._editor, self._edit_cell = self._editor, None, None
        editor.destroy()

    def _cancel_edit_and_focus(self) -> str:
        self._cancel_edit()
        self.tree.focus_set()
        return "break"

    def _finish_edit(self, *, move: str) -> str:
        cell = self._edit_cell
        self._commit_edit()
        self.tree.focus_set()
        if cell is None:
            return "break"
        item, column = cell
        if move == "right":
            index = COLUMNS.index(column)
            if index + 1 < len(COLUMNS):
                self._begin_edit(item, COLUMNS[index + 1])
                return "break"
            column = COLUMNS[0]
            move = "down"
        if move == "down":
            items = self._items()
            if item in items:
                nxt = items.index(item) + 1
                if nxt >= len(items):
                    self.append_row()
                    items = self._items()
                target = items[nxt]
                self._begin_edit(target, column)
        return "break"

    # --- events -----------------------------------------------------------

    def _on_click(self, event: tk.Event) -> None:
        self._commit_edit()
        column = self.tree.identify_column(event.x)
        if column in ("#1", "#2"):
            self._focus_col = COLUMNS[int(column[1:]) - 1]

    def _on_double_click(self, event: tk.Event) -> str | None:
        item = self.tree.identify_row(event.y)
        column = self.tree.identify_column(event.x)
        if not item or column not in ("#1", "#2"):
            return None
        self._begin_edit(item, COLUMNS[int(column[1:]) - 1])
        return "break"

    def _current_item(self) -> str | None:
        focus = self.tree.focus()
        if focus and self.tree.exists(focus):
            return focus
        selection = self.tree.selection()
        if selection:
            return selection[0]
        items = self._items()
        return items[0] if items else None

    def _on_return(self, _event: tk.Event) -> str:
        item = self._current_item()
        if item:
            self._begin_edit(item, self._focus_col)
        return "break"

    def _on_tab(self, _event: tk.Event) -> str:
        item = self._current_item()
        if item:
            index = COLUMNS.index(self._focus_col)
            self._focus_col = COLUMNS[(index + 1) % len(COLUMNS)]
            self._begin_edit(item, self._focus_col)
        return "break"

    def _on_delete(self, _event: tk.Event) -> str:
        # Multi-row delete; single row clears the focused cell (Excel-ish).
        selected = list(self.tree.selection())
        if len(selected) > 1:
            self.delete_selected()
        elif selected:
            self._set_cell(selected[0], self._focus_col, "")
        return "break"

    def _on_backspace(self, _event: tk.Event) -> str:
        for item in self.tree.selection():
            self._set_cell(item, self._focus_col, "")
        return "break"

    def _on_key(self, event: tk.Event) -> str | None:
        if event.state & 0x4:  # Control held — leave shortcuts alone
            return None
        if event.keysym in _EDIT_IGNORED_KEYS or not event.char or not event.char.isprintable():
            return None
        item = self._current_item()
        if not item:
            return None
        self._begin_edit(item, self._focus_col, initial=event.char)
        return "break"


PackageTable = PackageSheet
