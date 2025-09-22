import os, threading
from typing import List
from PySide6.QtCore import Qt, Signal, QObject, QEvent, QPoint, QRect
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFileDialog, QRadioButton,
    QProgressBar, QApplication, QTextBrowser, QDialog, QSizePolicy
)

from processor import ImageProcessor
from utils import (
    build_qss, apply_drop_shadow, GAP_DEFAULT, PADDING_CARD,
    try_icon_path, SUPPORTED_EXTENSIONS
)


# 内部シグナル（バックグラウンド処理→UI）

class _Signals(QObject):
    progress = Signal(float)   # 0.0 - 1.0
    status  = Signal(str)
    done    = Signal(bool)


class DropArea(QLabel):
    filesDropped = Signal(list)  # List[str]

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("dropArea")
        self.setText("ここにファイルやフォルダをドラッグ＆ドロップ")
        self.setAlignment(Qt.AlignCenter)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()

    def dropEvent(self, e):
        files = [u.toLocalFile() for u in e.mimeData().urls()]
        if files:
            # 親を直接呼ばず、シグナルで通知（親の種類に依存しない）
            self.filesDropped.emit(files)


# README ダイアログ

README_MD = r"""
# 画像変換＆分割ツール ©️2025 KisaragiIchigo
- 画像を左右で **1/2分割** して `_a`, `_b` 付きで保存するよ
- 複数ファイル/フォルダを **D&D** または **選択ボタン** で投入
- 進捗バーで処理状況を表示
- 出力先は **最初の入力画像と同階層の `half/`** フォルダ

## 使い方
1. 画像ファイル or フォルダを投入  
2. 分割方向「右→左」or「左→右」を選ぶ  
3. 完了したら `half/` をチェック！

"""

class ReadmeDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("README ©️2025 KisaragiIchigo")
        self.setWindowFlags(Qt.Dialog | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setMinimumSize(520, 360)
        self.resize(680, 520)

        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0)
        bg = QWidget(); bg.setObjectName("bgRoot"); outer.addWidget(bg)

        lay_bg = QVBoxLayout(bg); lay_bg.setContentsMargins(GAP_DEFAULT, GAP_DEFAULT, GAP_DEFAULT, GAP_DEFAULT)
        card = QWidget(); card.setObjectName("glassRoot"); lay_bg.addWidget(card)
        apply_drop_shadow(card)

        v = QVBoxLayout(card); v.setContentsMargins(PADDING_CARD, PADDING_CARD, PADDING_CARD, PADDING_CARD); v.setSpacing(GAP_DEFAULT)

        title_row = QHBoxLayout()
        title = QLabel("README"); title.setObjectName("titleLabel")
        title_row.addWidget(title); title_row.addStretch(1)
        btn_close = QPushButton("閉じる"); btn_close.clicked.connect(self.accept)
        title_row.addWidget(btn_close)
        v.addLayout(title_row)

        body = QTextBrowser()
        body.setObjectName("readmeText")
        body.setMarkdown(README_MD)
        body.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        v.addWidget(body)

        # ドラッグ移動
        self._dragging = False
        self._drag_offset = QPoint()
        for host in (bg, card, title):
            host.installEventFilter(self)

        self._apply_compact(self.isMaximized())

    def _apply_compact(self, compact: bool):
        self.setStyleSheet(build_qss(compact))

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == QEvent.WindowStateChange:
            self._apply_compact(self.isMaximized())

    def eventFilter(self, obj, e):
        if e.type() == QEvent.MouseButtonPress and e.button() == Qt.LeftButton:
            self._dragging = True
            self._drag_offset = e.globalPosition().toPoint() - self.frameGeometry().topLeft()
            return True
        if e.type() == QEvent.MouseMove and self._dragging and (e.buttons() & Qt.LeftButton):
            self.move(e.globalPosition().toPoint() - self._drag_offset)
            return True
        if e.type() == QEvent.MouseButtonRelease:
            self._dragging = False
            return True
        return super().eventFilter(obj, e)


# メインウィンドウ

class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("画像変換＆分割ツール ©️2025 KisaragiIchigo")
        self.setWindowFlags(Qt.FramelessWindowHint)       # #説明: フレームレス
        self.setAttribute(Qt.WA_TranslucentBackground)    # #説明: 背景透過
        self.resize(720, 520)
        self.setMinimumSize(600, 400)

        ip = try_icon_path("pst.ico", "app.ico")
        if ip:
            self.setWindowIcon(QIcon(ip))

        # 信号
        self.signals = _Signals()
        self.signals.progress.connect(self._on_progress)
        self.signals.status.connect(self._on_status)
        self.signals.done.connect(self._on_done)

        # Processor（コールバックはsignalsへ橋渡し）
        self.processor = ImageProcessor(
            progress_callback=self.signals.progress.emit,
            status_callback=self.signals.status.emit,
            done_callback=self.signals.done.emit
        )

        # 最背面ガラス
        outer = QVBoxLayout(self); outer.setContentsMargins(0,0,0,0)
        self._bg = QWidget(); self._bg.setObjectName("bgRoot"); outer.addWidget(self._bg)

        lay_bg = QVBoxLayout(self._bg); lay_bg.setContentsMargins(GAP_DEFAULT, GAP_DEFAULT, GAP_DEFAULT, GAP_DEFAULT)
        self._card = QWidget(); self._card.setObjectName("glassRoot"); lay_bg.addWidget(self._card)
        self._shadow = apply_drop_shadow(self._card)

        # カード内レイアウト
        v = QVBoxLayout(self._card); v.setContentsMargins(PADDING_CARD, PADDING_CARD, PADDING_CARD, PADDING_CARD); v.setSpacing(GAP_DEFAULT)

        # タイトルバー（左:タイトル / 右:操作）
        bar = QHBoxLayout()
        self._title = QLabel("画像変換＆分割ツール"); self._title.setObjectName("titleLabel")
        bar.addWidget(self._title); bar.addStretch(1)
        self._btn_menu  = QPushButton("README"); self._btn_menu.clicked.connect(self._open_readme)
        self._btn_min   = QPushButton("🗕"); self._btn_min.setFixedSize(28,28); self._btn_min.clicked.connect(self.showMinimized)
        self._btn_max   = QPushButton("🗖"); self._btn_max.setFixedSize(28,28); self._btn_max.clicked.connect(self._toggle_max_restore)
        self._btn_close = QPushButton("ｘ"); self._btn_close.setFixedSize(28,28); self._btn_close.clicked.connect(self.close)
        for b in (self._btn_menu, self._btn_min, self._btn_max, self._btn_close):
            bar.addWidget(b)
        v.addLayout(bar)

        # D&Dエリア（★シグナル接続）
        self.drop = DropArea(self._card)  # 親はカードでもOK（親直呼びしないので問題なし）
        self.drop.setFixedHeight(120)
        self.drop.filesDropped.connect(self.start_processing)
        v.addWidget(self.drop)

        # 分割方向
        row_dir = QHBoxLayout()
        row_dir.addWidget(QLabel("分割方向: "))
        self.rb_r2l = QRadioButton("右 → 左"); self.rb_r2l.setChecked(True)
        self.rb_l2r = QRadioButton("左 → 右")
        row_dir.addWidget(self.rb_r2l); row_dir.addWidget(self.rb_l2r)
        row_dir.addStretch(1)
        v.addLayout(row_dir)

        # ボタン列
        row_btn = QHBoxLayout()
        self.btn_pick_files = QPushButton("ファイル選択")
        self.btn_pick_dir   = QPushButton("フォルダ選択")
        self.btn_run_demo   = QPushButton("READMEを表示")
        self.btn_pick_files.clicked.connect(self._pick_files)
        self.btn_pick_dir.clicked.connect(self._pick_dir)
        self.btn_run_demo.clicked.connect(self._open_readme)
        row_btn.addWidget(self.btn_pick_files); row_btn.addWidget(self.btn_pick_dir); row_btn.addWidget(self.btn_run_demo)
        v.addLayout(row_btn)

        # 進捗エリア
        self.progress = QProgressBar(); self.progress.setRange(0,100); self.progress.setValue(0)
        v.addWidget(self.progress)
        self.status = QLabel("準備完了"); self.status.setObjectName("textPanel")
        v.addWidget(self.status)

        # フレームレスのドラッグ/リサイズ
        self._dragging = False
        self._drag_offset = QPoint()
        self._resizing = False
        self._resize_edges = ""
        for host in (self._bg, self._card, self._title):
            host.installEventFilter(self)

        # 初期スタイル
        self._apply_compact(self.isMaximized())

        # 進行フラグ
        self._busy = False

    # ====== 見た目切替 ======
    def _apply_compact(self, compact: bool):
        self.setStyleSheet(build_qss(compact))
        if hasattr(self, "_shadow"):
            self._shadow.setEnabled(not compact)
        self._btn_max.setText("❏" if self.isMaximized() else "🗖")

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == QEvent.WindowStateChange:
            self._apply_compact(self.isMaximized())

    # ====== フレームレス操作（移動/リサイズ） ======
    def eventFilter(self, obj, e):
        if obj in (self._bg, self._card, self._title):
            if e.type() == QEvent.MouseButtonPress and e.button() == Qt.LeftButton:
                pos = e.globalPosition().toPoint()
                self._dragging = True
                self._drag_offset = pos - self.frameGeometry().topLeft()
                self._resizing = False
                self._resize_edges = self._edge_at(self.mapFromGlobal(pos))
                if self._resize_edges:
                    self._resizing = True
                return True
            elif e.type() == QEvent.MouseMove:
                if self._resizing:
                    self._resize_to(e.globalPosition().toPoint())
                    return True
                if self._dragging and (e.buttons() & Qt.LeftButton) and not self.isMaximized():
                    self.move(e.globalPosition().toPoint() - self._drag_offset)
                    return True
                # カーソル更新
                edges = self._edge_at(self.mapFromGlobal(e.globalPosition().toPoint()))
                self._update_cursor(edges)
            elif e.type() == QEvent.MouseButtonRelease:
                self._dragging = False
                self._resizing = False
                self.setCursor(Qt.ArrowCursor)
                return True
        return super().eventFilter(obj, e)

    def _edge_at(self, pos):
        m = 8
        r = self.rect()
        edges = ""
        if pos.y() <= m: edges += "T"
        if pos.y() >= r.height()-m: edges += "B"
        if pos.x() <= m: edges += "L"
        if pos.x() >= r.width()-m: edges += "R"
        return edges

    def _update_cursor(self, edges):
        if edges in ("TL","BR"): self.setCursor(Qt.SizeFDiagCursor)
        elif edges in ("TR","BL"): self.setCursor(Qt.SizeBDiagCursor)
        elif edges in ("L","R"): self.setCursor(Qt.SizeHorCursor)
        elif edges in ("T","B"): self.setCursor(Qt.SizeVerCursor)
        else: self.setCursor(Qt.ArrowCursor)

    def _resize_to(self, gpos):
        dx = gpos.x() - (self.frameGeometry().x())
        dy = gpos.y() - (self.frameGeometry().y())
        geo = self.geometry()
        minw, minh = self.minimumSize().width(), self.minimumSize().height()
        x, y, w, h = geo.x(), geo.y(), geo.width(), geo.height()

        # 左端/上端は座標を動かしつつサイズ調整
        if "L" in self._resize_edges:
            new_x = gpos.x() - self._drag_offset.x()
            delta = x - new_x
            w = max(minw, w + delta)
            x = x - delta
        if "R" in self._resize_edges:
            w = max(minw, dx - self._drag_offset.x() + w)
        if "T" in self._resize_edges:
            new_y = gpos.y() - self._drag_offset.y()
            delta = y - new_y
            h = max(minh, h + delta)
            y = y - delta
        if "B" in self._resize_edges:
            h = max(minh, dy - self._drag_offset.y() + h)

        self.setGeometry(QRect(x, y, w, h))

    # ====== 操作系 ======
    def _toggle_max_restore(self):
        self.showNormal() if self.isMaximized() else self.showMaximized()

    def _open_readme(self):
        dlg = ReadmeDialog(self)
        dlg.move(self.frameGeometry().center() - dlg.rect().center())
        dlg.exec()

    def _pick_files(self):
        # 複数選択
        patterns = "画像ファイル (" + " ".join(f"*{ext}" for ext in SUPPORTED_EXTENSIONS) + ");;すべてのファイル (*.*)"
        files, _ = QFileDialog.getOpenFileNames(self, "画像ファイルを選択", "", patterns)
        if files:
            self.start_processing(files)

    def _pick_dir(self):
        d = QFileDialog.getExistingDirectory(self, "画像が入ったフォルダを選択")
        if d:
            self.start_processing([d])

    # ====== 実行 ======
    def start_processing(self, items: List[str]):
        if self._busy:
            self._on_status("いま処理中だよ…少し待ってね")
            return

        # 分割方向
        split_direction = "right_to_left" if self.rb_r2l.isChecked() else "left_to_right"

        # UIロック＆初期化
        self._busy = True
        self.progress.setValue(0)
        self._on_status("準備中…")

        # バックグラウンドThread
        t = threading.Thread(
            target=self.processor.process_images,
            args=(items, split_direction),
            daemon=True
        )
        t.start()

    # ====== シグナル受け口 ======
    def _on_progress(self, value: float):
        self.progress.setValue(int(value * 100))

    def _on_status(self, text: str):
        self.status.setText(text)

    def _on_done(self, ok: bool):
        self._busy = False
        if ok:
            self._on_status("すべての画像の分割が完了しました！")
        else:
            self._on_status("処理が中断されました。")
        # 視認性のため進捗は100%に固定
        self.progress.setValue(100)
