import pytest

from services.converter import convert_drug
from services.frames import convert_frame, parse_frames
from services.supplemented import PRIORITY, resolve


def converted(text, method, fallback=''):
    frames = parse_frames(text)
    assert len(frames) == 1
    frame = frames[0]
    item = convert_frame(frame, [method])
    return frame, item, resolve(item, method, fallback=fallback)


def assert_evidence_arithmetic(result, drug, method, target):
    assert result["source"]
    assert result["factor"] == pytest.approx(convert_drug(drug, 1, method, target))
    assert result["value"] == pytest.approx(result["dose"] * result["factor"])


def test_oral_paliperidone_falls_back_from_cmd_to_med_at_olanzapine_target():
    frame, item, result = converted("paliperidone 6mg", "CMD", "MED")

    assert item["conversions"][0]["value"] is None
    assert frame["route"] == "oral"
    assert result["actual"] == "MED"
    assert result["target"] == "olanzapine"
    assert result["supplemented"] is True
    assert_evidence_arithmetic(result, "paliperidone", "MED", "olanzapine")


def test_clopenthixol_falls_back_from_ddd_to_gardner():
    _, item, result = converted("clopenthixol 60mg", "DDD", "GARDNER")

    assert item["conversions"][0]["value"] is None
    assert result["actual"] == "GARDNER"
    assert result["target"] == "olanzapine"
    assert result["supplemented"] is True
    assert_evidence_arithmetic(result, "clopenthixol", "GARDNER", "olanzapine")


def test_cpz_fga_fallback_keeps_chlorpromazine_target():
    _, item, result = converted("paliperidone 6mg", "CPZ_FGA", "DDD")

    assert item["conversions"][0]["target"] == "chlorpromazine"
    assert item["conversions"][0]["value"] is None
    assert result["actual"] == "DDD"
    assert result["target"] == "chlorpromazine"
    assert result["supplemented"] is True
    assert_evidence_arithmetic(result, "paliperidone", "DDD", "chlorpromazine")


def test_ed95_fallback_uses_same_olanzapine_target_for_other_method():
    _, item, result = converted("clopenthixol 60mg", "ED95", "GARDNER")

    assert item["conversions"][0]["target"] == "olanzapine"
    assert item["conversions"][0]["value"] is None
    assert result["actual"] == "GARDNER"
    assert result["target"] == "olanzapine"
    assert result["supplemented"] is True
    assert_evidence_arithmetic(result, "clopenthixol", "GARDNER", "olanzapine")


def test_unknown_drug_does_not_fall_back():
    _, item, result = converted("unknownmedicine 5mg", "CMD")

    assert item["status"] == "unknown_drug"
    assert result["value"] is None
    assert result["actual"] == ""
    assert result["supplemented"] is False


def test_invalid_dose_does_not_fall_back():
    _, item, _ = converted("olanzapine 5mg", "CMD")
    item["daily_dose_mg"] = 0

    result = resolve(item, "CMD")

    assert result["value"] is None
    assert result["actual"] == ""
    assert result["supplemented"] is False
    assert result["reason"] == "용량·제형 정보 확인"


def test_aripiprazole_lai_without_single_oral_bridge_does_not_fall_back():
    frame, item, result = converted("aripiprazole LAI 400mg q4w", "CMD")

    assert frame["route"] == "injection"
    assert frame["oral_equivalent_mg"] is None
    assert item["conversions"][0]["value"] is None
    assert result["value"] is None
    assert result["actual"] == ""
    assert result["supplemented"] is False
    assert result["reason"] == "검증된 단일 경구 대응용량 없음"


def test_non_target_resolves_to_zero_without_supplementing():
    _, item, result = converted("lithium 600mg", "CMD")

    assert item["status"] == "non_target"
    assert result["value"] == 0.0
    assert result["status"] == "대상 외"
    assert result["actual"] == ""
    assert result["supplemented"] is False


def test_existing_base_conversion_is_returned_unchanged():
    frame, item, result = converted("olanzapine 5mg", "CMD")

    assert item["conversions"][0]["value"] == 5.0
    assert result["actual"] == "CMD"
    assert result["supplemented"] is False
    assert result["value"] == convert_drug(
        frame["drug"], frame["daily_dose_mg"], "CMD", result["target"]
    )
    assert_evidence_arithmetic(result, "olanzapine", "CMD", "olanzapine")


def test_fallback_priority_is_fixed_with_base_tried_first():
    assert PRIORITY == (
        "ED95",
        "MED",
        "GARDNER",
        "INADA",
        "CMD",
        "CMD_DIRECT",
        "CMD_INDIRECT",
        "DDD",
        "WOODS",
        "CPZ_FGA",
    )

    _, _, result = converted("olanzapine 5mg", "MED")
    assert result["actual"] == "MED"
    assert result["supplemented"] is False
