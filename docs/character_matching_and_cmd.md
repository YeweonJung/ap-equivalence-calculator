# 글자 비교와 추가 CMD 분석 (2026-09-18)

## 오타 검토
`services/name_distance.py`는 최적 문자열 정렬(Optimal String Alignment) 편집거리로 삽입, 삭제, 교체, 인접 글자 순서 교환을 각각 비용 1로 계산한다. 위치는 정규화된 약물명의 1부터 시작하는 위치다. 대소문자 및 장식 문장부호를 정규화한다. 한글은 음절 단위로 비교한다. 점수는 철자 유사도이며 약물 동일성이나 임상적 확률이 아니다.

미등록 철자와 기존 영문 오타 등록 항목은 후보 선택 전 환산하지 않는다. 기존에 등록된 약물 약칭, 정식 이름 및 제품명은 유지한다. 짧은 이름과 편집거리가 큰 입력에는 후보를 제시하지 않는다. 영문 후보는 정식 성분명과 명시적 제품명 목록으로 제한한다. 한글 후보는 기존 별칭 사전을 사용하므로 사전의 품질에 의존한다. 임의의 실제 처방을 교정하는 성능은 아직 임상 데이터셋으로 검증되지 않았다.

후보에는 글자별 편집 내역과 전체 원문을 보존한 수정안이 포함된다. 제형·용량·단위·빈도는 후보 비교로 수정하지 않는다. 이름을 선택해도 PRN, 미지원 제형 등의 기존 검증은 그대로 적용한다. Excel AuditTrail/ReviewQueue의 name_candidates에 수정 후보와 편집 근거를 남긴다. 화면에서 후보 선택 후에는 수정된 입력에 대한 결과를 새로 계산한다.

## 새 환산 분석
출처: Leucht et al. 2015, Dose Equivalents for Second-Generation Antipsychotic Drugs: The Classical Mean Dose Method, Table 1 (primary analysis).
- DOI: https://doi.org/10.1093/schbul/sbv037
- 저자 소속기관 보관 원문: https://mediatum.ub.tum.de/doc/1319918/1319918.pdf

CMD_DIRECT는 Direct Ratios 열, CMD_INDIRECT는 Direct and Indirect Ratios 열이다. 둘 다 olanzapine 1 mg/day에 대응하는 경구 용량이다. 기존 CMD와 같은 연구의 별도 분석으로, 서로 독립적인 임상 합의 기준이 아니다. 기존 CMD, MED, ED95, DDD, CPZ_FGA, WOODS, GARDNER의 계수는 변경하지 않았다.

원문 표의 숫자를 equivalence_anchors.csv에 기록하고 target anchor / source anchor 비율로 master_lookup.csv를 생성한다. n.a.는 추정하거나 다른 방법으로 보충하지 않는다. CMD_DIRECT는 9개 약물, CMD_INDIRECT는 12개 약물을 포함한다. 새 분석의 기본 출력은 OLZ mg/day이므로 CPZ 단위의 다른 분석과 숫자 자체를 직접 비교해서는 안 된다. 예: risperidone 0.27 mg/day = OLZ 1 mg/day; quetiapine은 DIRECT 27.64, INDIRECT 31.84 mg/day = OLZ 1 mg/day.

LAI에는 기존의 검증된 경구 대응량이 있을 때에만 해당 경구 분석을 적용하며 경구 대응 추정 표시를 유지한다. 원문은 성인 급성기 조현병의 경구 제제 연구이며 LAI 직접 동등성 연구가 아니다.

## 검증
원문 대표 계수, 역방향 환산, 미보고 약물 누락, 오타 네 종류, 자동확정 방지, 원문 보존, Excel 검토 근거, 기존 LAI/빈도/단위 회귀 검사를 수행한다. 변경 전후의 기존 환산 계수는 동일해야 한다.
