# AP Equivalence Calculator

항정신병약물 등가용량을 CSV/Excel 파일에서 일괄 계산하는 Flask 웹앱입니다.

첨부된 하이브리드 약물 파서를 통합해 사전 정확 매칭, RapidFuzz 유사도 매칭,
미인식 약물 검토 표시를 지원합니다. 메인 화면에서 약물 문자열을 바로 테스트할 수 있고,
일괄 계산 결과의 `Detailed`·`AuditTrail` 시트에 매칭 방식과 유사도가 함께 저장됩니다.
웹 화면에서 업로드하면 CMD·MED·ED95·DDD·CPZ_FGA 중 해당 약물에 존재하는 모든 환산값을 한 결과 파일에 생성합니다.

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
- 숫자 빈도 `1`~`4`, `1일 2회`, `매일`, `2mg 2정 BID` 같은 표기도 인식합니다.
- 복용 빈도가 없으면 1일 1회로 계산되며 결과에 경고가 표시됩니다.
- 결과에는 원본 시트·행 번호·약물 열 이름이 기록되어 검토 항목을 원본에서 바로 찾을 수 있습니다.

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
