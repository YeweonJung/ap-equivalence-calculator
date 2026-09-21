# 약물명 검색 코드 공유 안내

## 검색 로직을 설명하거나 리뷰받으려면

1. [services/candidate_retrieval.py](../services/candidate_retrieval.py): 핵심 검색 코드. 한글 NFD 자모 분해, 편집거리, 채널별 gate, 후보 union, target 중복 제거, 상한과 provenance.
2. [services/manual_suggestions.py](../services/manual_suggestions.py): 실제 앱 연결. 활성 채널, 수동 확인용 후보, UI 설명, 기존 baseline fallback.
3. [tests/test_candidate_retrieval.py](../tests/test_candidate_retrieval.py), [tests/test_manual_suggestions.py](../tests/test_manual_suggestions.py): 검색 규칙과 실제 API·Excel 연결 테스트.

첫 번째 파일만 공유해도 핵심 알고리즘은 볼 수 있다. 단독 실행 파일은 아니므로 재현·수정·실행이 목적이면 저장소 전체를 공유한다.

## 실행까지 재현하려면

저장소: https://github.com/YeweonJung/ap-equivalence-calculator

GitHub의 Code → Download ZIP 또는 git clone으로 받는다. 검색 코드는 name_dictionary/name_distance/name_features/name_ranker/drug_suggestions에 의존하고, 이들은 기존 parser/LAI 사전 및 lookup 파일을 함께 참조한다. 앱 실행에는 app.py, templates, static, requirements.txt도 필요하다. 파일을 몇 개만 복사하면 사전·설정 누락으로 동작하지 않을 수 있다.

운영 실행 의존성은 requirements.txt, 학습 재현·전체 개발 검사 의존성은 requirements-ranker.txt다. 모델 JSON은 함께 보관되지만 현재 앱 추천은 LR 모델을 사용하지 않는다.

## 학습한 LR 모델을 별도로 설명하려면

- [services/name_features.py](../services/name_features.py): 입력과 후보의 특징 추출.
- [services/name_ranker.py](../services/name_ranker.py): 로컬 LR 추론과 보류 정책.
- [scripts/train_name_ranker.py](../scripts/train_name_ranker.py): 학습 코드.
- `models/name_ranker/`: 학습된 계수·설정·metadata.
- [평가 보고서](CANDIDATE_RETRIEVAL_REPORT_KO.md): 오프라인 성능과 한계. 현재 운영 채널 변경은 [앱 릴리스 문서](CANDIDATE_RETRIEVAL_APP_RELEASE_KO.md)를 함께 읽는다.

자모 검색은 문자열 처리 알고리즘이며 학습한 LR 모델과 구분한다. 저장소에는 합성 평가 데이터만 포함한다. 로컬 .env나 비공개 피드백·환자정보는 공유 파일에 추가하지 않는다.
