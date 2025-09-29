import os, sys
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QGraphicsDropShadowEffect, QWidget


# サポートされる画像形式の拡張子

SUPPORTED_EXTENSIONS = ('.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tiff', '.webp')


# UI 定数

PRIMARY_COLOR    = "#4169e1"
HOVER_COLOR      = "#7000e0"
TITLE_COLOR      = "#FFFFFF"
TEXT_COLOR       = "#FFFFFF"
WINDOW_BG        = "rgba(255,255,255,0)"
GLASS_BG         = "rgba(5,5,51,200)"
GLASS_BORDER     = "3px solid rgba(65,105,255,255)"
TEXTPANEL_BG     = "#579cdd"

RADIUS_WINDOW    = 18
RADIUS_CARD      = 16
RADIUS_PANEL     = 10
RADIUS_BUTTON    = 8
RADIUS_DROP      = 12

GAP_DEFAULT      = 10
PADDING_CARD     = 16


# QSS 生成

def build_qss(compact: bool = False) -> str:
    glass_grad = (
        "qlineargradient(x1:0, y1:0, x2:0, y2:1, "
        "stop:0 rgba(255,255,255,48), stop:0.5 rgba(200,220,255,22), stop:1 rgba(255,255,255,8))"
    )
    bg_img = "none" if compact else glass_grad
    return f"""
    QWidget#bgRoot {{ background-color:{WINDOW_BG}; border-radius:{RADIUS_WINDOW}px; }}
    QWidget#glassRoot {{
        background-color:{GLASS_BG};
        border:{GLASS_BORDER};
        border-radius:{RADIUS_CARD}px;
        background-image: {bg_img};
        background-repeat: no-repeat;
        background-position: 0 0;
    }}
    /* ドロップ領域 */
    QLabel#dropArea {{
        border:2px dashed {PRIMARY_COLOR};
        border-radius:{RADIUS_DROP}px;
        background-color: rgba(25, 25, 112, 0.45);
        color:#b8dcff; font-weight:bold;
    }}
    /* タイトル */
    QLabel#titleLabel {{ color:{TITLE_COLOR}; font-weight:bold; }}
    /* テキストパネル */
    .DarkPanel, #textPanel {{
        background-color:{TEXTPANEL_BG};
        border-radius:{RADIUS_PANEL}px;
        border:1px solid rgba(0,0,0,120);
        padding:8px;
        color:{TEXT_COLOR};
    }}
    /* 入力類 */
    .DarkPanel QRadioButton, .DarkPanel QLabel {{ color:{TEXT_COLOR}; }}
    .DarkPanel QComboBox, .DarkPanel QLineEdit {{
        background:#ffe4e1; color:#000; border:1px solid #888; border-radius:3px; padding:2px;
    }}
    QPushButton {{
        background-color:{PRIMARY_COLOR}; color:white; border:none;
        padding:6px 10px; border-radius:{RADIUS_BUTTON}px;
    }}
    QPushButton:hover {{ background-color:{HOVER_COLOR}; }}
    QProgressBar {{ border:1px solid #555; border-radius:5px; text-align:center; background:#333; color:white; height:16px; }}
    QProgressBar::chunk {{ background:{PRIMARY_COLOR}; border-radius:5px; }}
    """


# ドロップシャドウ

def apply_drop_shadow(widget: QWidget) -> QGraphicsDropShadowEffect:
    eff = QGraphicsDropShadowEffect(widget)
    eff.setBlurRadius(28)
    eff.setOffset(0, 3)
    c = QColor(0, 0, 0, 46) 
    eff.setColor(c)
    widget.setGraphicsEffect(eff)
    return eff


def resource_path(rel_path: str) -> str:
    base = getattr(sys, "_MEIPASS", os.path.abspath("."))
    return os.path.join(base, rel_path)

def try_icon_path(*candidates: str) -> str | None:
    for c in candidates:
        p = resource_path(c)
        if os.path.exists(p):
            return p
    return None
