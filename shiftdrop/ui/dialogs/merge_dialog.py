"""
Merge Dialog: Drag-and-drop file reordering before combining multiple PDFs or images into one.
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt

class MergeDialog(QDialog):
    def __init__(self, file_paths: list[str], parent=None):
        super().__init__(parent)
        self.file_paths = file_paths
        self.setWindowTitle("📑 Ordenar Archivos para Combinar")
        self.setFixedSize(460, 340)
        self.setStyleSheet("""
            QDialog {
                background-color: #121824;
                color: #FFFFFF;
                border: 1px solid #2B384E;
                border-radius: 10px;
            }
            QLabel {
                color: #DDE5ED;
            }
            QListWidget {
                background-color: #1A2232;
                border: 1px solid #2F3E57;
                border-radius: 8px;
                color: #FFFFFF;
                padding: 6px;
            }
            QListWidget::item {
                padding: 8px 10px;
                border-radius: 4px;
                margin-bottom: 2px;
                background-color: #232D42;
            }
            QListWidget::item:selected {
                background-color: #00E676;
                color: #0B1A12;
                font-weight: bold;
            }
            QPushButton.toolBtn {
                background-color: #242E40;
                color: #CAD6E2;
                border: 1px solid #3B4B66;
                border-radius: 6px;
                padding: 6px 12px;
                font-weight: bold;
            }
            QPushButton.toolBtn:hover {
                background-color: #313E57;
                color: #FFFFFF;
            }
            QPushButton#actionBtn {
                background-color: #00E676;
                color: #081B10;
                font-weight: bold;
                border-radius: 6px;
                padding: 8px 16px;
            }
            QPushButton#actionBtn:hover {
                background-color: #33EC8F;
            }
            QPushButton#cancelBtn {
                background-color: #242E40;
                color: #A0B0C4;
                border-radius: 6px;
                padding: 8px 16px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        info = QLabel("<b>Arrastra los archivos o usa los botones para definir el orden final:</b>")
        info.setWordWrap(True)
        layout.addWidget(info)

        # File List
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QListWidget.DragDropMode.InternalMove)
        for p in self.file_paths:
            path_obj = Path(p)
            item = QListWidgetItem(f"📄  {path_obj.name}")
            item.setData(Qt.ItemDataRole.UserRole, str(path_obj))
            self.list_widget.addItem(item)
        layout.addWidget(self.list_widget)

        # Reorder buttons
        tools_layout = QHBoxLayout()
        up_btn = QPushButton("▲ Subir")
        up_btn.setProperty("class", "toolBtn")
        up_btn.clicked.connect(self._move_up)

        down_btn = QPushButton("▼ Bajar")
        down_btn.setProperty("class", "toolBtn")
        down_btn.clicked.connect(self._move_down)

        del_btn = QPushButton("✕ Quitar")
        del_btn.setProperty("class", "toolBtn")
        del_btn.clicked.connect(self._remove_item)

        tools_layout.addWidget(up_btn)
        tools_layout.addWidget(down_btn)
        tools_layout.addWidget(del_btn)
        tools_layout.addStretch()
        layout.addLayout(tools_layout)

        # Actions
        btn_layout = QHBoxLayout()
        cancel_btn = QPushButton("Cancelar")
        cancel_btn.setObjectName("cancelBtn")
        cancel_btn.clicked.connect(self.reject)

        merge_btn = QPushButton("Combinar Todo 📑")
        merge_btn.setObjectName("actionBtn")
        merge_btn.clicked.connect(self.accept)

        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(merge_btn)
        layout.addLayout(btn_layout)

    def _move_up(self):
        row = self.list_widget.currentRow()
        if row > 0:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row - 1, item)
            self.list_widget.setCurrentRow(row - 1)

    def _move_down(self):
        row = self.list_widget.currentRow()
        if 0 <= row < self.list_widget.count() - 1:
            item = self.list_widget.takeItem(row)
            self.list_widget.insertItem(row + 1, item)
            self.list_widget.setCurrentRow(row + 1)

    def _remove_item(self):
        row = self.list_widget.currentRow()
        if row >= 0:
            self.list_widget.takeItem(row)

    def get_ordered_files(self) -> list[str]:
        ordered = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            ordered.append(item.data(Qt.ItemDataRole.UserRole))
        return ordered
