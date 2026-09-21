# Phase 1 — 변경 전 검색 구조 감사

2026-09-21. 개선 코드 작성 전에 기록. 대상: `work/ranker_update`.

1. 앱은 `app.py`/`services/frames.py` → `suggest_drugs` → 기본 `baseline_suggestions`를 호출한다. 모델 환경변수와 production 승인이 모두 있어야 기존 ML 경로를 사용한다. 현재 승인은 false다.
2. 실험용 `generate_candidates`는 `name_and_suffix`로 첫 숫자 또는 공백 뒤 제형 토큰 앞까지 이름을 분리한다. 나머지 suffix는 그대로 보존한다. baseline은 숫자가 없으면 후보를 반환하지 않으며 분리하는 제형 목록도 더 짧다.
3. NFKC → casefold → `[a-z가-힣]` 이외 제거. 공백·구두점·분리된 자모가 제거된다. 한글 음절이 하나라도 있으면 Korean bucket이며 영문만 있는 alias와 비교하지 않는다. 키보드 모드 변환은 없다.
4. `generate_candidates`의 `if not 3 <= len(query) <= 40: return []`가 첫 검색 gate다. `records()`도 정규화 길이 3 미만 alias를 사전 뷰에서 제외한다. 영문은 BRANDS, alias==drug, `invega ` prefix만 허용한다.
5. 길이 차이가 allowed를 넘으면 거리 계산 전 제외한다. allowed는 query 길이 <6:1, <12:2, 그 외:3. OSA(삽입·삭제·교체·인접 전치 각 비용 1), score=`round(100*(1-distance/max(lengths)),1)` 사용. 거리 >allowed 또는 score <한글60/영문70이면 제외한다. Levenshtein/NFD 자모/2·3gram/prefix/suffix는 기존 rank feature에서만 사용한다.
6. score 내림차순, distance 오름차순, alias 사전순으로 정렬한 raw alias 최대20개. 앱 기본 표시는3개. target 중복 제거 전에 K를 자른다.
7. alias_map → drug. PRODUCTS의 alias 완전 일치 또는 `invega `+product 일치로 profile을 얻는다. target=`drug|profile` 또는 `drug|non_product_specific`. 같은 성분의 다른 LAI profile은 별도 target이다. 경로는 profile이면 injection, BRANDS이면 oral, 나머지는 unknown이다.
8. 길이 gate, 문자 체계 불일치, 사전 alias 필터, 길이 차이 gate, OSA 거리/score gate가 후보를 없앤다. target이 K 뒤로 밀릴 수도 있다. baseline에는 숫자 없음 gate도 있다.
9. 고정 test 247개 중 known227개. raw alias recall@1=223/227(98.24%), @3/5/10/20=224/227(98.68%). `phase1_audit.json`으로 실행 결과와 원본 해시를 저장한다.
10. 검색 실패 전부: `로핀`(origin 로도핀/zotepine), `조핀`(origin 조테핀/zotepine), `지돈`(origin 지오돈/ziprasidone). 모두 query 길이2라 위 첫 gate에서 반환한다. 정답 alias와 비교했다면 OSA=1, score66.7로 기존 한글 distance≤1/score≥60을 충족한다. 따라서 직접 원인은 거리 threshold가 아니라 query 길이 gate다. `로나핀`은 검색에 성공했으나 1위 target이 달라 ranking 오류다.

개선 전 평가 artifact, 관련 서비스/학습/평가/생성 코드와 기존 테스트를 읽었다. Phase 2는 기존 함수와 학습 artifact를 유지한 별도 실험용 generator로 진행한다. 개선 정책은 test 재평가 전에 동결하고 필요한 선택은 validation에서만 수행한다.
