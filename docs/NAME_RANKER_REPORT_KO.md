# 약물명 후보 순위 모델 구현·평가 보고서

작성: 2026-09-21. 모델 `name-logistic-v1`, 합성 데이터 `synthetic-name-v1`, seed `20260921`.

**결론: 로컬 학습·추론·평가 코드를 추가했지만, 앱의 기본 추천은 기존 편집거리 방식으로 유지한다.** 합성 테스트에서 ML의 Top-1이 기존 방식보다 좋아지지 않았다. 약물 환산 공식, 등가용량표, 용량·빈도 파서, 기존 테스트는 변경하지 않았다. 새 모델은 외부 AI API나 사전학습 모델을 사용하지 않으며, scikit-learn으로 현재 사전에서 만든 데이터를 직접 학습한다. scikit-learn의 학습 알고리즘 구현을 사용하는 것이므로 최적화 알고리즘까지 새로 작성한 것은 아니다.

## A. 기존 시스템과 연결 위치

- `app.py`의 `/api/parse` → `services/frames.py`의 `parse_frames` → 기존 `convert_frame` 환산 경로.
- 등록된 성분명·제품명·alias를 먼저 인식하고, 용량·빈도를 기존 규칙으로 해석한다.
- 미확인 이름에만 `services/drug_suggestions.py`가 문자별 OSA 편집거리 후보를 제시한다. 사용자가 후보를 선택해 수정 입력을 다시 제출해야 환산으로 진행한다.
- CSV/Excel도 frames/환산 경로를 사용하며 후보는 검토용 정보로 남는다. 추천 후보 자체가 약물 확정값이 되지 않는다.
- 사전은 `lookup/drug_alias.csv`, 파서의 `alias_map`, `name_distance.BRANDS`, `lai_support.PRODUCTS`의 기존 정보를 읽는다. 모델용 사전은 기존 후보 추천의 필터를 유지한 읽기 전용 뷰다.
- 저장소에 `llm_client.py`, `llm_batch_parser.py`라는 과거 외부 LLM 코드가 있지만 현재 조사한 앱 실행 경로에서는 호출하지 않는다. 새 ranker에서도 호출하지 않는다.

새 실험 경로: 이름 분리 → 기존 거리 규칙으로 최대 20개 후보 검색 → 26개 특징 → StandardScaler + LogisticRegression → 순위 점수 → 보류 사유. **`confirmed_drug=None`, `auto_accepted=False`를 항상 반환한다.**

## B. 수정한 기존 파일

| 파일 | 변경 |
|---|---|
| `services/drug_suggestions.py` | 기존 함수 본문을 `baseline_suggestions`로 보존. 별도 후보 생성 함수와 기본값 baseline인 선택 래퍼 추가 |
| `.gitignore` | 향후 비공개 피드백 및 외부 데이터 임시 보관 폴더 제외 |

기존 환산·파싱·UI·데이터베이스 파일은 변경하지 않았다. 기본 serving 의존성에도 sklearn을 추가하지 않았다.

## C. 새 파일

| 파일/경로 | 용도 |
|---|---|
| `services/name_dictionary.py` | 등록 후보, 정규화, 제형, 사전 해시 |
| `services/name_features.py` | 문자열·자모·제형 특징 |
| `services/name_ranker.py` | JSON 모델 검증, 로컬 추론, 순위, 보류 |
| `services/name_feedback.py` | 비식별 확인을 요구하는 오프라인 피드백 구조 |
| `services/drug_data_sources.py` | 향후 공식 데이터의 출처·버전·이용조건 기록과 별도 임시 저장 구조 |
| `scripts/make_typo_examples.py` | 합성 입력 생성과 성분 단위 분할 |
| `scripts/train_name_ranker.py` | 학습·검증 세트 기반 임계값 선택·모델 저장 |
| `scripts/evaluate_name_ranker.py` | 고정 테스트 세트의 baseline/ML 비교 |
| `scripts/ranker_experiment.py` | 검색·순위·정책 지표와 사례별 결과 |
| `scripts/review_drug_name.py` | 저장·환산 없이 후보 JSON을 보는 로컬 CLI |
| `models/name_ranker/config.json` | seed, K, 학습 설정, 임계값 후보, 기본 보류 정책 |
| `models/name_ranker/model.json` | 표준화 계수·로지스틱 회귀 가중치. pickle 사용 안 함 |
| `models/name_ranker/metadata.json` | 버전·학습일·특징·표본 수·해시·임계값·평가·배포 비활성 상태 |
| `data/name_ranker/synthetic.jsonl`, `dataset_metadata.json` | 합성 입력, split, 출처와 해시 |
| `data/name_ranker/training_pairs.jsonl` | train 입력에서 만든 positive/negative 후보 쌍 |
| `data/name_ranker/validation_policy_search.json` | validation에서만 실행한 정책 탐색 |
| `data/name_ranker/evaluation.json` | 전체 지표, 오류 유형별 지표, 테스트 개별 사례 |
| `requirements-ranker.txt` | 학습용 의존성. scikit-learn 1.7.2 |
| `tests/test_name_ranker.py` | 새 회귀·안전·재현성 테스트 |
| `docs/NAME_RANKER_REPORT_KO.md` | 이 보고서 |

## D. 입력 특징과 출력

26개 특징: Levenshtein, OSA, 길이로 나눈 OSA, 삽입·삭제·교체·순서변경 횟수, 길이 차이, 공통 접두·접미 길이 비율, 2/3-gram Jaccard, 문자집합 Jaccard, SequenceMatcher, 성분명 일치/부분일치, 제품명 일치/부분일치, alias 일치, 정규화 일치, 한글 존재, NFD 자모 유사도, 문자 체계 일치, 경로 정보 존재, 경로 일치, 제형 충돌.

출력에는 등록 후보 성분/alias, `ranking_score`, `rank`, `prediction_source`, `confidence`, `status`, `abstention_reasons`, 모델·사전 버전을 제공한다. 후보별 점수는 **보정되지 않은 순위 점수이며 실제 정답 확률이 아니다.** 현재 앱 UI는 baseline 유지이므로 이 점수를 확률처럼 표시하는 UI도 추가하지 않았다.

영문 대소문자/문장부호 정규화와 한글 자모 비교는 지원한다. 한/영 키보드 모드를 잘못 켜 입력한 문자를 서로 변환하는 기능은 이번에 구현하지 않았다. 후보 생성은 한글/영문 문자 체계를 구분한다. XR/ER 등은 이름과 분리하지만 모든 약의 서방/속방 적합성을 판정하는 제형 DB는 아니다. 정보가 없는 성분의 투여경로를 임의로 경구로 채우지 않는다.

## E. 합성 데이터

기존 등록 alias에 삭제·삽입·중복·교체·인접 순서변경·영문 인접키·대소문자·공백·hyphen·XR 혼합·한글 모음 자모 변형을 적용했다. 정상 입력, 알려진 제품의 반대 투여경로, 무작위 미등록 문자열도 포함한다.

총 **1,840개 입력**. train 1,223개에서 **7,697개 후보 쌍**(양성 1,551, 음성 6,146)을 만들었다. 실제 검색 후보에 철자가 가까운 다른 target의 hard negative 최대 5개를 추가했다. 학습에 한해서 검색에 실패한 정답 alias도 양성 쌍으로 넣었다. **평가에서는 정답 후보를 주입하지 않는다.**

입력 뒤의 `1mg QD`, `1mg LAI q4w`는 이름 파이프라인을 시험하는 합성 문자열이다. 실제 투여량·스케줄을 뜻하지 않으며 모델이 학습하거나 생성하는 용량이 아니다. 실제 처방이나 환자정보는 사용하지 않았다. 중복 제거 과정에서 각 split에 공통으로 넣었던 `qx` 짧은 미등록 사례는 제거되었다. 짧은 입력은 별도 단위 테스트로 검증했고, 테스트 세트에는 삭제로 짧아진 약물명 사례가 있다.

## F. 분할·학습·재현성

오타 생성 전에 성분을 seed로 섞어 약 60/20/20으로 나눴다. 같은 성분의 제품명·한글명·alias는 모두 같은 split에 둔다. 성분당 alias 수가 다르므로 입력 개수 비율은 정확히 60/20/20이 아니다. train/validation/test는 **1,223 / 370 / 247개**다. split 간 성분과 동일 입력의 중복이 없음을 테스트했다.

공통 사전은 후보 검색용 참조 어휘다. 다른 split 성분도 hard negative 후보가 될 수 있지만 해당 성분의 테스트 오타·정답 쌍을 학습 입력으로 가져오지는 않는다. 따라서 미등록 신약 일반화를 평가하는 실험은 아니다.

StandardScaler와 회귀 계수는 train에서만 fit. LogisticRegression은 `C=1`, `lbfgs`, `max_iter=2000`, `class_weight=balanced`. validation에서 허용 오류 0건, 최소 정책 통과 20건 조건으로 통과 수를 최대화했다. 선택값은 **threshold 0.95, distinct-target margin 0.25, 최소 이름 길이 4, K=20**. 테스트는 fit/임계값 선택에 사용하지 않았다.

모델·사전·데이터 SHA256과 feature 버전을 남겼다. 동일 seed 재생성 및 sklearn 재학습 계수/JSON 추론 일치 테스트가 통과했다. 학습일은 재실행할 때 갱신된다. 다른 Python/수치 라이브러리 버전에서는 작은 수치 차이가 가능하다. 특징의 의미를 바꾸면 feature 버전도 올리고 재학습해야 한다.

## G–J. 기존 방식, ML, 검색률, 순위 성능

고정 테스트 **247개 = 정답 target 있는 입력 227개 + 미등록 입력 20개**. target은 성분과 LAI 제품 profile의 조합이며, 동일 성분이라도 다른 depot profile은 정답으로 합치지 않는다. 순위 지표에서는 같은 target의 alias 중복만 묶는다.

| 지표 | 기존 edit-distance | Logistic ranker |
|---|---:|---:|
| Candidate recall@1 | 98.24% (223/227) | 98.24% |
| Candidate recall@3 / @5 / @20 | 98.68% (224/227) | 98.68% |
| Top-1, 전체 알려진 입력 기준 | 98.24% (223/227) | 98.24% |
| Top-3 / Top-5 | 98.68% (224/227) | 98.68% |
| 정답 검색 성공 조건부 Top-1 | 99.55% (223/224) | 99.55% |

기존 함수를 그대로 실행한 `legacy_baseline`과 새 공통 후보 풀에 기존 점수 순서를 적용한 `baseline`을 모두 평가했으며 이번 세트에서는 지표가 같았다. 검색 recall은 순위 모델 적용 전 raw alias K개 기준이다. Top-1은 검색 실패도 오답에 포함한다. 이것은 **이름 식별의 end-to-end 정확도**이지 임상 처방 전체 환산 성공률이 아니다.

오류 분석: `로핀`, `조핀`, `지돈`은 삭제 후 2글자가 되어 검색에서 제외되었고, `로나핀`은 정답 zotepine 후보가 있었지만 blonanserin 후보가 1위였다. 네 사례 모두 정책에서 보류되었다. 삭제 유형 Top-1은 18/21(85.71%), 교체는 20/21(95.24%)이며 다른 알려진 유형은 이번 작은 세트에서 100%였다. 정상·대소문자·공백 사례도 포함된 전체 평균만으로 복잡한 실제 오타 성능을 주장할 수 없다.

개선되지 않은 이유: 검색 후보가 이미 좁고 조건부 baseline 정확도가 높다. 검색에서 빠진 3건을 순위 모델로 복구할 수 없으며, 남은 1건도 분리하지 못했다. 학습 특징 상당수가 기존 거리와 겹치고 합성 오류가 단순하다. **ML을 production 추천으로 승격하지 않는다.**

## K–L. 잘못된 자동확정·보류·coverage

다음 표는 연구용 정책 시뮬레이션이다. 앱에서 실행되는 자동확정이 아니다. 전체 247개에 미등록/제형 충돌도 포함한다. 올바른 성분이어도 명시적 제형 충돌이면 정책 통과를 오류로 센다.

| 시뮬레이션 지표 | baseline 정책 | ML 정책 |
|---|---:|---:|
| 정책 통과 | 85/247 | 191/247 |
| 잘못된 통과 / 전체 | 0/247 (0%) | 0/247 (0%) |
| 통과 사례 중 정답률 | 85/85 (100%) | 191/191 (100%) |
| 보류율 | 65.59% | 22.67% |
| Coverage | 34.41% | 77.33% |

baseline 임계값은 설정한 휴리스틱(0.95, margin 0.15), ML 임계값은 validation에서 선택했다. 두 점수 척도도 다르므로 coverage 차이를 모델 정확도 향상이나 공정한 최적 정책 비교로 해석하지 않는다. 무작위 미등록 문자열이 실제 약물과 비슷한 미등록 입력보다 쉬울 수 있다.

**실제 정책은 모든 추정 후보에 사용자 확인을 요구한다.** 자동확정 coverage 0%, 자동확정 보류율 100%, 자동 오확정 0건. 자동확정 중 정확도는 분모 0으로 계산 불가(null)다. 이 0건은 자동화를 꺼 둔 구조의 결과이며 안전성을 실증한 수치가 아니다. 사용자가 선택한 후보의 실제 정답률도 아직 측정하지 않았다.

## M. 기존 테스트

기존 pytest 테스트 **165개 모두 통과**. 환산, LAI, 프레임, 업로드/빠른 검사, 내보내기, 문자별 검토 등 기존 테스트 파일은 수정하지 않았다. 기존 Node UI 검사도 통과(요청 순서, 반올림, 누락 factor, HTML escaping).

## N. 새 테스트

새 pytest **33개 통과**, 전체 **198 passed**. 정상/전치/삭제/중복 후보, 문자 편집 특징, 보류/미등록/짧은 입력/제형 충돌, 근접 후보, 가짜 후보 거부, suffix 보존, 비활성·미승인·누락 모델 fallback, 해시/feature 버전 불일치 거부, split 누출 방지, 재현성, 학습 쌍 범위, 검색 실패 분모, sklearn와 JSON 추론 일치, 피드백 비식별 확인과 허용 필드, 외부 데이터 provenance를 검사했다.

## O. 검증하지 못한 부분

- 실제 병원 처방, 약물과 비슷한 미등록 단어, 여러 오타가 겹친 입력, 기관별 약칭, 복합제, 한/영 키보드 전환, OCR 오류 분포.
- 약품코드(EDI/KD) 새 매핑, 모든 제형/제품의 표준화·정확성. 기존 사전 자체가 오기/불완전성을 가질 수 있다.
- calibrated probability, 기관·시점별 외부검증, 실제 임상 오류율 및 환자 결과.
- 문자열만으로 환자 이름인지 판별할 수 없다. 피드백 helper는 별도 비식별 확인을 요구하며 웹 요청을 자동 저장하지 않는다. 전체 처방을 넣으면 안 된다.
- 공식 외부 데이터는 **다운로드하지 않았다.** MFDS/RxNorm은 향후 adapter를 붙일 수 있는 출처·환경변수·별도 staging 구조만 있다. 실제 API 필드 매핑, 이용조건 검토, EDI/KD 연결은 후속 작업이다. `retrieved_at`은 현재 helper가 전달받은 레코드를 staging한 시각이다.

## P. 실제 데이터 확보 후

1. 기관 승인을 거쳐 약물명 토큰만 비식별 추출한다. 환자 ID/자유서술/용량 포함 처방 원문은 피드백에 저장하지 않는다.
2. 입력, 후보 목록/점수, 사용자가 선택한 등록 후보, 수동 확인 여부, 시각, 모델·사전 버전을 기록한다. 현재 helper는 기본 비활성 오프라인 기능이며 `pending_second_review`, `eligible_for_training=False`로 저장한다.
3. 두 검토자가 독립적으로 성분·제품·제형을 주석화하고 불일치를 조정한다. 사용자 클릭을 곧바로 정답으로 취급하지 않는다.
4. 기관/시간/성분 단위 holdout을 설계하고, 어려운 미등록·유사명·제형 충돌·짧은 약칭 사례를 충분히 확보한다. 테스트를 반복 튜닝에 쓰지 않는다.
5. 검색 누락과 순위 오류를 각각 분석하고 baseline과 같은 평가 조건에서 비교한다. 필요하면 후보 검색의 자모 특징부터 개선하되 짧은 이름 오확정 증가를 함께 측정한다.
6. 검토 완료 피드백만 별도 학습 버전으로 편입한다. 점수 보정은 분리된 calibration 세트에서 수행하고, 보류/coverage 곡선과 오류율 신뢰구간을 평가한다.
7. 먼저 shadow mode로 비교한다. 실제 자료의 개선과 검토 승인 전까지 `production_enabled=false`를 유지한다. 재학습이나 평가 스크립트는 자동 승격하지 않는다.

## 실행 방법

프로젝트 루트에서 실행한다. 학습 관련 패키지는 별도 개발 환경에 설치하는 편이 좋다.

```powershell
python -m pip install -r requirements-ranker.txt
python scripts/make_typo_examples.py
python scripts/train_name_ranker.py
python scripts/evaluate_name_ranker.py
python scripts/review_drug_name.py risperidnoe
python -m pytest -q
node tests/quick_check_ui.cjs
```

`review_drug_name.py`는 실험 모델의 등록 후보와 보류 상태만 출력한다. 앱 활성화에는 환경변수와 모델 metadata의 승인 상태가 모두 필요하다. 이번 metadata는 비승인이므로 환경변수만 설정해도 baseline을 유지한다. 실제 앱 환산은 기존 함수로 수행하며 모델이 용량·빈도를 채우거나 수정하지 않는다.
