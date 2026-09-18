최신 업데이트: [Woods·Gardner·LAI 변환과 검증 안내](EQUIVALENCE_UPDATE.md).

# AP Equivalence Calculator

항정신병약물 등가용량을 CSV/Excel 파일에서 일괄 계산하는 Flask 웹앱입니다.

첨부된 하이브리드 약물 파서를 통합해 사전 정확 매칭, RapidFuzz 유사도 매칭,
미인식 약물 검토 표시를 지원합니다. 메인 화면에서 약물 문자열을 바로 테스트할 수 있고,
일괄 계산 결과의 `Detailed`·`AuditTrail` 시트에 매칭 방식과 유사도가 함께 저장됩니다.
웹 화면에서 업로드하면 CMD·MED·ED95·DDD·CPZ_FGA·WOODS·GARDNER 중 해당 약물에 존재하는 모든 환산값을 한 결과 파일에 생성합니다.

파싱 알고리즘의 선택 이유, 대안별 장단점, 코드 단계, 2,000명 데이터 평가 계획은
[`PARSING_METHODS_KO.md`](PARSING_METHODS_KO.md)에 정리되어 있습니다.

## 로컬 실행

```bash
pip install -r requirements.txt
python app.py
```

브라우저에서 `http://localhost:5000`을 엽니다.

## 입력 형식

- 파일: `.csv`, `.xls`, `.xlsx` (최대 100MB, Excel은 최대 5개 시트)
- 약물 열 이름: `drug`, `medication`, `medications`, `rx`, `prescription`, `medicine` 중 하나 포함
- 약물 값 예시: `Risperdal 2mg BID, Abilify 15mg QD`
- 약물명·용량·단위·빈도가 각각 다른 열인 파일도 자동 결합합니다. 예: `drug,dose,unit,frequency`
- 대소문자, 유니코드, 공백, 장식용 기호를 정규화하고 정확 사전 매칭 후 보수적 유사도 매칭을 적용합니다.
- 숫자 빈도 `1`~`4`, `1일 2회`, `2회/일`, `q12h`, `1-0-1`, `매일`, `2mg 2정 BID` 같은 표기도 인식합니다.
- `제품명`, `성분명`, `약품명`, `함량`, `1회용량`, `일일횟수` 등 병원 추출 파일의 일반적인 한글 열 이름도 자동 탐지합니다.
- 복용 빈도가 없으면 1일 1회로 계산되며 결과에 경고가 표시됩니다.
- 결과에는 원본 시트·행 번호·약물 열 이름이 기록되어 검토 항목을 원본에서 바로 찾을 수 있습니다.
- 선택한 환산법 중 해당 약물에 값이 없는 방법은 `AuditTrail.unavailable_methods`에 기록됩니다.

## Render 배포

이 저장소에는 Render Blueprint용 `render.yaml`이 포함되어 있습니다. Render Dashboard에서 **New > Blueprint**를 선택하고 이 GitHub 저장소를 연결하면 됩니다.

배포 후 `/health`가 `{"status":"ok"}`를 반환하면 정상입니다.

> 연구 및 교육 보조용이며 임상 판단을 대체하지 않습니다.

## 환산값 해석 제한

- CMD: Leucht et al. 2015, PMID 25841041
- MED: Leucht et al. 2014, PMID 24493852
- ED95: Leucht et al. 2020, PMID 31838873
- DDD: WHO ATC/DDD 방법론에 따른 약물사용 연구용 기술 단위
- CPZ_FGA: Davis 1974, PMID 4156792의 역사적 CPZ 비교값

환산 방법들은 서로 다른 연구 설계와 환자 집단에 기반하며 개인별 권장용량이나
약물 변경 지시가 아닙니다. 빈도 미기재, fuzzy 매칭, PRN, 장기지속형 주사제와 주 단위 처방은
확정값으로 취급하지 않고 검토 경고 또는 오류로 분리합니다.


## 약물 Frame 개선 (2026-09-11)

- 괄호 밖의 쉼표·세미콜론·줄바꿈·+에서만 분리하며 괄호 불일치는 검토로 남깁니다.
- `ris 2mg olz 5mg`처럼 구분자가 없는 입력도 약물별 Frame으로 나눕니다.
- `drug1,dose1,unit1,frequency1,drug2,dose2,unit2,frequency2` 형태를 지원합니다. 번호가 같은 열끼리 연결합니다.
- `arp`, `hd`, `olan`, `pariperidone` 별칭과 Blonanserin, Escitalopram, Benztropine, Lithium을 등록했습니다.
- `olz15` 등은 단위가 없으면 mg으로 계산하고 Errors에 확인바람을 기록합니다.
- `mgs`, `milligram(s)`, `밀리그램`은 mg로 정규화합니다. 다른 단위 오타는 `unit_candidates`에 유사 후보만 표시하며 자동 적용하지 않습니다.
- PP1M/PP3M/PP6M, LAI, IM, 주사 등의 투여경로·제형·간격 표기를 보존합니다. 주사 질량/일에 경구 환산계수를 직접 적용하지 않습니다.
- `AuditTrail`은 환산 성공뿐 아니라 모든 Frame을 보존합니다. `status`는 converted, non_target, unknown_drug, missing_unit, unsupported_formulation, missing_factor, review로 구분합니다.
- 환산 대상이 아닌 병용약과 계수 없는 약물은 0으로 처리하지 않습니다. Blonanserin의 환산계수는 추가하지 않았습니다.
- Excel의 `method_warning`, `limitation` 항목을 제거했습니다. MethodInfo의 방법명과 출처는 유지합니다.
- Frame의 source_start/source_end는 original이 추출된 파싱 입력의 문자 위치(0 기반, 끝 제외)입니다. 별도 열을 결합한 경우 결합 문자열 기준입니다.

검증: `python -B -m pytest tests -q -p no:cacheprovider`

## 셀별 환산 합계
동일 셀의 약물을 각각 환산하고 웹 화면과 Excel CellTotals 시트에 환산법·기준 약물별 합계를 표시합니다. 미환산 약물이 있으면 총합은 빈값이고 계산된 약물만 부분합으로 표시합니다. RIS,OLZ처럼 숫자 용량 자체가 없으면 합계를 계산하지 않습니다. 환산 대상이 아닌 병용약은 제외 건수로 기록합니다. 서로 다른 행이나 약물 열은 합치지 않습니다.

별도 열에서 drug=`Risperdal,OLA`, dose=`6,5`, unit=`MG`, frequency=`BID`를 입력하면 순서대로 연결하고 공통 단위·빈도를 적용합니다. 약물과 용량 개수가 다르면 검토 대상으로 남깁니다. B 등 미지원 빈도는 QD로 가정하지 않습니다.


## 결과 시트와 주사제 DDD (2026-09-14)

`Results`가 첫 시트입니다. original 원문과 약물별 환산값, 같은 셀의 총 환산값을 CMD, MED, ED95, DDD, CPZ_FGA 순으로 표시합니다. 총합은 각 셀의 첫 약물 행에만 표시합니다. 미지원 약물/방법의 값은 실제 빈 셀로 남기며, 하나라도 환산하지 못하면 그 방법의 총합도 비웁니다. 부분합은 기존 CellTotals에서만 확인합니다.

단위가 생략된 숫자 용량은 mg으로 계산하며 `unit_assumed=True`와 `확인바람: 단위 미기재로 mg 가정`을 Errors/AuditTrail에 기록합니다. 숫자 자체가 없거나 `.G`, `gm`처럼 명시된 불명확한 단위는 mg으로 덮어쓰지 않습니다.

지속형 주사제는 WHO의 투여경로별 DDD로 계산합니다. 현재 depot DDD는 paliperidone 활성성분 2.5 mg/day, aripiprazole 13.3 mg/day, risperidone 2.7 mg/day, olanzapine 10 mg/day입니다. 주사량/투여간격/주사제 DDD × chlorpromazine 경구 DDD 300 mg으로 계산합니다. 다른 방법은 제품별 경구 대응용량이 명확하고 기존 계수가 있는 경우에 한해 추정값으로 표시합니다. [LAI 지원 범위와 출처](LAI_METHODS.md)를 확인하세요.

- `paliperidone 100mg PP1M`: 100/30/2.5×300 = 400 CPZ mg/day (DDD).
- `aripiprazole 400mg LAI q4w`: 400/28/13.3×300 CPZ mg/day.
- PP1M/PP3M/PP6M은 각각 30/90/180일, 월 단위는 30일/월의 연구 계산 기준입니다. q4w는 28일로 구분합니다. 간격 없는 LAI는 추정하지 않습니다.
- paliperidone은 활성성분 mg 표기 기준입니다. 제품·제형에 맞는 palmitate 표시량은 활성성분으로 변환하며 표시기준 검토 경고를 남깁니다.
- 부하·초기·PRN 용법과 상충 간격은 검토 대상으로 남깁니다. 유지요법을 전제로 한 계산임을 경고로 보존합니다.
- `LAI둘다`는 셀의 약물들에 주사제 표시를 적용하고 각 약물의 제형·간격 확인을 요청합니다.
- 약물별 일일 주사량은 투여간격으로 나눈 평균량이며 경구 투여량이 아닙니다.

계수 출처 (확인일 2026-09-14; WHO index 갱신일 2026-01-20):
https://atcddd.fhi.no/atc_ddd_index/?code=N05AX&showdescription=yes
https://atcddd.fhi.no/atc_ddd_index/?code=N05AA01
결과 파일 InjectionInfo 시트에도 계수·출처·월 환산 기준을 기록합니다.


## 사용성 및 입력 검증 개선 (2026-09-18)

- 한 줄 계산 결과를 `이 결과 Excel 저장`으로 저장한다. 파일 업로드와 동일한
  출력 모듈을 사용하며 미인식 처방, 부분합, 원자료 및 검토표도 포함한다.
- 웹 결과는 7개 방법을 모두 표시하고 미지원 계수/경구 대응량 사유를 표시한다.
- 화면 용량은 소수점 최대 4자리로 표시하며 실제 환산계수는 변경하지 않았다.
- 입력을 수정하면 진행 중인 요청을 취소하고 오래된 응답은 반영하지 않는다.
- 한 줄 입력은 10,000자와 문자열 형식으로 제한한다. 파일 업로드 범위는 기존과 같다.
- CSV 구분자는 헤더의 쉼표·세미콜론·탭·파이프만 탐지한다.
  단일 열 CSV에서 약물명 일부가 구분자로 오인되던 문제를 수정했다.
- 검증: Python 150개 테스트와 JavaScript 요청 순서/표시/문자 이스케이프 검사.


## 2026-09-18 글자별 오타 검토 및 추가 분석

영문 삽입·삭제·교체·순서 교환 오타 후보에 위치와 차이를 표시하고, 선택 전 환산하지 않습니다. Excel에도 후보를 보존합니다. CMD_DIRECT와 CMD_INDIRECT를 추가해 총 9개 분석을 출력합니다. 두 분석은 Leucht 2015 연구의 별도 비교 분석이며 기본 단위는 OLZ mg/day입니다. 상세 근거와 제한은 [설명 문서](docs/character_matching_and_cmd.md)를 참고하세요.
