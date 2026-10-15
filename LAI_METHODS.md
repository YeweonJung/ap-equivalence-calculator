최신 추가 지원(Aristada, palmitate 표시량, Woods/Gardner): [업데이트 안내](EQUIVALENCE_UPDATE.md).

# LAI 환산 지원

## 2026-10-15 지원 확대와 검토 구분

정상 LAI의 연구 계산 기준은 `calculation_note`로 보존합니다. 계산에 성공했다는 이유만으로
검토 표시를 붙이지 않으며, 입력 충돌·누락·미지원 제형·가정한 mg 단위는 계속 검토합니다.
방법별 계수 또는 단일 경구 대응용량이 없으면 해당 방법의 값과 전체 합계는 계속 빈칸입니다.

| 추가 제품군 | 검증된 지원 범위 | 근거 |
|---|---|---|
| Longavo | 50/75/100/125mg, 명시된 월 1회; 경구 RIS 2/3/4/5mg 대응 추정 및 DDD | [Health Canada 표 1](https://pdf.hres.ca/dpd_pm/00080831.PDF) |
| Rykindo | 25/37.5/50mg, 명시된 14일; DDD만 | [DailyMed §2](https://dailymed.nlm.nih.gov/dailymed/drugInfo.cfm?setid=58534c96-96f5-4c2e-a061-92d4506aee91) |
| Risvan | 75/100mg, 명시된 월 1회; 경구 RIS 3/4mg 대응 추정 및 DDD. 미국 허가표 기준으로 Okedi 28일 표와 구분 | [FDA 2024 §2.2](https://www.accessdata.fda.gov/drugsatfda_docs/label/2024/214835s000lbl.pdf) |
| Haldol decanoate / 할돌 데카노아스 | haloperidol base 표시량 0 초과~300mg, 명시된 28일; DDD만. 농도·에스터 질량 제외 | [SmPC §2, §4.2](https://www.medicines.org.uk/emc/product/15245/smpc), [WHO depot DDD 3.3mg](https://atcddd.fhi.no/atc_ddd_index/?code=N05AD01) |
| Paliperidone Teva injection | 제품별 월 유지요법 표와 활성성분 표시량 확인; PP1M 기존 대응표 | [HPRA SmPC](https://assets.hpra.ie/products/Human/37833/Licence_PA0436-050-003_23022024160349.pdf) |
| Palmeux | 제품별 월 유지요법 표와 활성성분 표시량 확인; PP1M 기존 대응표 | [AEMPS §4.2](https://cima.aemps.es/cima/dochtml/ft/86754/FT_86754.html) |
| Niapelf | 제품별 월 유지요법 표와 활성성분 표시량 확인; PP1M 기존 대응표 | [AEMPS §4.2](https://cima.aemps.es/cima/dochtml/ft/1241795003/FT_1241795003.html) |

제품의 허가·유통 현황을 보증하는 목록이 아닙니다. 위 표는 기록된 유지 처방의 연구 계산 범위입니다.
Longavo를 UZEDY 2개월 표로 대체하거나, Rykindo를 Consta와 동일한 제품으로 합치지 않습니다.
경구 대응표는 역방향 임상 전환 처방이 아닌 노출 대응에 따른 연구 추정으로 표시합니다.

`4주`, `4주마다`, `4주 간격`, `28일마다`, `28일 간격`을 명시된 주사 간격으로 인식합니다.
월은 기존의 30일 연구 기준이며 q4w와 구분합니다. 간격 없는 일반 LAI를 임의 보완하지 않습니다.
명시된 PP 제형/PP 제품의 주기는 기존 정책대로 제품 프로필에서 확인합니다.

날짜별 규칙 버전은 `prescription-date-2.1-lai`입니다.
날짜별 업로드의 `prescription_date` 경로에서도 검증된 LAI를 계산합니다. 성분·제품 필드의
용량이 같은 활성성분량인지 확인하며, 처방일수는 투여간격으로 사용하지 않습니다.
하루 정 수가 비어 있거나 1인 경우에만 주사 총량을 그대로 사용하고, 다른 값은 확인 대상으로 둡니다.
기준일별 기간 추정 경로(`review`, `replace`)의 주사제 보류 정책은 유지합니다.
LAI 제형·간격·질량 기준·경구 대응값·출처는 날짜별 AuditTrail의 `injection_evidence`에 보존하고,
보완합계에서도 이 근거를 재사용합니다. 주사 평균 mg/day를 경구 mg/day로 취급하지 않습니다.

## 계산 기준

DDD는 WHO의 주사제 전용 DDD를 사용합니다. OLZ 경구 DDD 10mg을 기준으로
`투여용량 / 투여간격(일) / 주사제 DDD × 10`을 계산합니다.

다른 방법은 **경구 대응용량 기반 추정**입니다. 제품 설명서의 유지요법 대응용량을
먼저 조회한 뒤 기존 경구 CMD/MED/ED95/WOODS/GARDNER 계수를 적용합니다. LAI 자체를 대상으로
검증된 CMD/MED/ED95 결과라는 의미가 아닙니다. 주사 용량을 일수로 나눈 값이나
DDD 결과를 다른 방법의 입력으로 재사용하지 않습니다.

| 제형 | 추가 계산 | 조건 |
|---|---|---|
| Paliperidone PP1M/PP3M/PP6M | MED, ED95, GARDNER | 등록된 활성성분 용량, 월 단위 유지요법 |
| Olanzapine pamoate | CMD, MED, ED95 | 제품 설명서의 2개월 이후 유지요법 용량·간격 |
| Risperidone Okedi 75mg | CMD, MED, ED95 | 28일 간격, 경구 대응용량 3mg/day |
| Aripiprazole LAI, risperidone 2주 제형, Okedi 100mg | DDD만 | 단일 경구 대응용량을 확정하지 않음 |

기존 CMD 표에는 paliperidone이 없으며 CPZ_FGA에는 위 약물의 계수가 없습니다.
해당 결과와 미완성 총합은 빈칸으로 둡니다. 서로 다른 방법을 섞어 합산하지 않습니다.
Results의 `환산 근거`, Detailed의 `conversion_basis` 및 `conversion_source`,
AuditTrail의 `oral_equivalent_mg` 및 `oral_bridge_source`, InjectionInfo에서 근거를 확인할 수 있습니다.

## 용량·간격 확인

- Paliperidone DDD는 활성성분 mg 기준입니다. 제형과 등록된 palmitate 질량은 활성성분으로 변환합니다.
  표시기준이 불명확한 156mg 입력은 확인 대상으로 둡니다.
- PP3M 100mg 같은 제형과 용량이 맞지 않는 입력은 빈칸으로 둡니다.
- 월은 연구상 30일로 계산합니다. Aripiprazole 720/960mg 2개월 제형은
  제품 설명서의 56일을 사용합니다. 일반적인 월간격과 주간격을 임의로 동일시하지 않습니다.
- 소수·음수·0 간격, 서로 충돌하는 간격, LAI와 BID 같은 일일 빈도의 동시 표기,
  초기·부하·PRN 처방은 자동 계산하지 않습니다.
- `aripiprazole 400mg LAI 1개월`에서 LAI를 다른 약물로 분리하지 않습니다.
- 용량·간격 표에 없는 조합은 보간하거나 용량비로 외삽하지 않습니다.

## 출처

- [WHO N05AX depot DDD](https://atcddd.fhi.no/atc_ddd_index/?code=N05AX&showdescription=yes)
- [WHO olanzapine depot DDD](https://atcddd.fhi.no/atc_ddd_index/?code=N05AH03)
- [WHO chlorpromazine DDD](https://atcddd.fhi.no/atc_ddd_index/?code=N05AA01)
- [Xeplion SmPC §4.2](https://www.medicines.org.uk/emc/product/7652/smpc)
- [Trevicta SmPC §4.2](https://www.medicines.org.uk/emc/product/7230/smpc)
- [Byannli SmPC §4.2](https://www.medicines.org.uk/emc/product/13307/smpc)
- [Zypadhera SmPC §4.2](https://www.medicines.org.uk/emc/product/15651/smpc)
- [Okedi SmPC §4.2](https://www.medicines.org.uk/emc/product/13777/smpc)
- [Aripiprazole Otsuka 2개월 제형 SmPC](https://www.medicines.org.uk/emc/product/15678/smpc)

PP3M/PP6M의 경구 대응용량은 해당 제품의 PP1M 대응표와 Xeplion의 경구 대응표를
연결한 추정입니다. LAI 전용 MED 문헌인 Rothe et al. (2018), PMID 28735640의
olanzapine 기준은 주사제이므로, 현재 경구 OLZ 결과 열과 직접 혼합하지 않았습니다.

이는 연구용 추정이며 개인별 약물 전환 처방을 제시하지 않습니다.
