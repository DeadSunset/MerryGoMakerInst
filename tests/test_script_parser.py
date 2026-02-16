from carousel_generator.script_parser import parse_script, to_script
from carousel_generator.models import Job, Slide, TextBlock


def test_parse_script_ok():
    src = '''
Шаблон: carousel_default

Слайд:
  Текст hero: Привет
  Стиль hero: H1
  Выравнивание hero: центр
  Картинка main: C:\\img.jpg
  Fit main: cover
'''
    job, errors = parse_script(src)
    assert not errors
    assert job is not None
    assert job.template == 'carousel_default'
    assert len(job.slides) == 1
    assert job.slides[0].textBlocks[0].align == 'center'


def test_to_script_contains_slide():
    job = Job(template='carousel_default', slides=[Slide(textBlocks=[TextBlock(region='hero', text='hello', style='H1', align='left')])])
    out = to_script(job)
    assert 'Слайд:' in out
    assert 'Текст hero: hello' in out
