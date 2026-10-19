# 근거 추적·단위 검증

2026-10-19. 기존 배포 `8af0079`의 약물쌍·환산계수 문자열 2,318개를 모두 보존하고 메타데이터와 검증 기능을 추가했다. 환산표 전체를 새로 임상 검증했다는 뜻은 아니다.

## 제안별 반영

| 제안 | 적용 |
|---|---|
| 1. 모르면 멈추기 | 이름 미확인·충돌·PRN·불명확한 LAI 보류 유지. 분수 정 수·농도·범위 용량/간격의 보류 보강. 기존 단위/빈도 생략 가정은 검토 표시 유지. |
| 2. 단위 검증 | unit 정확도와 mg 정규화 용량을 별도 평가. 1,000배 오차 회귀 검증. 확정적인 Unicode 표기 정규화는 경고 대신 계산 설명으로 기록. |
| 3. 근거 메타데이터 | 모든 약물쌍에 evidence_source, evidence_grade, table_version, exclusion_conditions. 정식 GRADE 미평가는 not_assessed. 다른 약물군의 등급을 이식하지 않음. |
| 4. 미등록 계수 | 빈칸·미환산 방법 보존. 기존 보완합계는 사용한 보완 방법을 함께 기록. |
| 5. LAI | 기존 제품별 조건부 환산 유지. 새 근거 필드에서도 활성성분/염 질량, 간격, depot DDD/경구 연결 추정을 구분. |
| 6. 평가 | 요소별 PPV/재현율/F1, 추가·누락, 단위, 과대/과소, 자동 처리, 정상 입력 오경고, 보류, 약물군/경로, 시간·비용, 클리닝 전후 변화. |
| 7. 하이브리드 | 매칭 규칙을 확률과 구분해 기록. 미리 준비한 비식별·합성 예측을 오프라인으로 비교 가능. 외부 LLM 자동 호출 없음. |
| 8. 코드 자산 | 외부 코드의 계수를 자동 수입하지 않고 기존 동일 방법 내 비율 계산 유지. CPZ·DZP 등 다른 계열 척도를 합산하지 않음. |
| 9. 방법론 | /methods, /api/methods, /evidence.csv 제공. 현재 지원하는 9개 방법 및 clozapine·부분작용제·LAI의 한계 설명. |
| 10. 후속 연구 | 최적·안전·뇌용적 보존 용량을 자동 판정하지 않음. 별도 연구 설계와 실제 자료 검증 필요. |

## 근거와 적용 경계

`evidence_grade=not_assessed`는 정식 등급 평가가 없다는 뜻이다. 연구 설계를 A~D로 치환하지 않는다. `table_version=legacy-import-preserved`는 과거 수입된 값을 보존했다는 뜻으로, 원문 표 전체를 이번에 재추출했다는 의미가 아니다. 원자료 앵커가 있는 방법은 표와 연도를 함께 기록한다. 재현에 `/version`의 릴리스·표 해시를 사용한다.

원문: [CMD](https://pubmed.ncbi.nlm.nih.gov/25841041/), [MED](https://pubmed.ncbi.nlm.nih.gov/24493852/), [ED95](https://pubmed.ncbi.nlm.nih.gov/31838873/), [DDD 비교](https://pmc.ncbi.nlm.nih.gov/articles/PMC4960429/), [Davis](https://pubmed.ncbi.nlm.nih.gov/4156792/), [Woods](https://pubmed.ncbi.nlm.nih.gov/12823080/), [Gardner](https://doi.org/10.1176/appi.ajp.2009.09060802). [WHO 정의](https://www.who.int/tools/atc-ddd-toolkit/about-ddd)에서 DDD는 측정 단위이며 권장 처방량과 같다는 뜻이 아니다.

LAI의 실제 경로는 `factor_evidence`, `injection_evidence`, `mass_source`, `oral_bridge_source`로 확인한다. 월=30일은 앱 연구 가정이며 q4w=28일과 구분한다. [Aristada 라벨](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=17a8d11b-73b0-4833-a0b4-cf1ef85edefb)의 441mg 월 1회 사례는 활성성분 300mg을 사용한다. 처방일수로 주사 간격을 추정하지 않는다. 청구자료 클리닝 연구의 규칙을 정확한 처방일별 합산에 자동 이식하지 않는다.

## 결과 파일

기존 6개 시트(보완합계, 보완근거, Results, MedicationResults, Review, AuditTrail)로 제공합니다. 근거 정보는 기존 AuditTrail에 포함하며 추가 분석 선택이나 비교 시트를 만들지 않습니다.

## 평가 실행

```text
python scripts/evaluate_prescriptions.py data/evaluation/synthetic_prescriptions.jsonl --output output/evaluation.json
python scripts/evaluate_prescriptions.py gold.jsonl --predictions offline_predictions.jsonl --external-api-cost-usd 0 --output output/comparator.json
```

비교 파일은 행마다 `id`와 앱 프레임 형식의 `items`를 담고, 정답 ID와 정확히 일치해야 한다. 비용은 실제 측정값을 입력한다. 모델 실행·외부 전송은 없다. 환자 자료와 정답은 로컬에서 관리하며 `output/`은 Git에서 제외된다.

정답 JSONL 예:

```json
{"id":"S001","text":"risperidone 2mg QD","should_convert":true,"normal":true,"drug_class":"SGA","route_group":"oral","gold":[{"drug":"risperidone","unit":"mg","dose_mg":2,"daily_dose_mg":2,"frequency":"QD","equivalents":[{"method":"WOODS","target":"chlorpromazine","value":100}]}]}
```

gold는 약물별 입력 순서다. 생략한 요소는 미평가, 명시적 null은 추출되면 안 되는 값이다. should_convert=false는 계산 불가능 사례, normal=true는 경고 불필요한 정상 입력으로 오경고율의 분모다. before_daily_dose_mg와 단일 약물의 변환 후 값이 모두 있을 때만 클리닝 변화율에 포함한다. 변화율은 정답 대비 개선율과 다르다.

오답 출력은 FP, 필요한 정답 미제공은 FN으로 함께 센다. 분모 0은 null. 자동 처리율은 값 산출·입력 검토 불필요 기준이며 모든 방법의 계수 보유율과 다르다. 이름 완전 일치·일부 일치 개수·추가/누락을 구분한다. 과대/과소는 정답 대비 계산 방향이며 임상적 과다/과소투여 발생률이 아니다. equivalents는 독립 정답값을 입력하고 방법·기준약물까지 일치시킨다.

공개 합성 사례는 개발 검증셋으로 외부 임상 검증이 아니다. 논문에는 독립 검토자·의견 조정, 개발/평가 분리, 미추출 입력의 사전 포함, 하위그룹 표본 수, 정상 입력 분모, 환자 단위 반복측정 처리, 신뢰구간이 추가로 필요하다. 시간은 해당 환경의 처리시간이며 시작/의존성 로딩은 제외한다. 외부 API 비용 0은 하드웨어·전력·인건비 0이라는 뜻이 아니다.

붙여넣은 요약의 논문별 성능 수치는 이 앱의 성능이 아니므로 제품 화면에 넣지 않았다. 유의하지 않은 차이는 동등성의 입증이 아니다. 석사논문용 인과·최적 용량 결론은 별도 설계와 실제 자료 검증이 필요하다.
