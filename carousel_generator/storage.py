from __future__ import annotations

import json
from pathlib import Path

from .models import Job, Template, TextStyle, job_from_dict, template_from_dict, to_dict


def ensure_project(project_dir: Path) -> None:
    for folder in ['templates', 'styles', 'jobs', 'output', 'assets']:
        (project_dir / folder).mkdir(parents=True, exist_ok=True)
    settings = project_dir / 'settings.json'
    if not settings.exists():
        settings.write_text(json.dumps({'lastTemplate': 'carousel_default', 'lastJob': 'job_default'}, ensure_ascii=False, indent=2), encoding='utf-8')


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding='utf-8'))


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def template_path(project_dir: Path, name: str) -> Path:
    return project_dir / 'templates' / f'{name}.json'


def style_path(project_dir: Path, name: str) -> Path:
    return project_dir / 'styles' / f'{name}.json'


def job_path(project_dir: Path, name: str) -> Path:
    return project_dir / 'jobs' / f'{name}.json'


def load_template(project_dir: Path, name: str) -> Template:
    path = template_path(project_dir, name)
    if not path.exists():
        tpl = Template(
            name=name,
            textRegions=[
                {'name': 'hero', 'x': 80, 'y': 80, 'width': 920, 'height': 260, 'padding': 12, 'overflow': 'shrink-to-fit', 'align': 'center', 'valign': 'middle', 'defaultStyle': 'H1'},
                {'name': 'sub', 'x': 80, 'y': 360, 'width': 920, 'height': 220, 'padding': 10, 'overflow': 'wrap', 'align': 'left', 'valign': 'top', 'defaultStyle': 'H2'},
            ],
            imageRegions=[
                {'name': 'main', 'x': 80, 'y': 620, 'width': 920, 'height': 650, 'fit': 'cover', 'defaultCrop': {'scale': 1.0, 'offsetX': 0.0, 'offsetY': 0.0}},
            ],
        )
        save_template(project_dir, tpl)
        return tpl
    return template_from_dict(_read_json(path))


def save_template(project_dir: Path, template: Template) -> None:
    _write_json(template_path(project_dir, template.name), to_dict(template))


def load_styles(project_dir: Path) -> dict[str, TextStyle]:
    styles: dict[str, TextStyle] = {}
    files = sorted((project_dir / 'styles').glob('*.json'))
    if not files:
        defaults = {
            'H1': TextStyle(name='H1', fontFamily='Arial', fontSize=86, lineHeight=1.05, color='#FFFFFF'),
            'H2': TextStyle(name='H2', fontFamily='Arial', fontSize=52, lineHeight=1.2, color='#FFFFFF'),
        }
        save_styles(project_dir, defaults)
        return defaults
    for file in files:
        raw = _read_json(file)
        styles[raw['name']] = TextStyle(**raw)
    return styles


def save_styles(project_dir: Path, styles: dict[str, TextStyle]) -> None:
    for style in styles.values():
        _write_json(style_path(project_dir, style.name), to_dict(style))


def load_job(project_dir: Path, name: str, template_name: str) -> Job:
    path = job_path(project_dir, name)
    if not path.exists():
        job = Job(name=name, template=template_name, slides=[])
        save_job(project_dir, job)
        return job
    return job_from_dict(_read_json(path))


def save_job(project_dir: Path, job: Job) -> None:
    _write_json(job_path(project_dir, job.name), to_dict(job))
