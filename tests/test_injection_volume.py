import pytest

from services.frames import parse_frames, convert_frame


@pytest.mark.parametrize('dose,volume', [(300, 1.5), (400, 2)])
@pytest.mark.parametrize('suffix', ['/{volume}ml', ' ({volume}mL)', ' {volume}ML'])
def test_label_volume_does_not_change_injection_dose(dose, volume, suffix):
    baseline = parse_frames(f'Abilify Maintena {dose}mg q4w')[0]
    text = f'Abilify Maintena {dose}mg' + suffix.format(volume=volume) + ' q4w'
    frames = parse_frames(text)
    assert len(frames) == 1
    actual = frames[0]
    assert actual['original'] == text
    assert actual['dose_mg'] == dose
    assert actual['injection_volume_ml'] == volume
    assert actual['daily_dose_mg'] == pytest.approx(baseline['daily_dose_mg'])
    assert '주사액 부피' in actual['warning']
    actual = convert_frame(actual, ['DDD', 'CMD'])
    baseline = convert_frame(baseline, ['DDD', 'CMD'])
    assert actual['conversions'] == baseline['conversions']


def test_concentration_without_total_mass_stays_unconverted():
    frame = parse_frames('Abilify Maintena 200mg/ml q4w')[0]
    assert frame['status'] == 'unsupported_formulation'
    assert frame['daily_dose_mg'] is None


def test_volume_alone_is_not_mg():
    frame = parse_frames('Abilify Maintena 2ml q4w')[0]
    assert frame['status'] == 'unsupported_formulation'
    assert frame['daily_dose_mg'] is None
