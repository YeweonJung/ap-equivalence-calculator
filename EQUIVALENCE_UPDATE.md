# 등가용량 기준과 검증 (2026-09-17)

전체 환산은 CMD, MED, ED95, DDD, CPZ_FGA, WOODS, GARDNER를 각각 계산한다.
근거가 없는 약물·방법은 빈칸으로 유지하며 다른 방법으로 채우지 않는다.

## 원자료와 계수

- WOODS: Woods 2003, PMID 12823080. CPZ 100mg에 대응하는 경구 용량은
  haloperidol 2, risperidone 2, olanzapine 5, quetiapine 75, ziprasidone 60,
  aripiprazole 7.5mg이다. CPZ 자기환산을 포함한다. Paliperidone은 이 논문에 없다.
- GARDNER: Gardner 2010, PMID 20360319, Table 1의 경구 **중앙값**을 사용한다.
  CPZ 600 = OLZ 20을 기준으로 `target median / source median`을 계산한다.
  반올림된 상대역가 열이나 권장용량 범위의 중간값을 재사용하지 않는다.
  원표의 37개 명칭을 보존한다. Methotrimeprazine과 levomepromazine은 같은 성분의
  동의어지만 원표 응답 중앙값이 각각 300/400으로 달라 표의 명칭별 값을 보존하며
  서로 자동 합치지 않는다. Flupenthixol은 flupentixol, Clorprothixene은
  chlorprothixene으로 표준 철자를 사용한다.
- `lookup/equivalence_anchors.csv`: 원표 용량, 기준 약물, 연도, 출처.
- `lookup/master_lookup.csv`: 앱이 실제 읽는 환산 데이터베이스.
- `python scripts/build_equivalence_lookup.py`: 신규 두 방법의 모든 약물 쌍을 재생성한다.
  기존 방법의 계수는 변경하지 않는다.

## LAI 중간 단계

예: `paliperidone palmitate 156mg PP1M` 또는 `Sustenna 156mg monthly`:
표시량 156mg → 활성성분 100mg → 경구 paliperidone 9mg/day → 각 경구 방법.
GARDNER 결과는 CPZ 600mg/day이며 WOODS는 계수가 없어 빈칸이다.
DDD는 별도로 100/30/2.5×300 = CPZ 400mg/day이다.

`paliperidone 156mg PP1M`처럼 제형은 있지만 질량 기준을 확정할 수 없는 입력은
계산하지 않는다. `palmitate` 또는 제품명을 포함해 확인할 수 있게 입력한다.
제품명으로 국가를 단정하지 않으며, 제품과 등록된 용량의 조합을 확인하고
표시기준 검토 경고를 기록한다. 활성성분 표시와 염 질량 표시가 충돌하면 중단한다.

PP1M 39/78/117/156/234 → 활성성분 25/50/75/100/150mg.
PP3M 273/410/546/819 → 175/263/350/525mg.
PP6M 1092/1560 → 700/1000mg. PP3M/PP6M의 경구량은 PP1M 대응표를 연결한 추정이다.
숫자의 천 단위 쉼표와 약물 구분 쉼표를 구분한다.

Aristada는 lauroxil 441/662/882/1064 → aripiprazole 300/450/600/724mg을 쓴다.
경구 대응은 441mg 매월 → 10mg/day, 662mg 매월·882mg 6주·1064mg 2개월 → 15mg/day.
882mg 매월은 경구 20mg **이상**이므로 단일 경구량을 만들지 않는다.
Maintena·Asimtufii와 Aristada를 구분하며 INITIO·초기·부하·누락 후 재시작 요법은 제외한다.
월은 연구상 30일, Asimtufii 2개월은 기존 제품 기준 56일이다. 주는 7일이다.

유지요법의 경구 대응을 이용한 연구상 추정이며 실제 전환 처방을 생성하지 않는다.
PDF의 누락 시 재투여·시작 요법 지시는 앱의 임상 처방 기능으로 구현하지 않는다.

## 중간 점검과 교차 검증

- AuditTrail: 원문 위치, 성분, 입력량, 활성성분량, 질량 기준, 투여간격, 경구량,
  각 단계 출처 및 미지원 방법을 보존한다.
- FactorSources / MethodInfo: 계수의 원자료와 방법별 출처.
- VersionInfo: 계산에 사용한 버전과 데이터베이스 SHA256.
- ReviewQueue: 모든 원문에 검토자 1·2의 판단, 조정 결과, 수정값, 날짜를 기록할 수 있다.
  오류 표시가 없는 행도 무작위 표본으로 검토해야 조용한 오변환을 찾을 수 있다.
- `tests/annotated_equivalence_cases.csv`는 출처를 확인해 기대값을 작성한 **합성** 처방이다.
  실제 처방에 대한 임상의 이중 주석이나 외부 검증 완료를 의미하지 않는다.
- GitHub Actions는 파서·계수·LAI·Excel 회귀 테스트와 CSV 재생성 일치를 검사한다.

실제 연구에서는 익명화된 처방 원문에 두 검토자가 독립적으로 성분·제품·경로·함량·
빈도·일일량·LAI 표시기준을 주석하고 불일치를 조정해야 한다. 수정에 쓰는 개발 세트와
고정 검증 세트를 분리하고 기관/환자 단위로 나누어 중복 누출을 막는다.
미인식률, 성분·빈도·용량의 정확 일치율, 자동환산 오답률을 각각 보고한다.
EDI/KD 코드 매핑은 검증된 병원/공식 코드 원자료가 필요하며 이번 변경에서 추정하지 않았다.

## 출처

- https://pubmed.ncbi.nlm.nih.gov/12823080/
- https://doi.org/10.1176/appi.ajp.2009.09060802
- 원표 재수록: https://psychiatryonline.org/doi/10.1176/appi.focus.12.2.235
- https://www.jnjmedicalconnect.com/media/attestation/products/invega/invega-sustenna-dosing-conversion-to-invega-sustenna-from-oral-antipsychotics.pdf
- https://assets.jnjlabels.com/innovativemedicine/apac/australia/invega-sustenna-cmi.pdf
- https://labeling.alkermes.com/uspi_aristada.pdf
- 기존 제품별 SmPC와 WHO 출처: LAI_METHODS.md

첨부 LAI PDF는 참고자료로 읽고 용량·제품 표를 제품 설명서와 대조했다.
