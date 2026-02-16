from __future__ import annotations

from dataclasses import dataclass

from .models import ImageBlock, Job, Slide, TextBlock


@dataclass
class ParseError:
    line: int
    message: str


def parse_script(text: str) -> tuple[Job | None, list[ParseError]]:
    lines = text.splitlines()
    job = Job(slides=[])
    errors: list[ParseError] = []
    slide: Slide | None = None

    for i, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue
        if ':' not in line:
            errors.append(ParseError(i, 'Ожидается формат "Ключ: значение"'))
            continue

        key, value = [x.strip() for x in line.split(':', 1)]
        k = key.lower()
        if k == 'шаблон':
            job.template = value
        elif k == 'слайд':
            slide = Slide()
            job.slides.append(slide)
        elif k.startswith('текст '):
            if slide is None:
                errors.append(ParseError(i, 'Сначала объявите "Слайд:"'))
                continue
            region = key.split(' ', 1)[1].strip()
            tb = _ensure_text_block(slide, region)
            tb.text = value
        elif k.startswith('стиль '):
            if slide is None:
                errors.append(ParseError(i, 'Сначала объявите "Слайд:"'))
                continue
            region = key.split(' ', 1)[1].strip()
            tb = _ensure_text_block(slide, region)
            tb.style = value
        elif k.startswith('выравнивание '):
            if slide is None:
                errors.append(ParseError(i, 'Сначала объявите "Слайд:"'))
                continue
            region = key.split(' ', 1)[1].strip()
            tb = _ensure_text_block(slide, region)
            v = value.lower()
            mapping = {'слева': 'left', 'центр': 'center', 'справа': 'right'}
            tb.align = mapping.get(v, v)
        elif k.startswith('картинка '):
            if slide is None:
                errors.append(ParseError(i, 'Сначала объявите "Слайд:"'))
                continue
            region = key.split(' ', 1)[1].strip()
            ib = _ensure_image_block(slide, region)
            ib.path = value
        elif k.startswith('fit '):
            if slide is None:
                errors.append(ParseError(i, 'Сначала объявите "Слайд:"'))
                continue
            region = key.split(' ', 1)[1].strip()
            ib = _ensure_image_block(slide, region)
            ib.fit = value.lower()
        else:
            errors.append(ParseError(i, f'Неизвестный ключ: {key}'))

    if not job.template:
        errors.append(ParseError(1, 'Не указан "Шаблон:"'))

    return (job if not errors else None), errors


def to_script(job: Job) -> str:
    out = [f'Шаблон: {job.template}', '']
    for slide in job.slides:
        out.append('Слайд:')
        for text in slide.textBlocks:
            out.append(f'  Текст {text.region}: {text.text}')
            if text.style:
                out.append(f'  Стиль {text.region}: {text.style}')
            if text.align:
                ru = {'left': 'слева', 'center': 'центр', 'right': 'справа'}.get(text.align, text.align)
                out.append(f'  Выравнивание {text.region}: {ru}')
        for image in slide.imageBlocks:
            out.append(f'  Картинка {image.region}: {image.path}')
            if image.fit:
                out.append(f'  Fit {image.region}: {image.fit}')
        out.append('')
    return '\n'.join(out).strip() + '\n'


def _ensure_text_block(slide: Slide, region: str) -> TextBlock:
    for block in slide.textBlocks:
        if block.region == region:
            return block
    block = TextBlock(region=region, text='')
    slide.textBlocks.append(block)
    return block


def _ensure_image_block(slide: Slide, region: str) -> ImageBlock:
    for block in slide.imageBlocks:
        if block.region == region:
            return block
    block = ImageBlock(region=region, path='')
    slide.imageBlocks.append(block)
    return block
