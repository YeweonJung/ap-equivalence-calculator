# 공개 처방 표기 검증

2026-10-19. [MIMIC-IV Clinical Database Demo v2.2](https://physionet.org/content/mimic-iv-demo/2.2/)의 공개 `hosp/prescriptions.csv.gz`를 사용했다. Johnson A, Bulgarelli L, Pollard T, Horng S, Celi LA, Mark R (2023), DOI: [10.13026/dp1f-ex47](https://doi.org/10.13026/dp1f-ex47). 공개 데모의 라이선스는 [ODbL 1.0](https://opendatacommons.org/licenses/odbl/1-0/)이다.

## 범위

- 원본 18,087행에서 항정신병약 이름에 해당하는 145행을 선택했다. 약물 정보 6개 필드 조합은 75개였다.
- 환자 ID, 진료일, 입원 정보, 진단은 검증 요청에 포함하지 않았다. `PUBLIC001` 등의 ID는 새로 부여한 시험용 번호다.
- 사용 필드: `drug`, `prod_strength`, `dose_val_rx`, `dose_unit_rx`, `doses_per_24_hrs`, `route`. `prod_strength`는 원자료 조합을 구분하는 용도로만 보관하고 계산 입력에는 넣지 않았다.
- [공식 필드 정의](https://mimic.mit.edu/docs/iv/modules/hosp/prescriptions.html)에 따라 처방 용량과 하루 횟수를 사용했다. 제품 함량·불출 정 수·처방 기간으로 용량이나 빈도를 추정하지 않았다. 하루 횟수는 `N times a day`로 명시했다.
- 한 줄 계산과 CSV 업로드를 함께 점검했다. 정상 입력은 일일 mg, 약물명과 경로를 확인했다. 주사·범위 용량·0회 표기는 보류, 빈도 누락은 기존 가정 및 검토 표시를 확인했다. 환산계수의 임상적 타당성을 검증하는 연구는 아니다.

## 발견과 수정

`QUEtiapine Fumarate 100mg PO/NG 2 times a day`에서 `NG 2 times a day`를 두 번째 약물로 분리하여 하루 횟수가 사라지는 오류를 재현했다. `IV 1 times a day`도 같은 원인으로 분리되어 주사제가 경구 처방으로 처리될 수 있었다.

알려진 경로 표기는 뒤따르는 숫자와 함께 원래 약물에 유지하도록 수정했다. 다른 약물이나 미확인 약물의 경계는 유지한다. 0회 등 잘못된 빈도도 잘려 나가지 않고 검토 대상으로 남는다. 수정 전 실제 배포에서 계산/Excel 각각 20/75개가 기준을 만족했고, 수정 후 로컬 검증은 각각 75/75개를 만족했다. 이는 선택한 공개 표기의 개발 검증 결과이며 전체 실제 처방 정확도나 임상 검증 결과가 아니다.

민감도 분석 기능은 제공하지 않는다. 화면의 선택 항목과 추가 분석 모듈을 제거했으며 다운로드 결과는 기존 6개 시트를 유지한다.

## 재현

공개 원본을 내려받은 뒤 아래와 같이 실행한다. 원본과 결과 파일은 저장소에 넣지 않는다. 도구는 원본 SHA-256을 확인하고 약물 필드만 추린 CSV를 만든다. 외부 모델이나 피드백 학습에는 전송하지 않는다.

```text
python scripts/verify_public_prescriptions.py --source prescriptions.csv.gz --output output/public-local/report.json
python scripts/verify_public_prescriptions.py --source prescriptions.csv.gz --base https://ap-equivalence-calculator.onrender.com --commit TARGET_COMMIT --output output/public-live/report.json
```

실제 배포 검증은 지정한 커밋이 `/version`에 표시된 뒤 진행한다. `report.json`은 사례별 실패 사유와 Excel 시트 구성을 기록한다. 입력 CSV와 받은 Excel을 같은 결과 폴더에 저장한다. 테스트 ID 및 약물 표기만 포함한 중간 산출물도 공개 자료 라이선스에 따라 취급한다.
