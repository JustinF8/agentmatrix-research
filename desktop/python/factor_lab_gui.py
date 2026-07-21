# -*- coding: utf-8 -*-
"""Factor Lab Desktop GUI — PySide6 desktop application for factor research.

Features:
- Factor monitoring dashboard
- Strategy backtest engine
- Risk control monitoring
- Paper factor library management
"""
from __future__ import annotations
import os
import sys
import traceback
import webbrowser
import pandas as pd

try:
    from PySide6.QtCore import Qt, QThread, Signal, QObject
    from PySide6.QtGui import QFont, QTextOption
    from PySide6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QListWidget, QListWidgetItem,
        QStackedWidget, QHBoxLayout, QVBoxLayout, QLabel, QPushButton, QLineEdit,
        QTextEdit, QPlainTextEdit, QTableWidget, QTableWidgetItem, QSpinBox,
        QHeaderView, QMessageBox, QFrame, QSizePolicy, QComboBox, QCheckBox,
        QProgressBar, QStatusBar
    )
except ImportError:
    print("PySide6 not installed. Install with: pip install pyside6")
    sys.exit(1)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

try:
    from research_core.factor_lab.libraries.arxiv_paper import IMPLEMENTED_ARXIV_FACTORS, arxiv_specs
    from research_core.risk_rule_engine.drawdown_control import DrawdownController
    from research_core.strategy_engine.backtest_engine import TradeCosts, calculate_transaction_cost, calculate_turnover
    ARXIV_AVAILABLE = True
except ImportError:
    ARXIV_AVAILABLE = False
    print("Warning: Research core modules not fully available")

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
OUT_DIR = os.path.join(PROJECT_ROOT, "outputs")
DATA_DIR = os.path.join(PROJECT_ROOT, "data")

ACCENT = "#073d61"

QSS = f"""
* {{ font-family: -apple-system,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif; }}
QMainWindow, QWidget {{ background:#f7f9ff; color:#111c2d; font-size:14px; }}

#sidebar {{ background:#ffffff; border:none; border-right:1px solid #d7dee9; outline:none; }}
#sidebar::item {{ padding:11px 16px; border-radius:10px; margin:3px 12px; color:#4b5563; }}
#sidebar::item:hover {{ background:#f1f5fb; }}
#sidebar::item:selected {{ background:{ACCENT}; color:#ffffff; }}
#brand {{ font-size:16px; font-weight:800; color:#111c2d; padding:20px 20px 6px 22px; }}
#brandsub {{ font-size:11px; color:#657184; padding:0 22px 14px 22px; }}

#title {{ font-size:23px; font-weight:800; color:#0f172a; }}
#subtitle {{ font-size:13px; color:#657184; }}
#section {{ font-size:12px; font-weight:700; color:#657184; text-transform:uppercase; letter-spacing:.4px; }}

#card {{ background:#ffffff; border:1px solid #d7dee9; border-radius:12px; }}

QPushButton {{ background:{ACCENT}; color:#fff; border:none; border-radius:8px;
  padding:9px 18px; font-weight:600; }}
QPushButton:hover {{ background:#052e47; }}
QPushButton:disabled {{ background:#9cb8d4; color:#eef2ff; }}
QPushButton#ghost {{ background:#eef1f5; color:#374151; }}
QPushButton#ghost:hover {{ background:#e3e7ee; }}

QLineEdit, QTextEdit, QPlainTextEdit, QSpinBox, QComboBox {{
  background:#fff; border:1px solid #dbe3ef; border-radius:8px; padding:8px 11px;
  selection-background-color:{ACCENT}; }}
QLineEdit:focus, QPlainTextEdit:focus, QTextEdit:focus, QSpinBox:focus, QComboBox:focus {{ border:1px solid {ACCENT}; }}
QPlainTextEdit, QTextEdit {{ font-family:'SF Mono',Menlo,Consolas,monospace; font-size:13px; }}

QTableWidget {{ background:#fff; border:1px solid #dbe3ef; border-radius:10px; gridline-color:#e9ebef; }}
QTableWidget::item {{ padding:6px 8px; }}
QTableWidget::item:selected {{ background:#e9eef3; color:#0f172a; }}
QHeaderView::section {{ background:#fbfcff; border:none; padding:8px; color:#657184; font-weight:600; }}

QScrollBar:vertical {{ background:transparent; width:10px; margin:2px; }}
QScrollBar::handle:vertical {{ background:#cbd5e1; border-radius:5px; min-height:30px; }}
QScrollBar::add-line, QScrollBar::sub-line {{ height:0; }}
"""

PILL = {
    "ok":   "background:#dff9e9; color:#13a15a; padding:4px 11px; border-radius:999px; font-weight:600;",
    "warn": "background:#fff0dd; color:#e76f00; padding:4px 11px; border-radius:999px; font-weight:600;",
    "err":  "background:#fde7e5; color:#d93025; padding:4px 11px; border-radius:999px; font-weight:600;",
    "info": "background:#eef1f5; color:#4b5563; padding:4px 11px; border-radius:999px; font-weight:600;",
}


class Worker(QObject):
    done = Signal(object)
    failed = Signal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            self.done.emit(self.fn())
        except Exception as e:
            self.failed.emit(f"{type(e).__name__}: {e}\n{traceback.format_exc()}")


def card(*widgets, spacing=10, margins=(16, 16, 16, 16)):
    f = QFrame()
    f.setObjectName("card")
    v = QVBoxLayout(f)
    v.setContentsMargins(*margins)
    v.setSpacing(spacing)
    for w in widgets:
        if isinstance(w, (QHBoxLayout, QVBoxLayout)):
            v.addLayout(w)
        else:
            v.addWidget(w)
    return f


def section(text):
    l = QLabel(text)
    l.setObjectName("section")
    return l


class FactorLabGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Factor Lab Desktop")
        self.resize(1280, 800)
        self.state = {
            "factors": [],
            "strategies": [],
            "risk_status": "normal",
            "nav_values": [],
            "arxiv_specs": arxiv_specs() if ARXIV_AVAILABLE else [],
        }
        self._thread = None
        self._worker = None

        root = QWidget()
        self.setCentralWidget(root)
        lay = QHBoxLayout(root)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)

        side = QWidget()
        side.setObjectName("sidebar")
        side.setFixedWidth(220)
        sv = QVBoxLayout(side)
        sv.setContentsMargins(0, 0, 0, 0)
        sv.setSpacing(0)

        b = QLabel("Factor Lab")
        b.setObjectName("brand")
        sv.addWidget(b)
        bs = QLabel("Research · Backtest · Risk")
        bs.setObjectName("brandsub")
        sv.addWidget(bs)

        self.nav = QListWidget()
        self.nav.setObjectName("sidebar")
        nav_items = [
            "  因子监控",
            "  论文因子库",
            "  策略回测",
            "  风控监控",
            "  设置",
        ]
        for name in nav_items:
            self.nav.addItem(QListWidgetItem(name))
        self.nav.currentRowChanged.connect(lambda i: self.stack.setCurrentIndex(i))
        sv.addWidget(self.nav, 1)
        lay.addWidget(side)

        self.stack = QStackedWidget()
        lay.addWidget(self.stack, 1)

        self.stack.addWidget(self._factor_monitor())
        self.stack.addWidget(self._arxiv_library())
        self.stack.addWidget(self._backtest())
        self.stack.addWidget(self._risk_monitor())
        self.stack.addWidget(self._settings())

        self.nav.setCurrentRow(0)
        self.setStyleSheet(QSS)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self._update_status("Ready")

    def _update_status(self, text):
        self.status_bar.showMessage(text)

    def _page(self, title, subtitle=""):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(34, 28, 34, 28)
        v.setSpacing(16)
        t = QLabel(title)
        t.setObjectName("title")
        v.addWidget(t)
        if subtitle:
            s = QLabel(subtitle)
            s.setObjectName("subtitle")
            v.addWidget(s)
        return w, v

    def _factor_monitor(self):
        w, v = self._page("因子监控", "实时监控因子IC/IR指标与验证状态")

        stats_row = QHBoxLayout()
        stats_cards = [
            ("总因子", "100+", "#073d61"),
            ("Strong", "35", "#13a15a"),
            ("Medium", "45", "#e76f00"),
            ("Weak", "20", "#d93025"),
        ]
        for label, value, color in stats_cards:
            card_widget = card(
                QLabel(label),
                QLabel(f'<strong style="font-size:24px;color:{color}">{value}</strong>'),
                margins=(12, 12, 12, 12),
                spacing=4,
            )
            stats_row.addWidget(card_widget)
        stats_row.addStretch()
        v.addWidget(card(stats_row))

        table = QTableWidget(0, 6)
        table.setHorizontalHeaderLabels(["因子", "来源", "IC_IR", "IC均值", "覆盖率", "状态"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        sample_factors = [
            ("alpha001", "Alpha101", "0.45", "0.035", "98%", "Strong"),
            ("alpha002", "Alpha101", "0.32", "0.028", "95%", "Strong"),
            ("alpha003", "Alpha101", "0.18", "0.015", "92%", "Medium"),
            ("ret_1m", "Quant API", "0.38", "0.031", "99%", "Strong"),
            ("roe_ttm", "Quant API", "0.25", "0.022", "88%", "Medium"),
            ("arxiv_magnitude_shrink", "arXiv", "0.28", "0.024", "90%", "Medium"),
        ]

        for row, (name, source, ic_ir, ic_mean, coverage, status) in enumerate(sample_factors):
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(name))
            table.setItem(row, 1, QTableWidgetItem(source))
            table.setItem(row, 2, QTableWidgetItem(ic_ir))
            table.setItem(row, 3, QTableWidgetItem(ic_mean))
            table.setItem(row, 4, QTableWidgetItem(coverage))

            status_item = QTableWidgetItem(status)
            if status == "Strong":
                status_item.setForeground(Qt.GlobalColor.green)
            elif status == "Medium":
                status_item.setForeground(Qt.GlobalColor.yellow)
            else:
                status_item.setForeground(Qt.GlobalColor.red)
            table.setItem(row, 5, status_item)

        v.addWidget(card(table), 1)

        actions = QHBoxLayout()
        actions.addWidget(QPushButton("刷新数据"))
        actions.addWidget(QPushButton("导出报告", objectName="ghost"))
        actions.addStretch()
        v.addLayout(actions)

        return w

    def _arxiv_library(self):
        w, v = self._page("论文因子库", "arXiv学术论文复现因子管理")

        info_card = card(
            QLabel("当前包含 5 篇论文的复现因子"),
            QLabel("来源: arXiv Quantitative Finance 预印本"),
            margins=(16, 16, 16, 16),
        )
        v.addWidget(info_card)

        table = QTableWidget(0, 5)
        table.setHorizontalHeaderLabels(["因子名称", "论文ID", "描述", "原始IC_IR", "年化收益"])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        if ARXIV_AVAILABLE and self.state["arxiv_specs"]:
            for row, spec in enumerate(self.state["arxiv_specs"]):
                table.insertRow(row)
                table.setItem(row, 0, QTableWidgetItem(spec.factor_name))
                table.setItem(row, 1, QTableWidgetItem(spec.metadata.get("paper_id", "-")))
                desc = spec.description[:50] + "..." if len(spec.description) > 50 else spec.description
                table.setItem(row, 2, QTableWidgetItem(desc))
                table.setItem(row, 3, QTableWidgetItem(str(spec.metadata.get("original_ic_ir", "-"))))
                table.setItem(row, 4, QTableWidgetItem(f"{spec.metadata.get('ann_ret', '-')}%"))
        else:
            table.insertRow(0)
            table.setItem(0, 0, QTableWidgetItem("arxiv_magnitude_shrink"))
            table.setItem(0, 1, QTableWidgetItem("2606.29591"))
            table.setItem(0, 2, QTableWidgetItem("幅度收缩因子：基于Portnaya论文"))
            table.setItem(0, 3, QTableWidgetItem("-0.855"))
            table.setItem(0, 4, QTableWidgetItem("6.16%"))

            table.insertRow(1)
            table.setItem(1, 0, QTableWidgetItem("arxiv_lag3_reversal"))
            table.setItem(1, 1, QTableWidgetItem("2606.29591"))
            table.setItem(1, 2, QTableWidgetItem("滞后3日反转因子"))
            table.setItem(1, 3, QTableWidgetItem("-1.920"))
            table.setItem(1, 4, QTableWidgetItem("6.21%"))

            table.insertRow(2)
            table.setItem(2, 0, QTableWidgetItem("arxiv_bounce_proxy"))
            table.setItem(2, 1, QTableWidgetItem("2606.29591"))
            table.setItem(2, 2, QTableWidgetItem("反弹代理因子"))
            table.setItem(2, 3, QTableWidgetItem("-1.065"))
            table.setItem(2, 4, QTableWidgetItem("6.04%"))

            table.insertRow(3)
            table.setItem(3, 0, QTableWidgetItem("arxiv_residual_ma20"))
            table.setItem(3, 1, QTableWidgetItem("2605.12977"))
            table.setItem(3, 2, QTableWidgetItem("瞬态统计因子"))
            table.setItem(3, 3, QTableWidgetItem("-10.025"))
            table.setItem(3, 4, QTableWidgetItem("4.40%"))

            table.insertRow(4)
            table.setItem(4, 0, QTableWidgetItem("arxiv_regime"))
            table.setItem(4, 1, QTableWidgetItem("2605.13407"))
            table.setItem(4, 2, QTableWidgetItem("波动率状态因子"))
            table.setItem(4, 3, QTableWidgetItem("-2.306"))
            table.setItem(4, 4, QTableWidgetItem("7.05%"))

        v.addWidget(card(table), 1)

        actions = QHBoxLayout()
        actions.addWidget(QPushButton("运行因子计算"))
        actions.addWidget(QPushButton("查看论文", objectName="ghost"))
        actions.addStretch()
        v.addLayout(actions)

        return w

    def _backtest(self):
        w, v = self._page("策略回测", "完整回测引擎，含交易成本与滑点模型")

        params_row = QHBoxLayout()

        param_groups = [
            ("因子集", QComboBox()),
            ("股票池", QComboBox()),
            ("调仓频率", QComboBox()),
            ("手续费", QComboBox()),
        ]

        for label, combo in param_groups:
            row = QVBoxLayout()
            row.addWidget(QLabel(label))
            row.addWidget(combo)
            params_row.addLayout(row)

        param_groups[0][1].addItems(["Alpha101", "GTJA191", "arXiv Papers", "自定义"])
        param_groups[1][1].addItems(["沪深300", "中证500", "中证1000", "全A股"])
        param_groups[2][1].addItems(["日频", "周频", "月频", "季频"])
        param_groups[3][1].addItems(["无", "3‰佣金", "3‰佣金+1‰印花税", "3‰佣金+1‰印花税+1‰滑点"])

        params_row.addStretch()
        v.addWidget(card(params_row))

        metrics_grid = QHBoxLayout()

        metrics = [
            ("年化收益", "28.5%", "#13a15a"),
            ("夏普比率", "1.85", "#073d61"),
            ("最大回撤", "-12.3%", "#d93025"),
            ("Calmar比率", "2.32", "#073d61"),
            ("换手率", "150%", "#657184"),
            ("交易成本", "2.1%", "#657184"),
        ]

        for label, value, color in metrics:
            metric_card = card(
                QLabel(label),
                QLabel(f'<strong style="font-size:22px;color:{color}">{value}</strong>'),
                margins=(12, 12, 12, 12),
                spacing=6,
            )
            metrics_grid.addWidget(metric_card)

        metrics_grid.addStretch()
        v.addWidget(card(metrics_grid))

        chart_placeholder = card(
            QLabel('<center style="font-size:48px;margin-bottom:16px">📈</center>'),
            QLabel("<center>净值曲线</center>"),
            QLabel("<center style='color:#657184;font-size:12px'>运行回测后显示净值走势与基准对比</center>"),
            margins=(24, 24, 24, 24),
        )
        chart_placeholder.setMinimumHeight(300)
        v.addWidget(chart_placeholder, 1)

        actions = QHBoxLayout()
        actions.addWidget(QPushButton("运行回测"))
        actions.addWidget(QPushButton("加载模板", objectName="ghost"))
        actions.addWidget(QPushButton("导出结果", objectName="ghost"))
        actions.addStretch()
        v.addLayout(actions)

        return w

    def _risk_monitor(self):
        w, v = self._page("风控监控", "三级预警机制：10%警告 / 12%减仓 / 15%清仓")

        status_row = QHBoxLayout()

        status_items = [
            ("当前状态", "正常", "ok"),
            ("预警等级", "0", "ok"),
            ("最大回撤", "3.2%", "ok"),
            ("当前仓位", "85%", "info"),
        ]

        for label, value, pill_type in status_items:
            status_card = card(
                QLabel(label),
                QLabel(f'<strong style="font-size:22px">{value}</strong>'),
                QLabel(f'<span style="{PILL[pill_type]}">{pill_type.upper()}</span>'),
                margins=(12, 12, 12, 12),
                spacing=4,
            )
            status_row.addWidget(status_card)

        status_row.addStretch()
        v.addWidget(card(status_row))

        threshold_card = card(
            section("预警阈值"),
            QLabel("警告线 (10%) — 禁止新开仓"),
            QLabel("减仓线 (12%) — 强制减仓50%"),
            QLabel("清仓线 (15%) — 强制全部清仓"),
            margins=(16, 16, 16, 16),
        )
        v.addWidget(threshold_card)

        nav_section = card(
            section("净值监控"),
            margins=(16, 16, 16, 16),
        )
        nav_layout = QVBoxLayout()

        nav_input_row = QHBoxLayout()
        nav_input_row.addWidget(QLabel("输入净值:"))
        nav_input = QLineEdit()
        nav_input.setPlaceholderText("例如: 950000")
        nav_input_row.addWidget(nav_input)
        nav_input_row.addWidget(QPushButton("更新"))
        nav_input_row.addStretch()
        nav_layout.addLayout(nav_input_row)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(96.8)
        progress_bar.setFormat("当前净值: 96.8% (基准: 100%)")
        nav_layout.addWidget(progress_bar)

        nav_list = QPlainTextEdit()
        nav_list.setReadOnly(True)
        nav_list.setMaximumHeight(100)
        nav_list.setPlainText("""日期          净值        回撤
2024-01-01    1000000     0.00%
2024-01-02     995000    -0.50%
2024-01-03     985000    -1.50%
2024-01-04     978000    -2.20%
2024-01-05     968000    -3.20%""")
        nav_layout.addWidget(nav_list)

        nav_section.layout().addLayout(nav_layout)
        v.addWidget(nav_section)

        position_section = card(
            section("仓位限制"),
            QLabel("单票上限: 30%"),
            QLabel("行业上限: 50%"),
            QLabel("冷却期: 5天 (强制清仓后)"),
            margins=(16, 16, 16, 16),
        )
        v.addWidget(position_section)

        return w

    def _settings(self):
        w, v = self._page("设置", "配置API密钥与数据源")

        api_card = card(
            section("LLM API 设置"),
            QLabel("DeepSeek API Key:"),
            QLineEdit(),
            QLabel("OpenAI API Key (可选):"),
            QLineEdit(),
            QLabel("Anthropic API Key (可选):"),
            QLineEdit(),
            QPushButton("保存配置"),
            margins=(16, 16, 16, 16),
        )
        v.addWidget(api_card)

        data_card = card(
            section("数据源设置"),
            QLabel("Quant API Base URL:"),
            QLineEdit("https://api.quant.com"),
            QLabel("数据缓存目录:"),
            QLineEdit(os.path.join(DATA_DIR, "cache")),
            QCheckBox("启用本地缓存"),
            margins=(16, 16, 16, 16),
        )
        v.addWidget(data_card)

        about_card = card(
            section("关于"),
            QLabel("Factor Lab Desktop"),
            QLabel("版本: v1.0.0"),
            QLabel("PySide6 桌面应用"),
            QLabel("集成因子监控、策略回测、风控监控"),
            margins=(16, 16, 16, 16),
        )
        v.addWidget(about_card)

        return w


def main():
    app = QApplication(sys.argv)
    app.setFont(QFont("-apple-system", 10))
    win = FactorLabGUI()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()