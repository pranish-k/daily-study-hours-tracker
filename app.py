import sys
import os
import json
from datetime import datetime
from PySide6.QtCore import QTimer, Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QSpinBox, QComboBox,
    QDockWidget, QTableWidget, QTableWidgetItem, QAbstractItemView
)

HISTORY_FILE = os.path.expanduser("/Users/pranishkhanal/Documents/weeklyProjects/studyTimer/study_history.json")

class StudyTracker(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Study Tracker")
        self.resize(600, 300)

        # --------------------------------------------------
        #   State Variables for Stopwatch / Timer
        # --------------------------------------------------
        self.mode = "Stopwatch"  # Can be "Stopwatch" or "Timer"

        # Stopwatch state
        self.stopwatch_seconds = 0
        self.stopwatch_active = False

        # Timer state
        self.timer_seconds = 0
        self.timer_target_seconds = 0
        self.timer_active = False

        # QTimer to update every second
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_display)

        # --------------------------------------------------
        #   Main Window Layout
        # --------------------------------------------------
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # Mode Selector (Stopwatch / Timer)
        self.mode_selector = QComboBox()
        self.mode_selector.addItems(["Stopwatch", "Timer"])
        self.mode_selector.currentIndexChanged.connect(self.on_mode_changed)

        # Time Selector (used only in Timer mode)
        self.time_selector = QSpinBox()
        self.time_selector.setRange(1, 720)  # 1 min to 12 hrs
        self.time_selector.setValue(30)
        self.time_selector.setSuffix(" min")
        self.time_selector.setVisible(False)  # hidden if in Stopwatch mode

        # Display Label (for stopwatch or timer)
        self.display_label = QLabel("00:00:00", alignment=Qt.AlignCenter)
        self.display_label.setStyleSheet("font-size: 24px;")

        # Buttons
        btn_layout = QHBoxLayout()
        self.start_button = QPushButton("Start")
        self.pause_button = QPushButton("Pause")
        self.stop_button = QPushButton("Stop")
        self.history_button = QPushButton("View History")

        # Connect buttons
        self.start_button.clicked.connect(self.start_action)
        self.pause_button.clicked.connect(self.pause_action)
        self.stop_button.clicked.connect(self.stop_action)
        self.history_button.clicked.connect(self.toggle_history_dock)

        btn_layout.addWidget(self.start_button)
        btn_layout.addWidget(self.pause_button)
        btn_layout.addWidget(self.stop_button)
        btn_layout.addWidget(self.history_button)

        # Add widgets to main layout
        layout.addWidget(self.mode_selector)
        layout.addWidget(self.time_selector)
        layout.addWidget(self.display_label)
        layout.addLayout(btn_layout)

        # --------------------------------------------------
        #   Dock Widget for History on the Right
        # --------------------------------------------------
        self.historyDock = QDockWidget("History", self)
        self.historyDock.setAllowedAreas(Qt.RightDockWidgetArea)
        self.historyDock.setFeatures(QDockWidget.NoDockWidgetFeatures)
        # Optionally remove the title bar:
        # self.historyDock.setTitleBarWidget(QWidget())

        # Create a table widget for the history
        self.historyTable = QTableWidget()
        self.historyTable.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.historyTable.setColumnCount(2)
        self.historyTable.setHorizontalHeaderLabels(["Date", "Time Studied"])
        self.historyTable.horizontalHeader().setStretchLastSection(True)

        # Put the table in the dock
        self.historyDock.setWidget(self.historyTable)
        self.addDockWidget(Qt.RightDockWidgetArea, self.historyDock)

        # Hide the dock by default
        self.historyDock.hide()

    # --------------------------------------------------------
    #   Show/Hide the History Dock with a Table
    # --------------------------------------------------------
    def toggle_history_dock(self):
        """Toggle the history dock. Also refresh the table."""
        if self.historyDock.isVisible():
            self.historyDock.hide()
        else:
            self.refresh_history_table()
            self.historyDock.show()

    def refresh_history_table(self):
        """Reload the JSON history and populate the QTableWidget."""
        history = self.load_history()

        # Clear existing rows
        self.historyTable.setRowCount(0)

        if not history:
            # If no data, just set row count = 0 and return
            return

        # Sort by date, then add rows
        sorted_items = sorted(history.items())  # (date_str, seconds)
        self.historyTable.setRowCount(len(sorted_items))

        for row_index, (day_str, seconds) in enumerate(sorted_items):
            date_item = QTableWidgetItem(day_str)
            time_item = QTableWidgetItem(self.format_seconds(seconds))

            self.historyTable.setItem(row_index, 0, date_item)
            self.historyTable.setItem(row_index, 1, time_item)

        # Optionally, resize columns to contents
        self.historyTable.resizeColumnsToContents()

    # --------------------------------------------------------
    #   Timer / Stopwatch Logic
    # --------------------------------------------------------
    def on_mode_changed(self, index):
        """Switch between Stopwatch and Timer mode."""
        self.mode = self.mode_selector.currentText()
        if self.mode == "Stopwatch":
            self.time_selector.setVisible(False)
            self.reset_timer()      # reset Timer state
        else:  # Timer
            self.time_selector.setVisible(True)
            self.reset_stopwatch()  # reset Stopwatch state

    def start_action(self):
        """Start the current mode."""
        if self.mode == "Stopwatch":
            self.start_stopwatch()
        else:
            self.start_timer()

    def pause_action(self):
        """Pause the current mode (without adding to history)."""
        if self.mode == "Stopwatch":
            self.pause_stopwatch()
        else:
            self.pause_timer()

    def stop_action(self):
        """Stop the current mode, add time to history, and reset."""
        if self.mode == "Stopwatch":
            self.stop_stopwatch()
        else:
            self.stop_timer()

    # ----------------------------
    #   STOPWATCH
    # ----------------------------
    def start_stopwatch(self):
        """Begin or resume the stopwatch."""
        if not self.stopwatch_active:
            self.stopwatch_active = True
            self.update_timer.start(1000)

    def pause_stopwatch(self):
        """Pause the stopwatch (no history saved)."""
        if self.stopwatch_active:
            self.stopwatch_active = False
            self.update_timer.stop()

    def stop_stopwatch(self):
        """Stop the stopwatch, add to history, and reset."""
        if self.stopwatch_active:
            self.stopwatch_active = False
            self.update_timer.stop()
            # Add final time to daily total
            self.add_to_daily_total(self.stopwatch_seconds)
            self.save_history()
        # Always reset (whether active or not)
        self.reset_stopwatch()

    def reset_stopwatch(self):
        """Reset stopwatch time to zero."""
        self.stopwatch_active = False
        self.stopwatch_seconds = 0
        self.update_display()

    def update_stopwatch(self):
        """Increment stopwatch by one second each tick."""
        self.stopwatch_seconds += 1

    # ----------------------------
    #   TIMER
    # ----------------------------
    def start_timer(self):
        """Begin or resume the timer."""
        if not self.timer_active:
            # If timer isn't set yet, load from user selection
            if self.timer_seconds == 0:
                self.timer_target_seconds = self.time_selector.value() * 60
                self.timer_seconds = self.timer_target_seconds
            self.timer_active = True
            self.update_timer.start(1000)

    def pause_timer(self):
        """Pause the timer countdown."""
        if self.timer_active:
            self.timer_active = False
            self.update_timer.stop()

    def stop_timer(self):
        """Stop the timer, add elapsed to history, and reset."""
        if self.timer_active:
            self.timer_active = False
            self.update_timer.stop()
            # Calculate how much actually elapsed
            elapsed = self.timer_target_seconds - self.timer_seconds
            self.add_to_daily_total(elapsed)
            self.save_history()
        # Always reset
        self.reset_timer()

    def reset_timer(self):
        """Reset timer to zero."""
        self.timer_active = False
        self.timer_seconds = 0
        self.timer_target_seconds = 0
        self.update_display()

    def update_timer_mode(self):
        """Called once per second while timer is active."""
        if self.timer_seconds > 0:
            self.timer_seconds -= 1
        else:
            # Timer finished
            self.stop_timer()

    # ----------------------------
    #   Common Update
    # ----------------------------
    def update_display(self):
        """Called every second by QTimer."""
        if self.mode == "Stopwatch" and self.stopwatch_active:
            self.update_stopwatch()
            text = self.format_seconds(self.stopwatch_seconds)

        elif self.mode == "Timer" and self.timer_active:
            self.update_timer_mode()
            text = self.format_seconds(self.timer_seconds)

        else:
            # If paused or just switched mode, show current values
            if self.mode == "Stopwatch":
                text = self.format_seconds(self.stopwatch_seconds)
            else:
                text = self.format_seconds(self.timer_seconds)

        self.display_label.setText(text)

    @staticmethod
    def format_seconds(total_seconds):
        h = total_seconds // 3600
        m = (total_seconds % 3600) // 60
        s = total_seconds % 60
        return f"{h:02d}:{m:02d}:{s:02d}"

    # --------------------------------------------------------
    #   History: Load & Save
    # --------------------------------------------------------
    def add_to_daily_total(self, added_seconds):
        """Add added_seconds to today's total in the history file."""
        if added_seconds <= 0:
            return  # No time elapsed, skip
        history = self.load_history()
        today_str = datetime.now().strftime("%Y-%m-%d")
        history[today_str] = history.get(today_str, 0) + added_seconds
        self.save_history(history)

    def load_history(self):
        if not os.path.exists(HISTORY_FILE):
            return {}
        try:
            with open(HISTORY_FILE, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}

    def save_history(self, data=None):
        if data is None:
            data = self.load_history()
        with open(HISTORY_FILE, "w") as f:
            json.dump(data, f, indent=4)


def main():
    app = QApplication(sys.argv)
    tracker = StudyTracker()
    tracker.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
