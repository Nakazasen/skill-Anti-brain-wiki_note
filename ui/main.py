import os
import sys
import json
import logging
import re
import traceback
from urllib.parse import urlparse
from datetime import datetime
from pathlib import Path

import requests
from PySide6.QtGui import QAction, QDesktopServices, QFont, QKeySequence, QShortcut, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLineEdit, QLabel, QPlainTextEdit, QMessageBox,
    QFrame, QSizePolicy, QFileDialog, QStatusBar, QTabWidget,
    QListWidget, QListWidgetItem, QComboBox, QDialog, QDialogButtonBox,
    QFormLayout, QProgressBar, QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtCore import QByteArray, QProcess, QProcessEnvironment, Qt, QTimer, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest

from release_support import (
    APP_NAME,
    APP_VERSION,
    BUILD_INFO,
    AdminSettings,
    configure_file_logger,
    export_diagnostics,
    save_feedback,
)


LOGGER = configure_file_logger("abw_admin.app", "app.log")
MIN_UI_FONT_POINT_SIZE = 10
RESULT_FONT_POINT_SIZE = 11
DEFAULT_REQUEST_TIMEOUT = 20
HEALTH_REQUEST_TIMEOUT = 5
CLI_REQUEST_TIMEOUT = 120


from release_support import feedback_dir


class PilotDashboard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Pilot Analytics Dashboard")
        self.resize(900, 650)
        self.init_ui()
        self.refresh_data()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # Metrics panel
        metrics_group = QFrame()
        metrics_group.setFrameShape(QFrame.StyledPanel)
        metrics_layout = QVBoxLayout(metrics_group)
        self.stats_label = QLabel("Loading stats...")
        self.stats_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        metrics_layout.addWidget(self.stats_label)
        layout.addWidget(metrics_group)

        # Latest entries table
        layout.addWidget(QLabel("Latest 10 Feedback Entries:"))
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Timestamp", "Version", "Category", "Message"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setWordWrap(True)
        layout.addWidget(self.table)

        # Buttons
        btn_layout = QHBoxLayout()
        self.btn_export = QPushButton("Export Summary")
        self.btn_export.clicked.connect(self.on_export)
        
        self.btn_mark_reviewed = QPushButton("Mark All as Reviewed")
        self.btn_mark_reviewed.clicked.connect(self.on_mark_reviewed)
        
        btn_layout.addWidget(self.btn_export)
        btn_layout.addWidget(self.btn_mark_reviewed)
        layout.addLayout(btn_layout)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

    def refresh_data(self):
        fdir = feedback_dir()
        if not fdir.exists():
            self.stats_label.setText("No feedback directory found.")
            return

        files = sorted(fdir.glob("feedback_*.json"), key=os.path.getmtime, reverse=True)
        total = len(files)
        bugs = 0
        usability = 0
        ideas = 0
        versions = {}
        entries = []

        for f in files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                cat = str(data.get("category", "")).lower()
                if "bug" in cat: bugs += 1
                elif "usability" in cat: usability += 1
                elif "idea" in cat: ideas += 1
                
                ver = data.get("app_version", "unknown")
                versions[ver] = versions.get(ver, 0) + 1
                
                if len(entries) < 10:
                    entries.append(data)
            except Exception:
                continue

        stats_text = (
            f"Total Feedback: {total}\n"
            f"Bugs: {bugs} | Usability: {usability} | Ideas: {ideas}\n"
            f"By Version: " + ", ".join([f"{v}: {c}" for v, c in versions.items()])
        )
        self.stats_label.setText(stats_text)

        self.table.setRowCount(0)
        for entry in entries:
            row = self.table.rowCount()
            self.table.insertRow(row)
            self.table.setItem(row, 0, QTableWidgetItem(entry.get("timestamp", "")))
            self.table.setItem(row, 1, QTableWidgetItem(entry.get("app_version", "")))
            self.table.setItem(row, 2, QTableWidgetItem(entry.get("category", "")))
            self.table.setItem(row, 3, QTableWidgetItem(entry.get("message", "")))

    def on_export(self):
        fdir = feedback_dir()
        fdir.mkdir(parents=True, exist_ok=True)
        files = list(fdir.glob("feedback_*.json"))
        all_data = []
        for f in files:
            try:
                all_data.append(json.loads(f.read_text(encoding="utf-8")))
            except:
                continue
        
        summary = {
            "exported_at": datetime.now().isoformat(),
            "count": len(all_data),
            "feedback": all_data
        }
        export_path = fdir / "feedback_summary.json"
        try:
            from datetime import datetime
            export_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
            QMessageBox.information(self, "Success", f"Exported to {export_path}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export: {str(e)}")

    def on_mark_reviewed(self):
        fdir = feedback_dir()
        fdir.mkdir(parents=True, exist_ok=True)
        files = [f.name for f in fdir.glob("feedback_*.json")]
        reviewed_file = fdir / "reviewed_index.json"
        try:
            reviewed_file.write_text(json.dumps(files, indent=2), encoding="utf-8")
            QMessageBox.information(self, "Success", "All current feedback files marked as reviewed.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to mark reviewed: {str(e)}")


class ABWAdminUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = AdminSettings()
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION}")
        window_size = self.settings.data.get("window_size", {})
        self.resize(int(window_size.get("width", 1100)), int(window_size.get("height", 750)))

        self.action_history = []
        self.buttons = []
        self.active_process = None
        self.active_cmd_name = ""
        self.active_stdout = ""
        self.active_stderr = ""
        self.active_is_search = False
        self.active_reply = None
        self.active_search_query = ""
        self.search_canceled = False
        self.network = QNetworkAccessManager(self)
        self.ingest_processed = 0
        self.ingest_total = 0
        self.active_ingest_folder = None

        self.init_ui()
        if self.settings.data.get("settings_load_error"):
            self.statusBar.showMessage("Ready - settings file could not be read; defaults were used")
            LOGGER.warning("Settings file could not be read; defaults were used")
        QTimer.singleShot(0, self.show_first_run_welcome)

    def init_ui(self):
        self.init_menu()
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        self.setStyleSheet(
            """
            QLabel, QLineEdit, QComboBox, QPushButton, QListWidget, QTableWidget {
                font-size: 10pt;
            }
            QPushButton {
                min-height: 30px;
            }
            QStatusBar {
                font-size: 10pt;
            }
            """
        )
        
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # --- Top Bar ---
        top_bar = QHBoxLayout()
        top_bar.addWidget(QLabel("API URL:"))
        default_url = os.environ.get("ABW_API_URL", f"http://127.0.0.1:{self.settings.last_api_port()}")
        self.api_url_input = QLineEdit(default_url)
        top_bar.addWidget(self.api_url_input)
        main_layout.addLayout(top_bar)
        
        # --- Content Layout ---
        content_layout = QHBoxLayout()
        main_layout.addLayout(content_layout)
        
        # --- Left Panel ---
        left_panel = QWidget()
        left_panel.setFixedWidth(320)
        left_layout = QVBoxLayout(left_panel)
        left_layout.setAlignment(Qt.AlignTop)
        left_layout.setSpacing(8)
        
        left_layout.addWidget(QLabel("Workspace Path:"))
        ws_row = QHBoxLayout()
        default_workspace = self.settings.data.get("last_workspace_path") or str(Path.cwd())
        self.workspace_input = QLineEdit(default_workspace)
        self.btn_browse = QPushButton("...")
        self.btn_browse.setFixedWidth(30)
        self.btn_browse.clicked.connect(self.on_browse)
        ws_row.addWidget(self.workspace_input)
        ws_row.addWidget(self.btn_browse)
        left_layout.addLayout(ws_row)

        self.recent_workspace_input = QComboBox()
        self.recent_workspace_input.addItem("Recent workspaces")
        for workspace in self.settings.recent_workspaces():
            self.recent_workspace_input.addItem(workspace)
        self.recent_workspace_input.currentTextChanged.connect(self.on_recent_workspace_selected)
        left_layout.addWidget(self.recent_workspace_input)
        
        left_layout.addWidget(self.create_divider())
        
        self.btn_health = QPushButton("Health")
        self.btn_health.clicked.connect(self.on_health)
        left_layout.addWidget(self.btn_health)
        self.buttons.append(self.btn_health)
        
        self.btn_inspect = QPushButton("Inspect")
        self.btn_inspect.clicked.connect(self.on_inspect)
        left_layout.addWidget(self.btn_inspect)
        self.buttons.append(self.btn_inspect)
        
        self.btn_gaps = QPushButton("Gaps")
        self.btn_gaps.clicked.connect(self.on_gaps)
        left_layout.addWidget(self.btn_gaps)
        self.buttons.append(self.btn_gaps)
        
        self.btn_trend = QPushButton("Trend")
        self.btn_trend.clicked.connect(self.on_trend)
        left_layout.addWidget(self.btn_trend)
        self.buttons.append(self.btn_trend)
        
        self.btn_improve = QPushButton("Improve")
        self.btn_improve.clicked.connect(self.on_improve)
        left_layout.addWidget(self.btn_improve)
        self.buttons.append(self.btn_improve)

        self.btn_workspace_intel = QPushButton("Workspace Intel")
        self.btn_workspace_intel.clicked.connect(self.on_workspace_intel)
        left_layout.addWidget(self.btn_workspace_intel)
        self.buttons.append(self.btn_workspace_intel)

        self.btn_ingest_raw = QPushButton("Import / Ingest Documents")
        self.btn_ingest_raw.clicked.connect(self.on_ingest_raw_folder)
        left_layout.addWidget(self.btn_ingest_raw)
        self.buttons.append(self.btn_ingest_raw)

        # Requirement 1: Add helper label
        ingest_hint = QLabel("Selecting folder mode may hide files. This is normal.")
        ingest_hint.setStyleSheet("font-size: 8pt; color: gray;")
        ingest_hint.setWordWrap(True)
        left_layout.addWidget(ingest_hint)
        
        content_layout.addWidget(left_panel)
        
        # --- Center Panel ---
        center_panel = QWidget()
        center_layout = QVBoxLayout(center_panel)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("Search Wiki:"))
        self.search_input = QComboBox()
        self.search_input.setEditable(True)
        self.search_input.setInsertPolicy(QComboBox.NoInsert)
        self.search_input.lineEdit().setPlaceholderText("Ask a question about local wiki/raw knowledge...")
        for query in self.search_history():
            self.search_input.addItem(query)
        self.search_input.lineEdit().returnPressed.connect(self.on_ask_wiki)
        search_layout.addWidget(self.search_input)
        self.btn_ask = QPushButton("Ask")
        self.btn_ask.clicked.connect(self.on_ask_wiki)
        search_layout.addWidget(self.btn_ask)
        self.btn_cancel_search = QPushButton("Cancel")
        self.btn_cancel_search.clicked.connect(self.cancel_active_process)
        self.btn_cancel_search.setEnabled(False)
        search_layout.addWidget(self.btn_cancel_search)
        center_layout.addLayout(search_layout)
        self.buttons.append(self.btn_ask)

        self.search_status_row = QHBoxLayout()
        self.search_status_label = QLabel("Type a question and press Enter or Ctrl+Enter.")
        self.search_progress = QProgressBar()
        self.search_progress.setRange(0, 0)
        self.search_progress.setVisible(False)
        self.search_progress.setFixedWidth(160)
        self.search_status_row.addWidget(self.search_status_label)
        self.search_status_row.addStretch()
        self.search_status_row.addWidget(self.search_progress)
        center_layout.addLayout(self.search_status_row)

        self.search_shortcut = QShortcut(QKeySequence("Ctrl+Return"), self)
        self.search_shortcut.activated.connect(self.on_ask_wiki)
        self.search_shortcut_enter = QShortcut(QKeySequence("Ctrl+Enter"), self)
        self.search_shortcut_enter.activated.connect(self.on_ask_wiki)
        
        self.tabs = QTabWidget()

        self.answer_viewer = QPlainTextEdit()
        self.answer_viewer.setReadOnly(True)
        self.answer_viewer.setPlaceholderText("Answer will appear here after a search.")

        self.warning_banner = QLabel("")
        self.warning_banner.setStyleSheet("background-color: #fff4ce; color: #5c3b00; padding: 6px; border: 1px solid #d8a900;")
        self.warning_banner.setVisible(False)
        center_layout.addWidget(self.warning_banner)

        self.sources_viewer = QTableWidget(0, 4)
        self.sources_viewer.setHorizontalHeaderLabels(["Path", "Title", "Confidence", "Snippet"])
        self.sources_viewer.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)
        self.sources_viewer.horizontalHeader().setStretchLastSection(True)
        self.sources_viewer.verticalHeader().setDefaultSectionSize(34)
        self.sources_viewer.setWordWrap(True)
        self.sources_viewer.setEditTriggers(QTableWidget.NoEditTriggers)
        self.sources_viewer.cellDoubleClicked.connect(self.open_source_file)
        
        self.json_viewer = QPlainTextEdit()
        self.json_viewer.setReadOnly(True)
        self.json_viewer.setPlaceholderText("JSON results will appear here...")
        
        self.raw_logs_viewer = QPlainTextEdit()
        self.raw_logs_viewer.setReadOnly(True)
        self.raw_logs_viewer.setPlaceholderText("Raw command logs will appear here...")
        self.raw_viewer = self.raw_logs_viewer

        self.workspace_intel_viewer = QPlainTextEdit()
        self.workspace_intel_viewer.setReadOnly(True)
        self.workspace_intel_viewer.setPlaceholderText("Workspace intelligence report will appear here...")

        intel_fix_layout = QHBoxLayout()
        intel_fix_layout.addWidget(QLabel("Intel Issue:"))
        self.workspace_issue_input = QComboBox()
        self.workspace_issue_input.addItem("Run Workspace Intel first")
        intel_fix_layout.addWidget(self.workspace_issue_input)
        self.btn_preview_fix = QPushButton("Preview Fix")
        self.btn_preview_fix.clicked.connect(lambda: self.on_workspace_fix(dry_run=True))
        intel_fix_layout.addWidget(self.btn_preview_fix)
        self.buttons.append(self.btn_preview_fix)
        self.btn_apply_fix = QPushButton("Apply Fix")
        self.btn_apply_fix.setStyleSheet("background-color: #ffe0e0;")
        self.btn_apply_fix.clicked.connect(lambda: self.on_workspace_fix(dry_run=False))
        intel_fix_layout.addWidget(self.btn_apply_fix)
        self.buttons.append(self.btn_apply_fix)
        center_layout.addLayout(intel_fix_layout)
        
        # Monospace font
        font = self.json_viewer.font()
        font.setFamily("Courier New")
        font.setPointSize(RESULT_FONT_POINT_SIZE)
        self.answer_viewer.setFont(font)
        self.workspace_intel_viewer.setFont(font)
        self.json_viewer.setFont(font)
        self.raw_logs_viewer.setFont(font)
        
        self.tabs.addTab(self.answer_viewer, "Answer")
        self.tabs.addTab(self.sources_viewer, "Sources")
        self.tabs.addTab(self.raw_logs_viewer, "Logs")
        self.tabs.addTab(self.json_viewer, "JSON")
        self.tabs.addTab(self.workspace_intel_viewer, "Workspace Intel")
        
        center_layout.addWidget(QLabel("Result Viewer:"))
        center_layout.addWidget(self.tabs)
        
        content_layout.addWidget(center_panel)
        
        # --- Right Panel ---
        right_panel = QWidget()
        right_panel.setFixedWidth(250)
        right_layout = QVBoxLayout(right_panel)
        right_layout.setAlignment(Qt.AlignTop)
        right_layout.setSpacing(8)
        
        right_layout.addWidget(QLabel("Quick Actions:"))
        
        self.btn_cleanup_dry = QPushButton("Cleanup Drafts (Dry)")
        self.btn_cleanup_dry.clicked.connect(lambda: self.on_apply("cleanup-drafts", yes=False))
        right_layout.addWidget(self.btn_cleanup_dry)
        self.buttons.append(self.btn_cleanup_dry)
        
        self.btn_cleanup_real = QPushButton("Cleanup Drafts (REAL)")
        self.btn_cleanup_real.setStyleSheet("background-color: #ffe0e0;")
        self.btn_cleanup_real.clicked.connect(lambda: self.on_apply("cleanup-drafts", yes=True))
        right_layout.addWidget(self.btn_cleanup_real)
        self.buttons.append(self.btn_cleanup_real)
        
        self.btn_archive_dry = QPushButton("Archive Stale (Dry)")
        self.btn_archive_dry.clicked.connect(lambda: self.on_apply("archive-stale", yes=False))
        right_layout.addWidget(self.btn_archive_dry)
        self.buttons.append(self.btn_archive_dry)

        self.btn_export_diagnostics = QPushButton("Export Diagnostics")
        self.btn_export_diagnostics.clicked.connect(self.on_export_diagnostics)
        right_layout.addWidget(self.btn_export_diagnostics)
        self.buttons.append(self.btn_export_diagnostics)
        
        right_layout.addWidget(self.create_divider())
        right_layout.addWidget(QLabel("History (Last 20):"))
        self.history_list = QListWidget()
        right_layout.addWidget(self.history_list)
        
        content_layout.addWidget(right_panel)
        
        # --- Status Bar ---
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")

    def init_menu(self):
        help_menu = self.menuBar().addMenu("Help")
        
        dashboard_action = QAction("Pilot Dashboard", self)
        dashboard_action.triggered.connect(self.on_pilot_dashboard)
        help_menu.addAction(dashboard_action)

        feedback_action = QAction("Send Feedback", self)
        feedback_action.triggered.connect(self.on_send_feedback)
        help_menu.addAction(feedback_action)

        about_action = QAction("About", self)
        about_action.triggered.connect(self.on_about)
        help_menu.addAction(about_action)

    def on_pilot_dashboard(self):
        dlg = PilotDashboard(self)
        dlg.exec()

    def create_divider(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

    def on_browse(self):
        path = QFileDialog.getExistingDirectory(self, "Select Workspace Directory", self.get_workspace())
        if path:
            self.workspace_input.setText(path)
            self.remember_workspace(path)

    def on_recent_workspace_selected(self, workspace):
        if workspace and workspace != "Recent workspaces":
            self.workspace_input.setText(workspace)

    def get_base_url(self):
        return self.api_url_input.text().rstrip("/")

    def get_workspace(self):
        return self.workspace_input.text().strip()

    def search_history(self):
        history = self.settings.data.get("search_history", [])
        if not isinstance(history, list):
            return []
        return [str(item).strip() for item in history if str(item).strip()][:20]

    def remember_search_query(self, query):
        query = str(query or "").strip()
        if not query:
            return
        history = [item for item in self.search_history() if item != query]
        history.insert(0, query)
        self.settings.data["search_history"] = history[:20]
        self.search_input.blockSignals(True)
        self.search_input.clear()
        for item in self.settings.data["search_history"]:
            self.search_input.addItem(item)
        self.search_input.setCurrentText(query)
        self.search_input.blockSignals(False)

    def workspace_path(self):
        workspace = self.get_workspace()
        if not workspace:
            return None
        return Path(workspace).expanduser()

    def validate_workspace(self):
        path = self.workspace_path()
        if path is None:
            return False, "Workspace path is required. Choose the folder that contains this ABW project."
        if not path.exists():
            return False, f"Workspace path does not exist:\n{path}"
        if not path.is_dir():
            return False, f"Workspace path is not a directory:\n{path}"
        return True, str(path.resolve())

    def remember_workspace(self, workspace):
        self.settings.remember_workspace(workspace)
        known = [self.recent_workspace_input.itemText(index) for index in range(self.recent_workspace_input.count())]
        if workspace not in known:
            self.recent_workspace_input.addItem(workspace)

    def remember_api_port(self):
        parsed = urlparse(self.get_base_url())
        if parsed.port:
            self.settings.data["last_api_port"] = parsed.port

    def set_loading(self, loading: bool):
        for btn in self.buttons:
            btn.setEnabled(not loading)
        self.btn_browse.setEnabled(not loading)
        if loading:
            self.statusBar.showMessage("Running...")
            QApplication.setOverrideCursor(Qt.WaitCursor)
            QApplication.processEvents()
        else:
            QApplication.restoreOverrideCursor()
            self.statusBar.showMessage("Ready")

    def add_to_history(self, cmd):
        self.action_history.append(cmd)
        if len(self.action_history) > 20:
            self.action_history.pop(0)
        
        self.history_list.clear()
        for item in reversed(self.action_history):
            self.history_list.addItem(item)

    def handle_response(self, response, cmd_name):
        self.add_to_history(cmd_name)
        try:
            response.raise_for_status()
            data = response.json()
            pretty = json.dumps(data, indent=2)
            self.json_viewer.setPlainText(pretty)
            if cmd_name == "workspace-intel":
                rendered = self.render_workspace_intel(data.get("data", {}))
                self.workspace_intel_viewer.setPlainText(rendered)
                self.answer_viewer.setPlainText(rendered)
                self.set_sources([])
                self.show_warning_banner([])
                self.tabs.setCurrentWidget(self.workspace_intel_viewer)
            elif cmd_name == "workspace-fix":
                rendered = self.render_workspace_fix(data.get("data", {}))
                self.workspace_intel_viewer.setPlainText(rendered)
                self.answer_viewer.setPlainText(rendered)
                self.set_sources([])
                self.show_warning_banner([])
                self.tabs.setCurrentWidget(self.workspace_intel_viewer)
            else:
                self.answer_viewer.setPlainText(pretty)
                self.set_sources([])
                self.show_warning_banner([])
            self.raw_viewer.setPlainText(response.text)
            self.statusBar.showMessage(f"Success: {cmd_name}")
            LOGGER.info("Request succeeded: %s", cmd_name)
        except Exception as e:
            error_msg = str(e)
            if response is not None:
                try:
                    error_msg = response.text
                except:
                    pass
            self.statusBar.showMessage(f"Failed: {cmd_name}")
            LOGGER.exception("Request failed: %s", cmd_name)
            QMessageBox.critical(self, "Request failed", f"{cmd_name} failed.\n\n{error_msg}")

    def render_workspace_intel(self, report):
        if not isinstance(report, dict):
            return "Workspace Intel\n---------------\nNo report data returned."
        summary = report.get("summary") if isinstance(report.get("summary"), dict) else {}
        lines = [
            "Workspace Intel",
            "---------------",
            f"Workspace: {summary.get('workspace', 'unknown')}",
            (
                "Corpus: "
                f"raw={summary.get('raw_files', 0)} "
                f"wiki={summary.get('wiki_topics', 0)} "
                f"drafts={summary.get('drafts', 0)} "
                f"processed={summary.get('processed_files', 0)}"
            ),
            f"Issues: {summary.get('issue_count', 0)} highest={summary.get('highest_severity', 'none')}",
            "",
        ]
        issues = report.get("issues") if isinstance(report.get("issues"), list) else []
        self.populate_workspace_issues(issues)
        if not issues:
            lines.append("No workspace intelligence issues detected.")
        else:
            lines.append("Issues:")
            for issue in issues:
                lines.append(
                    f"- {issue.get('type')} [{issue.get('severity')}] "
                    f"count={issue.get('count')}: {issue.get('recommendation')}"
                )
                lines.append(
                    f"  fix: {issue.get('recommended_action', 'Manual review required.')} "
                    f"auto={issue.get('can_auto_fix', False)} risk={issue.get('risk_level', 'unknown')}"
                )
        actions = report.get("top_actions") if isinstance(report.get("top_actions"), list) else []
        lines.append("")
        lines.append("Top actions:")
        if actions:
            lines.extend(f"- {action}" for action in actions)
        else:
            lines.append("- None")
        return "\n".join(lines)

    def populate_workspace_issues(self, issues):
        self.workspace_issue_input.clear()
        auto_fix_count = 0
        for issue in issues:
            if not isinstance(issue, dict) or not issue.get("can_auto_fix"):
                continue
            issue_type = str(issue.get("type") or "").strip()
            if not issue_type:
                continue
            label = f"{issue_type} ({issue.get('risk_level', 'unknown')} risk)"
            self.workspace_issue_input.addItem(label, issue_type)
            auto_fix_count += 1
        if auto_fix_count == 0:
            self.workspace_issue_input.addItem("No auto-fixable issues")

    def render_workspace_fix(self, report):
        if not isinstance(report, dict):
            return "Workspace Fix\n-------------\nNo fix data returned."
        apply_report = report.get("apply_report") if isinstance(report.get("apply_report"), dict) else {}
        lines = [
            "Workspace Fix",
            "-------------",
            f"Issue type: {report.get('issue_type', 'unknown')}",
            f"Apply action: {report.get('apply_action', 'unknown')}",
            f"Mode: {report.get('mode', 'unknown')}",
            f"Risk: {report.get('risk_level', 'unknown')}",
            f"Backup/archive first: {'yes' if report.get('backup_or_archive_first') else 'no'}",
            f"Estimated impact: {report.get('estimated_impact', 'unknown')}",
            "",
            f"Files affected: {apply_report.get('files_affected_count', 0)}",
            f"Changes planned: {apply_report.get('changes_planned_count', 0)}",
            f"Changes applied: {apply_report.get('changes_applied_count', 0)}",
            f"Operation log: {apply_report.get('log_path', 'unknown')}",
        ]
        if apply_report.get("rollback_command"):
            lines.append(f"Rollback command: {apply_report['rollback_command']}")
        changes = apply_report.get("changes_planned") if isinstance(apply_report.get("changes_planned"), list) else []
        if changes:
            lines.append("")
            lines.append("Plan:")
            for change in changes:
                source = change.get("source")
                target = change.get("target")
                if source:
                    lines.append(f"- {change.get('description')}: {source} -> {target}")
                else:
                    lines.append(f"- {change.get('description')}: {target}")
        return "\n".join(lines)

    def call_api(self, method, endpoint, payload=None, timeout=DEFAULT_REQUEST_TIMEOUT):
        cmd_name = endpoint
        if payload and payload.get("action"):
            cmd_name = f"{endpoint}:{payload['action']}"
            if payload.get("yes"):
                cmd_name += " (REAL)"
            else:
                cmd_name += " (DRY)"

        self.set_loading(True)
        url = f"{self.get_base_url()}/{endpoint}"
        self.remember_workspace(self.get_workspace())
        self.remember_api_port()
        try:
            if method == "GET":
                resp = requests.get(url, timeout=timeout)
            else:
                resp = requests.post(url, json=payload, timeout=timeout)
            self.handle_response(resp, cmd_name)
        except requests.exceptions.Timeout:
            self.statusBar.showMessage(f"Timed out: {cmd_name}")
            LOGGER.exception("Request timed out: %s", cmd_name)
            QMessageBox.critical(
                self,
                "Request timed out",
                f"{cmd_name} did not finish within {timeout} seconds.\n\n"
                "Check that the ABW API is still running, then try again.",
            )
        except requests.exceptions.ConnectionError as e:
            self.statusBar.showMessage(f"Connection failed: {cmd_name}")
            LOGGER.exception("Connection failed: %s", cmd_name)
            QMessageBox.critical(
                self,
                "Connection failed",
                f"Could not reach the ABW API at:\n{self.get_base_url()}\n\n"
                "Start with the one-click launcher or update the API URL.\n\n"
                f"Details: {e}",
            )
        except Exception as e:
            self.statusBar.showMessage(f"Error: {cmd_name}")
            LOGGER.exception("Connection failed: %s", cmd_name)
            QMessageBox.critical(self, "Error", f"{cmd_name} failed.\n\n{str(e)}")
        finally:
            self.set_loading(False)

    def set_search_running(self, running, label=None):
        self.search_progress.setVisible(running)
        if running:
            self.search_progress.setRange(0, 0)
        self.btn_cancel_search.setEnabled(running)
        if label:
            self.search_status_label.setText(label)

    def show_warning_banner(self, warnings, trust_score=None):
        messages = [str(item).strip() for item in warnings if str(item).strip()]
        if trust_score is not None and trust_score < 50:
            messages.insert(0, f"Weak evidence: trust score {trust_score}/100.")
        self.warning_banner.setText(" ".join(messages))
        self.warning_banner.setVisible(bool(messages))

    def set_sources(self, sources):
        if not isinstance(sources, list):
            sources = [sources] if sources else []
        normalized = []
        for source in sources:
            if isinstance(source, dict):
                normalized.append(
                    {
                        "path": str(source.get("path") or ""),
                        "title": str(source.get("title") or ""),
                        "confidence": str(source.get("confidence") or ""),
                        "snippet": str(source.get("snippet") or ""),
                    }
                )
            else:
                normalized.append({"path": str(source), "title": "", "confidence": "", "snippet": ""})

        self.sources_viewer.setRowCount(0)
        if not normalized:
            self.sources_viewer.insertRow(0)
            self.sources_viewer.setItem(0, 0, QTableWidgetItem("No sources or file references were returned."))
            self.sources_viewer.setSpan(0, 0, 1, 4)
            return

        for source in normalized:
            row = self.sources_viewer.rowCount()
            self.sources_viewer.insertRow(row)
            self.sources_viewer.setItem(row, 0, QTableWidgetItem(source["path"]))
            self.sources_viewer.setItem(row, 1, QTableWidgetItem(source["title"]))
            self.sources_viewer.setItem(row, 2, QTableWidgetItem(source["confidence"]))
            self.sources_viewer.setItem(row, 3, QTableWidgetItem(source["snippet"]))

    def resolve_source_path(self, source_path):
        path_text = str(source_path or "").strip()
        if not path_text or path_text.startswith("No sources"):
            return None
        candidate = Path(path_text).expanduser()
        if not candidate.is_absolute():
            workspace = self.workspace_path()
            if workspace is None:
                return None
            candidate = workspace / candidate
        return candidate.resolve()

    def open_source_file(self, row, column):
        item = self.sources_viewer.item(row, 0)
        if item is None:
            return
        path = self.resolve_source_path(item.text())
        if path is None or not path.exists() or not path.is_file():
            QMessageBox.warning(self, "Source not found", f"Local source file does not exist:\n{item.text()}")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(path)))

    def extract_sources(self, text, payload):
        sources = []

        def collect(value):
            if isinstance(value, dict):
                for key, child in value.items():
                    lowered = str(key).lower()
                    if lowered in {"source", "sources", "path", "paths", "file", "files", "evidence", "citations"}:
                        collect(child)
                    elif isinstance(child, (dict, list)):
                        collect(child)
            elif isinstance(value, list):
                for child in value:
                    collect(child)
            elif isinstance(value, str):
                normalized = value.strip()
                if normalized and any(part in normalized for part in ("wiki/", "raw/", "drafts/", "processed/")):
                    sources.append(normalized)

        collect(payload)
        for match in re.findall(r"(?:(?:wiki|raw|drafts|processed)/[^\s,;:)]+)", text):
            sources.append(match.strip())

        deduped = []
        for source in sources:
            if source not in deduped:
                deduped.append(source)
        return deduped

    def extract_answer_text(self, stdout, payload):
        if isinstance(payload, dict):
            for key in ("answer", "content", "rendered", "message"):
                value = payload.get(key)
                if isinstance(value, str) and value.strip():
                    return value.strip()
            data = payload.get("data")
            if isinstance(data, dict):
                for key in ("answer", "content", "rendered", "message"):
                    value = data.get(key)
                    if isinstance(value, str) and value.strip():
                        return value.strip()
        return stdout.strip()

    def render_cli_sections(self, cmd_name, returncode, stdout, stderr, canceled=False):
        parsed_payload = None
        try:
            parsed_payload = json.loads(stdout)
        except Exception:
            parsed_payload = None

        payload = {
            "ok": returncode == 0 and not canceled,
            "command": cmd_name,
            "returncode": returncode,
            "canceled": canceled,
            "stdout": stdout,
            "stderr": stderr,
        }
        self.json_viewer.setPlainText(json.dumps(payload, indent=2))

        if canceled:
            answer = "Search canceled before ABW returned a final answer."
            sources = []
        elif returncode == 0:
            answer = self.extract_answer_text(stdout, parsed_payload)
            sources = self.extract_sources(stdout, parsed_payload)
            if not answer:
                answer = "ABW completed successfully, but no answer text was returned."
        else:
            answer = stderr.strip() or stdout.strip() or "ABW returned an error without details."
            sources = self.extract_sources(stdout + "\n" + stderr, parsed_payload)

        self.answer_viewer.setPlainText(answer)
        self.set_sources(sources)
        self.show_warning_banner(["No supporting sources were returned."] if not sources and returncode == 0 and not canceled else [])
        raw_logs = stdout.strip()
        if stderr.strip():
            raw_logs = f"{raw_logs}\n\nSTDERR:\n{stderr.strip()}".strip()
        self.raw_logs_viewer.setPlainText(raw_logs or "No raw output was returned.")
        if self.active_is_search:
            self.tabs.setCurrentWidget(self.answer_viewer)

    def render_api_search_result(self, payload):
        data = payload.get("data", {}) if isinstance(payload, dict) else {}
        answer = str(data.get("answer") or "").strip() if isinstance(data, dict) else ""
        sources = data.get("sources", []) if isinstance(data, dict) else []
        logs = data.get("logs", []) if isinstance(data, dict) else []
        warnings = data.get("warnings", []) if isinstance(data, dict) else []
        trust_score = data.get("trust_score") if isinstance(data, dict) else None
        if not answer:
            answer = "ABW completed successfully, but no answer text was returned."
        if not isinstance(sources, list):
            sources = [sources]
        if not isinstance(logs, list):
            logs = [logs]
        if not isinstance(warnings, list):
            warnings = [warnings]
        self.answer_viewer.setPlainText(answer)
        self.set_sources(sources)
        self.show_warning_banner(warnings, trust_score=trust_score if isinstance(trust_score, int) else None)
        self.raw_logs_viewer.setPlainText("\n".join(str(log) for log in logs if str(log).strip()) or "No raw logs were returned by the API.")
        self.json_viewer.setPlainText(json.dumps(payload, indent=2))
        self.tabs.setCurrentWidget(self.answer_viewer)

    def finish_api_search(self):
        reply = self.active_reply
        if reply is None:
            return
        raw = bytes(reply.readAll()).decode(errors="replace")
        status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)
        error = reply.error()
        canceled = self.search_canceled or error == QNetworkReply.OperationCanceledError
        self.active_reply = None
        self.search_canceled = False

        if canceled:
            self.answer_viewer.setPlainText("Search canceled before ABW returned a final answer.")
            self.set_sources([])
            self.show_warning_banner([])
            self.raw_logs_viewer.setPlainText(raw or "Request was canceled.")
            self.json_viewer.setPlainText(json.dumps({"ok": False, "command": "ask", "canceled": True}, indent=2))
            self.set_search_running(False, "Search canceled.")
            self.set_loading(False)
            reply.deleteLater()
            return

        if error != QNetworkReply.NoError or status_code == 404:
            detail = reply.errorString() or raw or f"HTTP {status_code}"
            LOGGER.warning("Native ask API unavailable, falling back to CLI: %s", detail)
            reply.deleteLater()
            self.set_search_running(False, "Native API unavailable; falling back to CLI.")
            self.set_loading(False)
            self.run_cli_bridge(["ask", self.active_search_query], "ask wiki", timeout=CLI_REQUEST_TIMEOUT, is_search=True)
            return

        try:
            payload = json.loads(raw)
        except Exception:
            payload = {"ok": False, "command": "ask", "data": {"answer": raw, "sources": [], "logs": ["API returned non-JSON response."], "meta": {}}}

        self.add_to_history("ask")
        self.render_api_search_result(payload)
        ok = bool(payload.get("ok")) and 200 <= int(status_code or 0) < 300
        self.set_search_running(False, "Search complete." if ok else "Search needs attention.")
        self.set_loading(False)
        if ok:
            self.statusBar.showMessage("Success: ask")
            LOGGER.info("Native ask API succeeded")
        else:
            self.statusBar.showMessage("Failed: ask")
            QMessageBox.critical(self, "Search failed", raw or "Native ask API returned an error.")
        reply.deleteLater()

    def finish_cli_bridge(self, returncode, exit_status):
        cmd_name = self.active_cmd_name
        stdout = self.active_stdout
        stderr = self.active_stderr
        was_search = self.active_is_search
        canceled = exit_status == QProcess.CrashExit and returncode != 0 and "canceled" in stderr.lower()
        self.add_to_history(cmd_name)
        self.render_cli_sections(cmd_name, returncode, stdout, stderr, canceled=canceled)
        self.active_process = None
        self.active_cmd_name = ""
        self.active_stdout = ""
        self.active_stderr = ""
        self.active_is_search = False
        success_label = "Search complete." if was_search else "Command complete."
        failure_label = "Search needs attention." if was_search else "Command needs attention."
        self.set_search_running(False, success_label if returncode == 0 and not canceled else failure_label)
        self.set_loading(False)
        if returncode == 0 and not canceled:
            self.statusBar.showMessage(f"Success: {cmd_name}")
            LOGGER.info("CLI bridge succeeded: %s", cmd_name)
            if cmd_name == "ingest":
                self.show_ingest_success_popup(stdout)
                # Requirement 4: Auto refresh
                QTimer.singleShot(500, self.on_inspect)
                QTimer.singleShot(1000, self.on_workspace_intel)
            return
        self.statusBar.showMessage(f"Failed: {cmd_name}")
        LOGGER.error("CLI bridge failed: %s returncode=%s stderr=%s", cmd_name, returncode, stderr)
        if not canceled:
            QMessageBox.critical(self, "Command failed", f"{cmd_name} failed.\n\n{stderr or stdout or 'No details returned.'}")

    def read_cli_stdout(self):
        if self.active_process is None:
            return
        data = bytes(self.active_process.readAllStandardOutput()).decode(errors="replace")
        self.active_stdout += data
        
        is_ingest = self.active_cmd_name == "ingest"
        if (self.active_is_search or is_ingest) and data:
            self.raw_logs_viewer.setPlainText((self.active_stdout + "\n" + self.active_stderr).strip())
            self.raw_logs_viewer.moveCursor(QTextCursor.End)

        if is_ingest and data:
            for line in data.splitlines():
                line = line.strip()
                if not line: continue
                # Look for file paths/names patterns and status indicators
                match = re.search(r"(?:Processing|Ingesting|->|Reading|Skipped|Failed|Error)[:\s]+(.*)", line, re.I)
                if match:
                    filename = Path(match.group(1).strip()).name
                    self.ingest_processed += 1
                    status = f"Processed {self.ingest_processed}"
                    if self.ingest_total > 0:
                        status += f" / {self.ingest_total}"
                        self.search_progress.setValue(min(self.ingest_processed, self.ingest_total))
                    
                    # Requirement 4: Show current filename being processed
                    # If error, show it prominently in the status label
                    if any(x in line.upper() for x in ["ERROR", "FAILED"]):
                        self.search_status_label.setText(f"{status}: FAIL {filename}")
                        LOGGER.warning(f"Ingest failure for file: {filename}")
                    else:
                        self.search_status_label.setText(f"{status}: {filename}")

    def read_cli_stderr(self):
        if self.active_process is None:
            return
        data = bytes(self.active_process.readAllStandardError()).decode(errors="replace")
        self.active_stderr += data
        if (self.active_is_search or self.active_cmd_name == "ingest") and data:
            self.raw_logs_viewer.setPlainText((self.active_stdout + "\n" + self.active_stderr).strip())
            self.raw_logs_viewer.moveCursor(QTextCursor.End)

    def cancel_active_process(self):
        if self.active_reply is not None:
            self.search_canceled = True
            self.search_status_label.setText("Canceling search...")
            self.btn_cancel_search.setEnabled(False)
            self.active_reply.abort()
            return
        if self.active_process is None:
            return
        self.active_stderr += "\nCanceled by user."
        self.search_status_label.setText("Canceling search...")
        self.btn_cancel_search.setEnabled(False)
        self.active_process.kill()

    def run_api_search(self, query, timeout=CLI_REQUEST_TIMEOUT):
        ok, workspace_or_error = self.validate_workspace()
        if not ok:
            self.statusBar.showMessage("Workspace path needs attention")
            QMessageBox.warning(self, "Workspace path needs attention", workspace_or_error)
            return
        if self.active_reply is not None or self.active_process is not None:
            QMessageBox.warning(self, "Search already running", "Cancel or wait for the current search before starting another.")
            return

        self.workspace_input.setText(workspace_or_error)
        self.remember_workspace(workspace_or_error)
        self.active_search_query = query
        self.search_canceled = False
        self.answer_viewer.setPlainText("Searching...")
        self.set_sources([])
        self.show_warning_banner([])
        self.raw_logs_viewer.setPlainText("Native API request started.")
        self.json_viewer.setPlainText(json.dumps({"ok": None, "command": "ask", "status": "running", "transport": "api"}, indent=2))
        self.tabs.setCurrentWidget(self.answer_viewer)
        self.set_search_running(True, "Searching through native API...")
        self.set_loading(True)

        request = QNetworkRequest(QUrl(f"{self.get_base_url()}/ask"))
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        body = QByteArray(json.dumps({"workspace": workspace_or_error, "query": query}).encode("utf-8"))
        self.active_reply = self.network.post(request, body)
        self.active_reply.finished.connect(self.finish_api_search)
        QTimer.singleShot(timeout * 1000, lambda reply=self.active_reply, timeout=timeout: self.cancel_timed_out_reply(reply, timeout))

    def run_cli_bridge(self, args, cmd_name, timeout=CLI_REQUEST_TIMEOUT, is_search=False, status_message=None):
        ok, workspace_or_error = self.validate_workspace()
        if not ok:
            self.statusBar.showMessage("Workspace path needs attention")
            QMessageBox.warning(self, "Workspace path needs attention", workspace_or_error)
            return
        if self.active_process is not None:
            QMessageBox.warning(self, "Command already running", "Cancel or wait for the current command before starting another.")
            return
        self.workspace_input.setText(workspace_or_error)
        self.remember_workspace(workspace_or_error)
        self.active_cmd_name = cmd_name
        self.active_stdout = ""
        self.active_stderr = ""
        self.active_is_search = is_search
        self.answer_viewer.setPlainText("Searching..." if is_search else "Running command...")
        self.set_sources([])
        self.show_warning_banner([])
        self.raw_logs_viewer.setPlainText("Command started. Raw output will stream here when available.")
        self.json_viewer.setPlainText(json.dumps({"ok": None, "command": cmd_name, "status": "running"}, indent=2))
        self.tabs.setCurrentWidget(self.answer_viewer)
        if is_search:
            self.set_search_running(True, status_message or "Searching local wiki/raw knowledge...")
        else:
            self.set_search_running(True, status_message or "Running command...")
        self.set_loading(True)

        try:
            process = QProcess(self)
            env = QProcessEnvironment.systemEnvironment()
            src_path = str(Path(__file__).resolve().parent.parent / "src")
            if Path(src_path).exists():
                current_pythonpath = env.value("PYTHONPATH", "")
                env.insert("PYTHONPATH", f"{src_path};{current_pythonpath}" if current_pythonpath else src_path)
            process.setProcessEnvironment(env)
            process.setWorkingDirectory(workspace_or_error)
            process.readyReadStandardOutput.connect(self.read_cli_stdout)
            process.readyReadStandardError.connect(self.read_cli_stderr)
            process.finished.connect(self.finish_cli_bridge)
            self.active_process = process
            process.start(sys.executable, ["-m", "abw.cli", "--workspace", workspace_or_error, *args])
            QTimer.singleShot(timeout * 1000, lambda process=process, timeout=timeout: self.cancel_timed_out_process(process, timeout))
        except Exception as exc:
            self.active_process = None
            self.statusBar.showMessage(f"Error: {cmd_name}")
            LOGGER.exception("CLI bridge failed: %s", cmd_name)
            self.render_cli_sections(cmd_name, 1, "", str(exc))
            QMessageBox.critical(self, "Command failed", f"{cmd_name} failed.\n\n{exc}")
            self.set_search_running(False, "Search failed to start.")
            self.set_loading(False)

    def cancel_timed_out_process(self, process, timeout):
        if self.active_process is None or self.active_process is not process:
            return
        self.active_stderr += f"\nTimed out after {timeout} seconds."
        self.active_process.kill()

    def cancel_timed_out_reply(self, reply, timeout):
        if self.active_reply is None or self.active_reply is not reply:
            return
        self.search_canceled = True
        self.raw_logs_viewer.setPlainText(f"Native API search timed out after {timeout} seconds.")
        self.active_reply.abort()

    def on_health(self):
        self.call_api("GET", "health", timeout=HEALTH_REQUEST_TIMEOUT)

    def call_workspace_api(self, endpoint):
        ok, workspace_or_error = self.validate_workspace()
        if not ok:
            self.statusBar.showMessage("Workspace path needs attention")
            QMessageBox.warning(self, "Workspace path needs attention", workspace_or_error)
            return
        self.workspace_input.setText(workspace_or_error)
        self.call_api("POST", endpoint, {"workspace": workspace_or_error})

    def on_inspect(self):
        self.call_workspace_api("inspect")

    def on_gaps(self):
        self.call_workspace_api("gaps")

    def on_trend(self):
        self.call_workspace_api("trend")

    def on_improve(self):
        self.call_workspace_api("improve")

    def on_workspace_intel(self):
        self.call_workspace_api("workspace-intel")

    def selected_workspace_issue_type(self):
        issue_type = self.workspace_issue_input.currentData()
        if issue_type:
            return str(issue_type)
        text = self.workspace_issue_input.currentText().strip()
        if text in {"Run Workspace Intel first", "No auto-fixable issues"}:
            return ""
        return text.split(" ", 1)[0]

    def on_workspace_fix(self, dry_run=True):
        issue_type = self.selected_workspace_issue_type()
        if not issue_type:
            QMessageBox.warning(self, "Workspace Fix", "Run Workspace Intel and select an auto-fixable issue first.")
            return
        if not dry_run:
            reply = QMessageBox.question(
                self,
                "Confirm Workspace Fix",
                f"Apply fix for {issue_type}?\n\nABW will archive or back up first and write an operation log.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                return
        ok, workspace_or_error = self.validate_workspace()
        if not ok:
            self.statusBar.showMessage("Workspace path needs attention")
            QMessageBox.warning(self, "Workspace path needs attention", workspace_or_error)
            return
        self.workspace_input.setText(workspace_or_error)
        self.call_api(
            "POST",
            "workspace-fix",
            {"workspace": workspace_or_error, "issue_type": issue_type, "dry_run": dry_run},
        )

    def show_ingest_success_popup(self, stdout):
        scanned = ingested = skipped = errors = artifacts = docx_detected = None
        try:
            data = json.loads(stdout)
            stats = data.get("data", {}) if isinstance(data, dict) else {}
            scanned = stats.get("scanned")
            ingested = stats.get("ingested")
            skipped = stats.get("skipped")
            errors = stats.get("errors")
            artifacts = stats.get("artifacts_updated")
            docx_detected = stats.get("docx_detected")
        except Exception:
            pass

        if scanned is None: scanned = self._regex_extract(stdout, r"scanned[:\s]+(\d+)", None)
        if ingested is None: ingested = self._regex_extract(stdout, r"ingested[:\s]+(\d+)", None)
        if skipped is None: skipped = self._regex_extract(stdout, r"skipped(?:_unchanged)?[:\s]+(\d+)", None)
        if errors is None: errors = self._regex_extract(stdout, r"errors[:\s]+(\d+)", None)
        if artifacts is None: artifacts = self._regex_extract(stdout, r"artifacts(?:_updated)?[:\s]+(\d+)", None)
        if docx_detected is None: docx_detected = "docx" in stdout.lower() or "docx" in self.active_stdout.lower()

        folder_count = 0
        if self.active_ingest_folder:
            try:
                p = Path(self.active_ingest_folder)
                if p.exists():
                    folder_count = sum(1 for f in p.rglob("*") if f.is_file())
            except Exception:
                pass

        # Fact checking: Use folder count ONLY for scanned estimation if unknown
        if (scanned is None or str(scanned) == "0") and folder_count > 0:
            scanned = folder_count

        def fmt(v):
            return str(v) if v is not None else "Unknown"

        msg_lines = [
            f"Files scanned: {fmt(scanned)}",
            f"Files newly ingested: {fmt(ingested)}",
            f"Files skipped unchanged: {fmt(skipped)}",
        ]
        
        # Requirement 2: Show artifacts updated if present
        if artifacts is not None and str(artifacts) != "0":
            msg_lines.append(f"Artifacts updated: {artifacts}")
            
        msg_lines.append(f"Errors count: {fmt(errors)}")
        msg_lines.append(f"DOCX detected: {'Yes' if docx_detected else 'No'}")

        QMessageBox.information(self, "Ingest Success", "\n".join(msg_lines))

    def _regex_extract(self, text, pattern, default):
        match = re.search(pattern, text, re.IGNORECASE)
        return match.group(1) if match else default

    def on_ingest_raw_folder(self):
        ok, workspace_or_error = self.validate_workspace()
        if not ok:
            self.statusBar.showMessage("Workspace path needs attention")
            QMessageBox.warning(self, "Workspace path needs attention", workspace_or_error)
            return
        # Requirement 1: Choose folder, default to <workspace>\raw if exists
        start_dir = str(Path(workspace_or_error) / "raw")
        if not Path(start_dir).exists():
            start_dir = workspace_or_error
            
        # Requirement 2: Dialog title
        folder = QFileDialog.getExistingDirectory(self, "Select folder containing DOCX/PDF/TXT files", start_dir)
        if not folder:
            return
            
        self.active_ingest_folder = folder
        self.ingest_processed = 0
        self.ingest_total = 0
        try:
            p = Path(folder)
            # Requirement 2: estimate from selected folder file count
            self.ingest_total = sum(1 for f in p.rglob("*") if f.is_file())
        except Exception:
            pass

        # Requirement 3: show quick count
        self.search_status_label.setText(f"{self.ingest_total} files detected")
        QApplication.processEvents() # Ensure label updates before process starts

        self.tabs.setCurrentWidget(self.raw_logs_viewer)
        # Requirement 3: Progress bar becomes determinate
        if self.ingest_total > 0:
            self.search_progress.setRange(0, self.ingest_total)
            self.search_progress.setValue(0)
        else:
            self.search_progress.setRange(0, 0) # Indeterminate if really unknown

        self.run_cli_bridge(["ingest", folder], "ingest", timeout=CLI_REQUEST_TIMEOUT, status_message=f"Ingesting ({self.ingest_total} files detected)...")

    def on_ask_wiki(self):
        question = self.search_input.currentText().strip()
        if not question:
            self.answer_viewer.setPlainText("Enter a question to search the local wiki/raw knowledge.")
            self.set_sources([])
            self.show_warning_banner([])
            self.raw_logs_viewer.setPlainText("No command output yet.")
            self.tabs.setCurrentWidget(self.answer_viewer)
            self.search_status_label.setText("Enter a question first.")
            return
        self.remember_search_query(question)
        self.run_api_search(question, timeout=CLI_REQUEST_TIMEOUT)

    def on_apply(self, action, yes=False):
        ok, workspace_or_error = self.validate_workspace()
        if not ok:
            self.statusBar.showMessage("Workspace path needs attention")
            QMessageBox.warning(self, "Workspace path needs attention", workspace_or_error)
            return
        self.workspace_input.setText(workspace_or_error)
        if yes:
            reply = QMessageBox.question(
                self, "Confirm Action",
                f"Are you sure you want to run REAL {action} on {workspace_or_error}?\nThis may modify files.",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply == QMessageBox.No:
                return

        payload = {
            "workspace": workspace_or_error,
            "action": action,
            "yes": yes
        }
        self.call_api("POST", "apply", payload)

    def on_about(self):
        QMessageBox.about(
            self,
            f"About {APP_NAME}",
            f"{APP_NAME}\nVersion: {APP_VERSION}\nBuild: {BUILD_INFO}\nAPI URL: {self.get_base_url()}",
        )

    def show_first_run_welcome(self):
        if self.settings.welcome_seen():
            return
        QMessageBox.information(
            self,
            f"Welcome to {APP_NAME}",
            "ABW Admin stores pilot feedback, diagnostics, logs, and settings locally on this machine.\n\n"
            "Start with Health, then run Inspect, Gaps, Trend, and Improve against a non-critical workspace. "
            "Use Help > Send Feedback for bugs, ideas, or usability notes.",
        )
        self.settings.mark_welcome_seen()
        try:
            self.settings.save()
        except Exception:
            LOGGER.exception("Failed to save first-run welcome state")

    def on_send_feedback(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Send Feedback")
        layout = QVBoxLayout(dialog)

        form = QFormLayout()
        category_input = QComboBox()
        category_input.addItems(["bug", "idea", "usability"])
        message_input = QPlainTextEdit()
        message_input.setPlaceholderText("Describe what happened, what you expected, and any steps to reproduce.")
        message_input.setMinimumHeight(160)
        workspace_input = QLineEdit(self.get_workspace())

        form.addRow("Category:", category_input)
        form.addRow("Workspace:", workspace_input)
        form.addRow("Message:", message_input)
        layout.addLayout(form)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)

        if dialog.exec() != QDialog.Accepted:
            return

        message = message_input.toPlainText().strip()
        if not message:
            QMessageBox.warning(self, "Feedback not saved", "Message is required.")
            return

        workspace = workspace_input.text().strip()
        if workspace == ".":
            workspace = ""
        try:
            path = save_feedback(category_input.currentText(), message, workspace or None)
            LOGGER.info("Feedback saved to %s", path)
            self.statusBar.showMessage(f"Feedback saved: {path}")
            QMessageBox.information(self, "Feedback saved", f"Saved locally:\n{path}")
        except Exception as exc:
            LOGGER.exception("Feedback save failed")
            QMessageBox.critical(self, "Feedback save failed", str(exc))

    def on_export_diagnostics(self):
        try:
            self.settings.remember_workspace(self.get_workspace())
            self.remember_api_port()
            self.settings.save()
            path = export_diagnostics(self.settings)
            LOGGER.info("Diagnostics exported to %s", path)
            self.statusBar.showMessage(f"Diagnostics exported: {path}")
            QMessageBox.information(self, "Diagnostics exported", f"Saved locally:\n{path}")
        except Exception as exc:
            LOGGER.exception("Diagnostics export failed")
            QMessageBox.critical(self, "Diagnostics export failed", str(exc))

    def closeEvent(self, event):
        size = self.size()
        self.settings.set_window_size(size.width(), size.height())
        self.settings.remember_workspace(self.get_workspace())
        self.remember_api_port()
        try:
            self.settings.save()
            LOGGER.info("Settings saved")
        except Exception:
            LOGGER.exception("Settings save failed")
        super().closeEvent(event)


def main():
    try:
        LOGGER.info("Starting %s v%s build %s", APP_NAME, APP_VERSION, BUILD_INFO)
        app = QApplication(sys.argv)
        font = QFont(app.font())
        if font.pointSize() < MIN_UI_FONT_POINT_SIZE:
            font.setPointSize(MIN_UI_FONT_POINT_SIZE)
            app.setFont(font)
        window = ABWAdminUI()
        window.show()
        return app.exec()
    except Exception as exc:
        LOGGER.critical("Startup crash: %s\n%s", exc, traceback.format_exc())
        app = QApplication.instance()
        if app is None:
            app = QApplication(sys.argv)
        QMessageBox.critical(None, "ABW Admin startup failed", f"{exc}\n\nSee logs/app.log for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
