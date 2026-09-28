최신 업데이트: [Woods·Gardner·LAI 변환과 검증 안내](EQUIVALENCE_UPDATE.md).

# AP Equivalence Calculator

항정신병약물 등가용량을 CSV/Excel 파일에서 일괄 계산하는 Flask 웹앱입니다.

등록 사전과 사용자가 확정한 별칭으로 약물을 식별하고, 미인식 약물은 확인 대상으로 표시합니다. 메인 화면에서 약물 문자열을 바로 테스트할 수 있고,
결과는 `Results`(요약), `MedicationResults`(약물별 상세), `Review`(확인 필요), `AuditTrail`(처리 기록) 4개 시트만 제공합니다. 숨겨진 시트는 없습니다.
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
- 대소문자, 유니코드, 공백, 장식용 기호를 정규화하고 등록된 이름만 계산합니다.
- 숫자 빈도 `1`~`4`, `1일 2회`, `2회/일`, `q12h`, `1-0-1`, `매일`, `2mg 2정 BID` 같은 표기도 인식합니다.
- `제품명`, `성분명`, `약품명`, `함량`, `1회용량`, `일일횟수` 등 병원 추출 파일의 일반적인 한글 열 이름도 자동 탐지합니다.
- 복용 빈도가 없으면 1일 1회로 계산되며 결과에 경고가 표시됩니다.
- 결과에는 원본 시트·행 번호·약물 열 이름이 기록되어 검토 항목을 원본에서 바로 찾을 수 있습니다.
- 선택한 환산법 중 해당 약물에 값이 없는 방법은 상세의 환산 근거와 `Review`에 기록됩니다.

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


## 결과와 실행 속도 (2026-09-28)

- `Results`: 환자·처방일당 한 행의 합계, CPZ/OLZ 색상 구분, 환산 상태와 짧은 확인 사항. 날짜가 없는 파일은 환자별 합산입니다.
- `MedicationResults`: 약물당 한 행의 환산값과 원문·원본 위치·확인 사유. 중복 총합 열은 제외합니다.
- `AuditTrail`: 성공·미환산·제외 기록을 모두 포함합니다. 원본 위치, 해석된 성분과 용량, 단위·빈도 가정, 주사제 질량과 경구 대응 근거, 미지원 방법을 추적합니다. 날짜별 파일은 원본 처방마다 한 행이며 ID·날짜 오류가 있는 행도 보존합니다.
- `Review`: 미확인 약물, 누락 계수, 주사 간격, 가정 사항 등 확인할 기록만 표시합니다.
- 요약의 `—`와 상세의 빈 셀은 0이 아닙니다. 미환산 약물이 있는 방법의 총합은 비웁니다.
- 표시는 소수 2자리이며 계산된 원값은 보존합니다. 서로 다른 기준약물(CPZ/OLZ)의 값은 더하지 않습니다.
- 같은 환자라도 다른 처방일은 합산하지 않습니다. 처방기간이 겹쳐도 이전 날짜의 처방을 더하지 않습니다.
- 한 줄 계산·파일 업로드·내보내기는 자동 철자 후보 검색, AI 요청, AI 작업 대기를 하지 않습니다. 기존 `NAME_LLM_ENABLED=1` 설정으로도 다시 활성화되지 않습니다. 정확한 이름을 직접 수정한 후 다시 계산할 수 있습니다.
- Excel은 서식을 재사용하며 행 단위로 기록하고, 약물명 정규식도 한 번만 준비합니다. 환자별 입력이나 결과를 전역 캐시에 보관하지 않습니다.
- 환산표는 서버 시작 시 검사하고 메모리에 한 번 색인합니다. 환산계수나 약물별 계산식은 변경하지 않았습니다.
- 삭제된 시트: 별도 한눈에 보기, PatientChecks, Detailed, Errors, CellTotals, FactorSources, VersionInfo, ReviewQueue, MethodInfo, InjectionInfo. 요약은 Results에 통합했습니다.
- 저장소의 후보 검색·AI 평가 도구는 이전 실험용으로 남아 있지만 공개 계산 경로에서는 실행하지 않습니다.

환산 근거 및 주사제 제한은 [EQUIVALENCE_UPDATE.md](EQUIVALENCE_UPDATE.md), [LAI_METHODS.md](LAI_METHODS.md)를 참조하세요. 과거 문서의 출력 시트·자동 후보 검색 설명보다 이 문서의 현재 동작을 우선합니다.

검증: `python -m pytest tests -q`, `node tests/quick_check_ui.cjs`, `node tests/manual_suggestions_ui.cjs`.

등록된 항우울제는 항정신병약 환산에서 제외하고 환산값 0으로 표시합니다. 실제 복용량은 변경하지 않으며, 미확인 약물은 0으로 처리하지 않습니다. [등록 목록과 처리 규칙](docs/antidepressant-release-2026-09-28.md).
