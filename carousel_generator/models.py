from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import Any, Literal

OverflowMode = Literal['wrap', 'clip', 'ellipsis', 'shrink-to-fit']
AlignMode = Literal['left', 'center', 'right']
VAlignMode = Literal['top', 'middle', 'bottom']
FitMode = Literal['cover', 'contain', 'stretch']


@dataclass
class TextStyle:
    name: str
    fontFamily: str = 'Arial'
    fontSize: float = 64.0
    lineHeight: float = 1.2
    letterSpacing: float = 0.0
    color: str = '#FFFFFF'
    stroke: dict[str, Any] | None = None
    shadow: dict[str, Any] | None = None


@dataclass
class TextRegion:
    name: str
    x: int
    y: int
    width: int
    height: int
    padding: int = 0
    overflow: OverflowMode = 'wrap'
    align: AlignMode = 'left'
    valign: VAlignMode = 'top'
    defaultStyle: str = 'Body'


@dataclass
class ImageRegion:
    name: str
    x: int
    y: int
    width: int
    height: int
    fit: FitMode = 'cover'
    defaultCrop: dict[str, float] = field(default_factory=lambda: {'scale': 1.0, 'offsetX': 0.0, 'offsetY': 0.0})


@dataclass
class Template:
    name: str = 'carousel_default'
    width: int = 1080
    height: int = 1350
    background: str = '#1A1A1A'
    textRegions: list[TextRegion] = field(default_factory=list)
    imageRegions: list[ImageRegion] = field(default_factory=list)


@dataclass
class TextBlock:
    region: str
    text: str
    style: str | None = None
    align: AlignMode | None = None
    color: str | None = None


@dataclass
class ImageBlock:
    region: str
    path: str
    fit: FitMode | None = None
    crop: dict[str, float] = field(default_factory=lambda: {'scale': 1.0, 'offsetX': 0.0, 'offsetY': 0.0})


@dataclass
class Slide:
    textBlocks: list[TextBlock] = field(default_factory=list)
    imageBlocks: list[ImageBlock] = field(default_factory=list)


@dataclass
class Job:
    name: str = 'job'
    template: str = 'carousel_default'
    slides: list[Slide] = field(default_factory=list)


def _decode(dc: type, payload: dict[str, Any]):
    keys = {k for k in dc.__dataclass_fields__.keys()}
    return dc(**{k: v for k, v in payload.items() if k in keys})


def template_from_dict(data: dict[str, Any]) -> Template:
    template = _decode(Template, data)
    template.textRegions = [_decode(TextRegion, x) for x in data.get('textRegions', [])]
    template.imageRegions = [_decode(ImageRegion, x) for x in data.get('imageRegions', [])]
    return template


def job_from_dict(data: dict[str, Any]) -> Job:
    job = _decode(Job, data)
    slides: list[Slide] = []
    for raw in data.get('slides', []):
        slide = Slide(
            textBlocks=[_decode(TextBlock, x) for x in raw.get('textBlocks', [])],
            imageBlocks=[_decode(ImageBlock, x) for x in raw.get('imageBlocks', [])],
        )
        slides.append(slide)
    job.slides = slides
    return job


def to_dict(model: Any) -> dict[str, Any]:
    return asdict(model)
