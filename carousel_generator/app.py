from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .storage import ensure_project, load_job, load_styles, load_template
from .ui.main_window import MainWindow


def main() -> None:
    app = QApplication(sys.argv)
    project_dir = Path.cwd() / 'Project'
    ensure_project(project_dir)
    template = load_template(project_dir, 'carousel_default')
    styles = load_styles(project_dir)
    job = load_job(project_dir, 'job_default', template.name)
    window = MainWindow(project_dir, template, styles, job)
    window.show()
    sys.exit(app.exec())
