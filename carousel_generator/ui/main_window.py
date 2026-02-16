from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QSlider,
    QSpinBox,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ..models import ImageBlock, Job, Slide, Template, TextBlock, TextStyle
from ..renderer import export_job, image_to_png_bytes, render_slide
from ..script_parser import parse_script, to_script
from ..storage import save_job


class CropDialog(QDialog):
    crop_changed = Signal(dict)

    def __init__(self, crop: dict[str, float], parent=None):
        super().__init__(parent)
        self.setWindowTitle('Обрезка изображения')
        self.crop = dict(crop)
        layout = QFormLayout(self)

        self.scale = QSlider(Qt.Horizontal)
        self.scale.setRange(50, 250)
        self.scale.setValue(int(self.crop.get('scale', 1.0) * 100))
        self.offset_x = QSlider(Qt.Horizontal)
        self.offset_x.setRange(-100, 100)
        self.offset_x.setValue(int(self.crop.get('offsetX', 0.0) * 100))
        self.offset_y = QSlider(Qt.Horizontal)
        self.offset_y.setRange(-100, 100)
        self.offset_y.setValue(int(self.crop.get('offsetY', 0.0) * 100))
        layout.addRow('Zoom (колесо)', self.scale)
        layout.addRow('Сдвиг X', self.offset_x)
        layout.addRow('Сдвиг Y', self.offset_y)

        for widget in [self.scale, self.offset_x, self.offset_y]:
            widget.valueChanged.connect(self._emit)

        ok = QPushButton('Готово')
        ok.clicked.connect(self.accept)
        layout.addRow(ok)

    def wheelEvent(self, event):
        step = 5 if event.angleDelta().y() > 0 else -5
        self.scale.setValue(max(self.scale.minimum(), min(self.scale.maximum(), self.scale.value() + step)))

    def _emit(self):
        self.crop = {
            'scale': self.scale.value() / 100,
            'offsetX': self.offset_x.value() / 100,
            'offsetY': self.offset_y.value() / 100,
        }
        self.crop_changed.emit(self.crop)


class MainWindow(QMainWindow):
    def __init__(self, project_dir: Path, template: Template, styles: dict[str, TextStyle], job: Job):
        super().__init__()
        self.project_dir = project_dir
        self.template = template
        self.styles = styles
        self.job = job
        self.current_slide = 0

        self.setWindowTitle('Carousel Generator')
        self.resize(1500, 900)

        tabs = QTabWidget()
        tabs.addTab(self._build_cards_tab(), 'Карточки')
        tabs.addTab(self._build_script_tab(), 'Сценарий')
        self.setCentralWidget(tabs)
        self._refresh_all()

    def _build_cards_tab(self) -> QWidget:
        root = QWidget()
        layout = QHBoxLayout(root)

        self.slide_list = QListWidget()
        self.slide_list.currentRowChanged.connect(self._on_slide_selected)

        controls = QVBoxLayout()
        add_slide = QPushButton('+ Слайд')
        dup_slide = QPushButton('Дублировать')
        del_slide = QPushButton('Удалить')
        add_slide.clicked.connect(self._add_slide)
        dup_slide.clicked.connect(self._duplicate_slide)
        del_slide.clicked.connect(self._delete_slide)
        controls.addWidget(add_slide)
        controls.addWidget(dup_slide)
        controls.addWidget(del_slide)
        controls.addStretch(1)

        left = QVBoxLayout()
        left.addWidget(QLabel('Слайды'))
        left.addWidget(self.slide_list)
        left.addLayout(controls)
        lwrap = QWidget()
        lwrap.setLayout(left)
        layout.addWidget(lwrap, 1)

        middle_wrap = QWidget()
        middle = QVBoxLayout(middle_wrap)
        self.block_list = QListWidget()
        self.block_list.currentRowChanged.connect(self._on_block_selected)

        block_btns = QHBoxLayout()
        b_text = QPushButton('+ Текст')
        b_img = QPushButton('+ Картинка')
        b_del = QPushButton('Удалить блок')
        b_text.clicked.connect(self._add_text_block)
        b_img.clicked.connect(self._add_image_block)
        b_del.clicked.connect(self._delete_block)
        block_btns.addWidget(b_text)
        block_btns.addWidget(b_img)
        block_btns.addWidget(b_del)

        form = QFormLayout()
        self.region = QComboBox()
        self.region.currentTextChanged.connect(self._save_block_changes)
        self.text = QTextEdit()
        self.text.textChanged.connect(self._save_block_changes)
        self.style = QComboBox()
        self.style.addItems(sorted(self.styles.keys()))
        self.style.currentTextChanged.connect(self._save_block_changes)
        self.align = QComboBox()
        self.align.addItems(['left', 'center', 'right'])
        self.align.currentTextChanged.connect(self._save_block_changes)
        self.image_path = QPlainTextEdit()
        self.image_path.textChanged.connect(self._save_block_changes)
        self.fit = QComboBox()
        self.fit.addItems(['cover', 'contain', 'stretch'])
        self.fit.currentTextChanged.connect(self._save_block_changes)
        pick = QPushButton('Выбрать файл...')
        pick.clicked.connect(self._pick_image)
        crop = QPushButton('Обрезать')
        crop.clicked.connect(self._open_crop)

        form.addRow('Region', self.region)
        form.addRow('Текст', self.text)
        form.addRow('Стиль', self.style)
        form.addRow('Align', self.align)
        form.addRow('Файл изображения', self.image_path)
        form.addRow('Fit', self.fit)
        form.addRow(pick, crop)

        middle.addWidget(QLabel('Блоки слайда'))
        middle.addWidget(self.block_list)
        middle.addLayout(block_btns)
        middle.addLayout(form)
        layout.addWidget(middle_wrap, 2)

        right_wrap = QWidget()
        right = QVBoxLayout(right_wrap)
        self.preview = QLabel('preview')
        self.preview.setAlignment(Qt.AlignCenter)
        self.preview.setMinimumSize(540, 675)
        self.zoom = QSpinBox()
        self.zoom.setRange(10, 300)
        self.zoom.setValue(50)
        self.zoom.valueChanged.connect(self._render_preview)
        generate = QPushButton('Сгенерировать')
        generate.clicked.connect(self._generate)
        right.addWidget(QLabel('Preview'))
        right.addWidget(self.preview, 1)
        right.addWidget(self.zoom)
        right.addWidget(generate)
        self.warnings = QPlainTextEdit()
        self.warnings.setReadOnly(True)
        right.addWidget(self.warnings)
        layout.addWidget(right_wrap, 2)

        return root

    def _build_script_tab(self) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        self.script = QPlainTextEdit()
        apply_btn = QPushButton('Импортировать сценарий')
        apply_btn.clicked.connect(self._apply_script)
        layout.addWidget(self.script)
        layout.addWidget(apply_btn)
        return root

    def _refresh_all(self):
        if not self.job.slides:
            self.job.slides.append(Slide())
        self.slide_list.clear()
        for idx, _ in enumerate(self.job.slides, start=1):
            self.slide_list.addItem(f'Слайд {idx}')
        self.slide_list.setCurrentRow(min(self.current_slide, len(self.job.slides) - 1))
        self.script.setPlainText(to_script(self.job))
        self._render_preview()

    def _slide(self) -> Slide:
        return self.job.slides[self.current_slide]

    def _on_slide_selected(self, row: int):
        if row < 0:
            return
        self.current_slide = row
        self.block_list.clear()
        slide = self._slide()
        for block in slide.textBlocks:
            self.block_list.addItem(f'Текст ({block.region})')
        for block in slide.imageBlocks:
            self.block_list.addItem(f'Картинка ({block.region})')
        self._render_preview()

    def _selected_block(self):
        idx = self.block_list.currentRow()
        if idx < 0:
            return None
        slide = self._slide()
        joined = slide.textBlocks + slide.imageBlocks
        return joined[idx] if idx < len(joined) else None

    def _on_block_selected(self, row: int):
        block = self._selected_block()
        if block is None:
            return
        self.region.blockSignals(True)
        self.region.clear()
        if isinstance(block, TextBlock):
            self.region.addItems([x.name for x in self.template.textRegions])
            self.region.setCurrentText(block.region)
            self.text.setPlainText(block.text)
            self.style.setCurrentText(block.style or self.template.textRegions[0].defaultStyle)
            self.align.setCurrentText(block.align or 'left')
        else:
            self.region.addItems([x.name for x in self.template.imageRegions])
            self.region.setCurrentText(block.region)
            self.image_path.setPlainText(block.path)
            self.fit.setCurrentText(block.fit or 'cover')
        self.region.blockSignals(False)

    def _add_slide(self):
        self.job.slides.append(Slide())
        self._refresh_all()

    def _duplicate_slide(self):
        import copy

        self.job.slides.insert(self.current_slide + 1, copy.deepcopy(self._slide()))
        self._refresh_all()

    def _delete_slide(self):
        if len(self.job.slides) == 1:
            return
        self.job.slides.pop(self.current_slide)
        self.current_slide = max(0, self.current_slide - 1)
        self._refresh_all()

    def _add_text_block(self):
        region = self.template.textRegions[0].name if self.template.textRegions else 'hero'
        self._slide().textBlocks.append(TextBlock(region=region, text=''))
        self._on_slide_selected(self.current_slide)

    def _add_image_block(self):
        region = self.template.imageRegions[0].name if self.template.imageRegions else 'main'
        self._slide().imageBlocks.append(ImageBlock(region=region, path=''))
        self._on_slide_selected(self.current_slide)

    def _delete_block(self):
        idx = self.block_list.currentRow()
        if idx < 0:
            return
        slide = self._slide()
        if idx < len(slide.textBlocks):
            slide.textBlocks.pop(idx)
        else:
            slide.imageBlocks.pop(idx - len(slide.textBlocks))
        self._on_slide_selected(self.current_slide)
        self._save()

    def _pick_image(self):
        block = self._selected_block()
        if not isinstance(block, ImageBlock):
            return
        path, _ = QFileDialog.getOpenFileName(self, 'Выберите изображение', str(self.project_dir / 'assets'), 'Images (*.png *.jpg *.jpeg *.webp)')
        if path:
            self.image_path.setPlainText(path)
            self._save_block_changes()

    def _open_crop(self):
        block = self._selected_block()
        if not isinstance(block, ImageBlock):
            return
        dlg = CropDialog(block.crop, self)
        dlg.crop_changed.connect(lambda c: self._set_crop(c))
        dlg.exec()

    def _set_crop(self, crop):
        block = self._selected_block()
        if isinstance(block, ImageBlock):
            block.crop = crop
            self._save()

    def _save_block_changes(self):
        block = self._selected_block()
        if block is None:
            return
        if isinstance(block, TextBlock):
            block.region = self.region.currentText()
            block.text = self.text.toPlainText()
            block.style = self.style.currentText()
            block.align = self.align.currentText()
        else:
            block.region = self.region.currentText()
            block.path = self.image_path.toPlainText().strip()
            block.fit = self.fit.currentText()
        self._save()

    def _save(self):
        save_job(self.project_dir, self.job)
        self.script.setPlainText(to_script(self.job))
        self._render_preview()

    def _apply_script(self):
        parsed, errors = parse_script(self.script.toPlainText())
        if errors:
            self.warnings.setPlainText('\n'.join([f'Строка {e.line}: {e.message}' for e in errors]))
            return
        if parsed:
            parsed.name = self.job.name
            self.job = parsed
            save_job(self.project_dir, self.job)
            self.warnings.setPlainText('')
            self._refresh_all()

    def _render_preview(self):
        if not self.job.slides:
            return
        image, warnings = render_slide(self.template, self.styles, self._slide())
        png = image_to_png_bytes(image)
        qimage = QImage.fromData(png, 'PNG')
        if qimage.isNull():
            return
        scale = self.zoom.value() / 100
        pix = QPixmap.fromImage(qimage).scaled(int(self.template.width * scale), int(self.template.height * scale), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.preview.setPixmap(pix)
        self.warnings.setPlainText('\n'.join(warnings))

    def _generate(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M')
        base = self.project_dir / 'output' / f'{self.job.name}_{timestamp}'
        warnings = export_job(self.template, self.styles, self.job, base, fmt='png')
        QMessageBox.information(self, 'Готово', f'Слайды экспортированы: {base}\nПредупреждений: {len(warnings)}')
