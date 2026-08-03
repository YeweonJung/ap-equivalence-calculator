# AP Equivalence Calculator

항정신병약물 등가용량을 CSV/Excel 파일에서 일괄 계산하는 Flask 웹앱입니다.

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
- 복용 빈도가 없으면 1일 1회로 계산되며 결과에 경고가 표시됩니다.

## Render 배포

이 저장소에는 Render Blueprint용 `render.yaml`이 포함되어 있습니다. Render Dashboard에서 **New > Blueprint**를 선택하고 이 GitHub 저장소를 연결하면 됩니다.

배포 후 `/health`가 `{"status":"ok"}`를 반환하면 정상입니다.

> 연구 및 교육 보조용이며 임상 판단을 대체하지 않습니다.
