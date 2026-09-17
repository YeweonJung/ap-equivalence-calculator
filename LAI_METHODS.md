최신 추가 지원(Aristada, palmitate 표시량, Woods/Gardner): [업데이트 안내](EQUIVALENCE_UPDATE.md).

# LAI 환산 지원

## 계산 기준

DDD는 WHO의 주사제 전용 DDD를 사용합니다. CPZ 경구 DDD 300mg을 기준으로
`투여용량 / 투여간격(일) / 주사제 DDD × 300`을 계산합니다.

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
