from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import skia

from .models import ImageRegion, Job, Slide, Template, TextRegion, TextStyle


class RenderWarning(Exception):
    pass


def render_slide(template: Template, styles: dict[str, TextStyle], slide: Slide) -> tuple[skia.Image, list[str]]:
    surface = skia.Surface(template.width, template.height)
    canvas = surface.getCanvas()
    warnings: list[str] = []
    canvas.clear(_color(template.background))

    text_map = {x.region: x for x in slide.textBlocks}
    image_map = {x.region: x for x in slide.imageBlocks}

    for region in template.imageRegions:
        block = image_map.get(region.name)
        if not block or not block.path:
            continue
        fit = block.fit or region.fit
        crop = block.crop or region.defaultCrop
        if not Path(block.path).exists():
            warnings.append(f'Изображение не найдено: {block.path}')
            _draw_placeholder(canvas, region)
            continue
        image = skia.Image.open(block.path)
        _draw_image_region(canvas, image, region, fit, crop)

    for region in template.textRegions:
        block = text_map.get(region.name)
        if not block:
            continue
        style_name = block.style or region.defaultStyle
        style = styles.get(style_name)
        if style is None:
            warnings.append(f'Стиль отсутствует: {style_name}; fallback Arial')
            style = TextStyle(name='fallback')
        if not _font_available(style.fontFamily):
            warnings.append(f'Шрифт не найден: {style.fontFamily}; fallback Arial')
            style = replace(style, fontFamily='Arial')
        _draw_text_region(canvas, block.text, region, style, block.align or region.align, block.color)

    return surface.makeImageSnapshot(), warnings


def export_job(template: Template, styles: dict[str, TextStyle], job: Job, output_dir: Path, fmt: str = 'png', jpg_quality: int = 92) -> list[str]:
    output_dir.mkdir(parents=True, exist_ok=True)
    warnings: list[str] = []
    for idx, slide in enumerate(job.slides, start=1):
        image, slide_warnings = render_slide(template, styles, slide)
        warnings.extend([f'[slide {idx}] {w}' for w in slide_warnings])
        data = image.encodeToData(skia.kJPEG_Type if fmt == 'jpg' else skia.kPNG_Type, jpg_quality)
        ext = 'jpg' if fmt == 'jpg' else 'png'
        (output_dir / f'slide_{idx:02}.{ext}').write_bytes(bytes(data))
    return warnings


def image_to_png_bytes(image: skia.Image) -> bytes:
    return bytes(image.encodeToData(skia.kPNG_Type, 100))


def _font_available(name: str) -> bool:
    fm = skia.FontMgr.RefDefault()
    return fm.matchFamily(name) is not None


def _draw_placeholder(canvas: skia.Canvas, region: ImageRegion) -> None:
    rect = skia.Rect.MakeXYWH(region.x, region.y, region.width, region.height)
    p = skia.Paint(Color=_color('#2E2E2E'))
    canvas.drawRect(rect, p)
    border = skia.Paint(Color=_color('#777777'), Style=skia.Paint.kStroke_Style, StrokeWidth=3)
    canvas.drawRect(rect, border)


def _draw_image_region(canvas: skia.Canvas, image: skia.Image, region: ImageRegion, fit: str, crop: dict[str, float]) -> None:
    dst = skia.Rect.MakeXYWH(region.x, region.y, region.width, region.height)
    src_w, src_h = image.width(), image.height()

    if fit == 'stretch':
        src = skia.Rect.MakeWH(src_w, src_h)
    else:
        scale_cover = max(region.width / src_w, region.height / src_h)
        scale_contain = min(region.width / src_w, region.height / src_h)
        base = scale_cover if fit == 'cover' else scale_contain
        extra = crop.get('scale', 1.0)
        scale = base / extra
        view_w = min(src_w, region.width / scale)
        view_h = min(src_h, region.height / scale)
        cx = src_w / 2 + crop.get('offsetX', 0.0) * src_w
        cy = src_h / 2 + crop.get('offsetY', 0.0) * src_h
        left = max(0, min(src_w - view_w, cx - view_w / 2))
        top = max(0, min(src_h - view_h, cy - view_h / 2))
        src = skia.Rect.MakeXYWH(left, top, view_w, view_h)

    canvas.save()
    canvas.clipRect(dst)
    canvas.drawImageRect(image, src, dst, skia.SamplingOptions(skia.FilterMode.kLinear))
    canvas.restore()


def _draw_text_region(canvas: skia.Canvas, text: str, region: TextRegion, style: TextStyle, align: str, override_color: str | None) -> None:
    rect = skia.Rect.MakeXYWH(region.x, region.y, region.width, region.height)
    inner = skia.Rect.MakeXYWH(
        rect.left() + region.padding,
        rect.top() + region.padding,
        max(1, rect.width() - 2 * region.padding),
        max(1, rect.height() - 2 * region.padding),
    )

    size = style.fontSize
    lines: list[str]
    while True:
        font = skia.Font(skia.Typeface(style.fontFamily), size)
        lines = _layout_lines(text, font, inner.width(), style.letterSpacing, region.overflow)
        line_h = size * style.lineHeight
        total_h = line_h * max(1, len(lines))
        if region.overflow == 'shrink-to-fit' and total_h > inner.height() and size > 8:
            size -= 1
            continue
        break

    paint = skia.Paint(Color=_color(override_color or style.color), AntiAlias=True)
    line_h = size * style.lineHeight
    total_h = line_h * len(lines)
    if region.valign == 'middle':
        y = inner.top() + (inner.height() - total_h) / 2 + size
    elif region.valign == 'bottom':
        y = inner.bottom() - total_h + size
    else:
        y = inner.top() + size

    canvas.save()
    canvas.clipRect(rect)
    for line in lines:
        font = skia.Font(skia.Typeface(style.fontFamily), size)
        line_w = font.measureText(line)
        if align == 'center':
            x = inner.left() + (inner.width() - line_w) / 2
        elif align == 'right':
            x = inner.right() - line_w
        else:
            x = inner.left()
        canvas.drawString(line, x, y, font, paint)
        y += line_h
        if y > inner.bottom() + line_h:
            break
    canvas.restore()


def _layout_lines(text: str, font: skia.Font, width: float, letter_spacing: float, overflow: str) -> list[str]:
    words = text.replace('\n', ' \n ').split()
    if overflow == 'clip':
        return [text]

    lines: list[str] = []
    current = ''
    for word in words:
        if word == '\n':
            lines.append(current)
            current = ''
            continue
        probe = word if not current else current + ' ' + word
        measure = font.measureText(probe) + max(0, len(probe) - 1) * letter_spacing
        if measure <= width or not current:
            current = probe
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)

    if overflow == 'ellipsis' and lines:
        last = lines[-1]
        while font.measureText(last + '…') > width and len(last) > 1:
            last = last[:-1]
        lines[-1] = last + '…'
    return lines or ['']


def _color(value: str) -> int:
    v = value.strip().lstrip('#')
    if len(v) == 6:
        v = 'FF' + v
    return int(v, 16)
