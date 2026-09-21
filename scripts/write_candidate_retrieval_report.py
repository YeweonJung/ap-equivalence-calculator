"""Render the Korean report from saved measurements; does not rerun/tune retrieval."""
import json
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'data/candidate_retrieval'


def read(name):
    return json.loads((OUT / name).read_text(encoding='utf-8'))


def pct(value):
    return 'N/A' if value is None else f'{100 * value:.2f}%'


def table(headers, rows):
    def line(row):
        return '| ' + ' | '.join(str(v).replace('|', '\\|') for v in row) + ' |'
    return '\n'.join([line(headers), line(['---'] * len(headers))] + [line(r) for r in rows])


def main():
    e = read('evaluation.json')
    ablation = read('stress_channels.json')['results']
    val = read('validation.json')
    sm = read('stress_metadata.json')
    audit = read('phase1_audit.json')
    names = {'A_existing': 'A 기존 retrieval + 거리순위', 'A_existing_LR': '기존 retrieval + LR',
             'B_improved': 'B 개선 retrieval + 거리순위', 'C_improved_LR': 'C 개선 retrieval + LR'}
    def accuracy(dataset):
        return table(['System', 'Retrieval Recall@5', 'Top-1', 'Top-3', 'Top-5',
                      'Unknown rejection(빈 pool)', 'Unknown rejection(정책)', '연구 보류율', '실제 보류율'],
                     [[names[s], pct(r['metrics']['recall']['5']),
                       *[pct(r['metrics']['top'][str(k)]) for k in (1, 3, 5)],
                       pct(r['metrics']['unknown_empty_rejection']), pct(r['metrics']['unknown_policy_rejection']),
                       pct(r['metrics']['simulated_abstention']), '100%'] for s, r in e[dataset].items()])
    recall_table = table(['데이터', '시스템', 'known N', '@1', '@3', '@5', '@10', '@20'],
        [[d, names[s], r['metrics']['known'], *[pct(r['metrics']['recall'][str(k)]) for k in (1, 3, 5, 10, 20)]]
         for d in ('fixed', 'stress') for s, r in e[d].items()])
    errors_table = table(['데이터', '시스템', 'Retrieval error', 'Ranking error', '검색 성공 시 Top-1', '정답 검색 평균 rank', '정답 순위 평균 rank'],
        [[d, names[s], r['metrics']['retrieval_errors'], r['metrics']['ranking_errors'],
          pct(r['metrics']['conditional_top1']), f"{r['metrics']['mean_correct_retrieval_rank']:.4f}",
          f"{r['metrics']['mean_correct_ranking_rank']:.4f}"] for d in ('fixed', 'stress') for s, r in e[d].items()])
    explosion_table = table(['데이터', '시스템', '평균 target 수', 'median', '최대', '평균 오답 target 수', 'unknown 후보 생성', '2–3글자 후보 생성'],
        [[d, names[s], f"{r['metrics']['candidate_mean']:.4f}", r['metrics']['candidate_median'],
          r['metrics']['candidate_max'], f"{r['metrics']['false_target_mean']:.4f}",
          pct(r['metrics']['unknown_candidate_rate']), pct(r['metrics']['short_candidate_rate'])]
         for d in ('fixed', 'stress') for s, r in e[d].items() if s in ('A_existing', 'B_improved')])
    strata = table(['Stress 유형', 'known N', '기존 검색 성공', '선택 개선 검색 성공', '+자모 검색 성공'],
        [[kind, m['known'], m['recall_hits']['20'],
          e['stress']['B_improved']['by_error_type'][kind]['recall_hits']['20'],
          ablation['osa_short_jamo']['by_error_type'][kind]['recall_hits']['20']]
         for kind, m in e['stress']['A_existing']['by_error_type'].items() if m['known']])
    va = table(['Validation 구성', 'Recall@20', '평균 target 수', '평균 오답 target 수', 'unknown 후보 생성'],
        [[s, pct(r['metrics']['recall']['20']), f"{r['metrics']['candidate_mean']:.4f}",
          f"{r['metrics']['false_target_mean']:.4f}", pct(r['metrics']['unknown_candidate_rate'])] for s, r in val.items()])
    ab = table(['Stress 채널 구성', 'Recall@20', '검색 성공/1362', '평균 target 수', '평균 오답 target 수', 'unknown 후보 생성'],
        [[s, pct(r['metrics']['recall']['20']), r['metrics']['recall_hits']['20'],
          f"{r['metrics']['candidate_mean']:.4f}", f"{r['metrics']['false_target_mean']:.4f}",
          pct(r['metrics']['unknown_candidate_rate'])] for s, r in ablation.items()])
    unsafe = [c for c in e['stress']['C_improved_LR']['cases'] if c['unsafe_eligible']]
    unsafe_table = table(['합성 unknown 입력', 'LR 1위 target'], [[c['original'], c['top_target']] for c in unsafe])
    fixed_inputs = {c['original'] for c in e['fixed']['A_existing']['cases']}
    overlap = sum(c['original'] in fixed_inputs for c in e['stress']['A_existing']['cases'])
    text = f'''# Candidate Retrieval 개선 및 재평가 보고서

작성일: 2026-09-21. 프로젝트: `work/ranker_update`. 외부 AI API, 실제 환자정보, 모델 재학습, Git push, Render 배포를 사용하지 않았다.

**고정 test에서 recall은 개선됐지만, stress에서 약물 유사 unknown의 후보 생성이 늘었다. LR은 개선 pool에서도 Top-1 이득이 없고, 기존 연구용 통과 정책은 unknown 5건을 잘못 통과시킨다. 앱 기본 추천과 자동확정 비활성을 유지한다.**

## A. 기존 candidate retrieval 구조

Phase 2 구현 전에 [Phase 1 감사](CANDIDATE_RETRIEVAL_PHASE1_KO.md)와 [실행 결과·원본 해시](../data/candidate_retrieval/phase1_audit.json)를 기록했다. 기존 198개 테스트의 변경 전 실행도 통과했다.

- 앱: `app.py`/`services/frames.py` → `suggest_drugs` → `baseline_suggestions`. 숫자/용량 경계가 없으면 legacy baseline은 빈 목록이다. 앱 기본 표시는 K=3이다.
- 실험: `generate_candidates` → `name_and_suffix` → `normalize_name` → `records` 순회 → 문자 체계/길이 차이 gate → OSA → 정렬 → raw alias K=20. 이름만 입력할 수 있다.
- 정규화: NFKC, casefold, `[a-z가-힣]` 외 제거. 띄어쓰기·문장부호가 제거되며 단독 자모도 제거된다. 한글 음절이 하나라도 있으면 Korean bucket. 한/영 키보드 전환은 없다.
- Query 길이 3–40. 사전 뷰도 normalized alias 길이≥3. 영문은 BRANDS·성분 완전 일치·`invega ` prefix만 허용한다.
- 허용 OSA 거리: query 길이 <6 →1, <12 →2, 그 외 →3. 길이 차이도 같은 한도. score=`round(100*(1-distance/max(lengths)),1)`가 한글60/영문70 이상이어야 한다. Levenshtein은 기존 검색 gate가 아니라 rank feature다.
- 정렬: score 내림차순 → distance → alias. **기존 K는 alias 수이며 동일 target 중복을 먼저 제거하지 않는다.**
- alias_map의 성분 + PRODUCTS의 LAI profile을 target으로 사용한다. `drug|profile` / `drug|non_product_specific`. 같은 paliperidone이라도 PP1M/PP3M/PP6M은 구별한다. 사전 필터·문자 체계·길이 gate·거리·score·K 절단에서 target이 소실될 수 있다.

## B. 기존 실패 원인

고정 test 247개 = known227 + unknown20. 검색 실패는 다음 **3건이 전부**다.

| 입력 | 정답 alias / target 성분 | 실제 제거 위치 | 비교를 했다면 |
| --- | --- | --- | --- |
| 로핀 | 로도핀 / zotepine | `generate_candidates`: `if not 3 <= len(query) <= 40: return []` | OSA1, score66.7 |
| 조핀 | 조테핀 / zotepine | 같은 query 길이 gate | OSA1, score66.7 |
| 지돈 | 지오돈 / ziprasidone | 같은 query 길이 gate | OSA1, score66.7 |

거리/score 기준은 충족하므로 직접 원인은 **거리 계산 전 query 길이 gate**다. `로나핀`은 zotepine이 pool 안에 있으나 blonanserin이 1위인 ranking 오류다. 원본 고정 데이터와 기존 `data/name_ranker/evaluation.json`은 수정하지 않았다.

## C. 개선한 retrieval 방법

새 `services/candidate_retrieval.py`를 별도 오프라인 경로로 추가했다. 기존 generator·parser·환산·모델·UI 코드는 전혀 수정하지 않았다.

| 길이/문자 | 정책 |
| --- | --- |
| 한글 완성형 2글자 | 등록 3글자 alias의 첫·끝 음절과 정확히 같고 가운데 한 음절만 빠진 경우. `short_hangul` 채널, 최대3 target |
| 한글 3글자 | 기존 OSA gate 유지. 실험 자모 채널은 NFD 편집≤1, 유사도≥0.80, 음절 OSA≤1, 길이 차이≤1 |
| 한글 4글자 이상 | 기존 OSA gate 유지. 실험 자모 채널은 NFD 편집≤2, 유사도≥0.82, 음절 OSA≤2, 길이 차이≤1 |
| 영문 | 기존 OSA gate 유지. 2글자 허용하지 않음 |
| 전체 | 최대 이름길이40, 출력 최대20 target. 비정상 limit 거부, limit0은 빈 목록 |

2글자 일반 교체·임의 접두/접미 일치는 허용하지 않는다. 따라서 모든 짧은 이름을 복구하는 정책이 아니다. 성분·제품 정답을 입력받아 후보에 주입하지 않는다.

정책 상수는 final test 평가 전에 선언했다. Validation370개(known350/unknown20)에서 세 구성을 비교했다. 선택 기준은 recall@20 최대 → unknown 후보 생성 최소 → 오답 target 평균 최소 → 채널 수 최소다. threshold 수치 탐색·모델 재학습은 하지 않았다.

{va}

선택: **`osa_short` = OSA + 제한적 짧은 한글 + 정규화 exact alias**. `policy_lock.json`에 구현·평가기·원본 데이터·validation 결과 해시를 동결했다. 자모/ngram이 validation에서 이득을 보이지 않아 선택 구성에는 넣지 않았다. Stress에서 자모 이득을 발견했어도 선택을 바꾸지 않았다.

## D. 한글 자모 처리

추가 채널은 Unicode NFD 초성·중성·종성 단위 Levenshtein 거리와 `1-distance/max(NFD lengths)` 유사도를 사용한다. 기존 ranker의 NFD SequenceMatcher feature와는 다른 검색용 거리다. 모델 feature·계수는 그대로다.

새 retrieval 정규화는 NFKC 후 완성형과 `U+1100–U+11FF` 불완전 자모를 보존한다. 기존 정규화가 누락 자모를 버리는 것과 차이가 있다. 이것은 손실을 숨기지 않지만 어떤 입력에서는 기존 검색보다 불리하다. Stress에서 `ᄋᆯ란자핀`, `ᄏᆯ로자린` 2건이 선택 구성에서는 새 검색 실패가 됐다. 총18건 복구·2건 소실로 순16건 증가다.

자모 누락의 모든 경우를 해결하지 않는다. 기존 rank feature 정규화는 여전히 단독 자모를 제거하므로 retrieval/ranking 표현이 완전히 같지 않다. `레스패리돈`의 NFD 2/11 편집은 유사도0.81818로 동결된0.82보다 낮아 자모 채널에서도 제외된다. `헬로패리돌`은 2/12 편집으로 자모 채널에서 haloperidol을 복구한다. 이 경계를 단위 테스트로 확인했으며 평가 결과에 맞춰 threshold를 낮추지 않았다.

## E. Multi-channel retrieval 구조

| 채널 | 구현/채택 | raw score·gate |
| --- | --- | --- |
| A `osa` | 구현, 선택 | 기존 OSA similarity/100, 기존 거리·score gate |
| 짧은 한글 `short_hangul` | 구현, 선택 | 가운데 음절 삭제 조건 + OSA similarity/100 |
| B `hangul_jamo` | 구현, 별도 ablation | NFD Levenshtein normalized similarity + D절 gate |
| C `ngram` | 구현, 별도 ablation | 양쪽 길이≥6, bigram Jaccard≥0.65, OSA≤min(기존허용+1,3) |
| D prefix/suffix | 독립 채널 미구현 | 짧은 공통 어미만으로 무관 성분을 늘릴 근거가 부족함. 짧은 한글의 양끝 일치는 별도 제한 정책에 사용 |
| E `normalized_alias` | 구현, 선택 | ingredient/brand/alias 사전의 정규화 완전일치. 새 동의어·약칭 추론 없음 |

alias별 통과 채널을 union한 다음 동일 target을 합친다. 기존 OSA/exact 후보를 먼저 놓고, 그 안은 기존 score/distance/alias 순서다. 추가 후보는 채널 score → OSA score → distance → alias 순서다. target 대표 alias는 이 순서의 첫 alias이고, LR은 대표 alias를 평가한다. 다른 alias의 LR 최대값을 뒤늦게 선택하지 않는다.

각 후보에 `retrieved_by`, 채널별 `retrieval_scores`, alias/거리/gate/이유를 포함한 `retrieval_evidence`, `matched_aliases`, `pool_inclusion_reason`, `pre_cap_target_count`, `retrieval_rank`, 정책 버전을 남긴다. 각 채널 점수의 최댓값을 기록하되 어느 alias에서 나왔는지도 evidence에 보존한다. raw score는 확률이 아니다. profile이 다른 LAI는 합치지 않는다.

저수준 `retrieve()`의 기본 채널은 자모를 포함한 실험 구성이다. **선택 시스템을 재현하는 평가기와 `review_candidate_retrieval.py`는 반드시 lock의 채널을 명시한다.** 앱은 이 새 모듈을 호출하지 않는다.

## F. 기존 고정 test set 결과

{accuracy('fixed')}

정답 검색 224→227/227, Top-1 223→226/227. 추가된 정답3건은 모두 수동 검토 대상으로 남는다. LR 적용 전후 Top-1/3/5가 같다. 이름 식별 지표이며 처방 환산 정확도나 임상 정확도가 아니다.

## G. Stress test 설계

별도 `stress.jsonl`: **{sm['count']}개(known{sm['known']} + unknown26)**. target·문자 체계마다 가장 짧은 등록 alias를 결정적으로 선택한80개 원형에 고정 위치 변형을 가했다. 무작위 seed가 필요 없는 생성이며 `make_retrieval_stress.py`로 재현한다. 이미 생성된 파일을 실수로 덮어쓰지 않도록 보호했다.

짧은 한글2/3/4글자, 삭제+교체, 삽입+전치, 공백+오타, 제품명+`injeciton` 제형 오타, 초성/모음/받침/자모누락/두 모음 오류, 영문 인접키/전치/삭제/삽입/중복/복수오타, XR/ER/LAI/depot/oral/injection, 유사 등록 성분명을 포함한다. 용량 문자열은 parser 경계 시험용 합성 suffix다.

Unknown26개 중23개는 `neurozapine`, `risperidonex`, `뉴로자핀`, `로가핀` 같은 약물 유사 문자열,3개는 무관 문자열이다. 여기서 unknown은 **의도적으로 미등록으로 라벨한 합성 입력**이며 세계 전체에 그런 약물이 없다는 뜻이 아니다. 오타와 미등록명은 문자열만으로 구별할 수 없는 경우가 있다. 같은 입력의 다른 원형·unknown 의도가 겹치는 **{sm['ambiguous']}개 행을 삭제하지 않고 `ambiguous`로 표시**했다.

Stress는 추가 난도 시험이며 독립 holdout이 아니다. 사전과 기존 데이터의 성분을 공유하고, fixed test와 완전 동일 original인 stress 행도 {overlap}개 있다. 일부 short3/4는 정상 원형 그대로다. 분모는 사례 행이며 동일 이름이 여러 제형/오류 유형에 반복된다. 따라서 전체 평균을 실사용 유병률 가중 성능으로 해석하지 않는다.

## H. Stress test 결과

{accuracy('stress')}

선택 개선의 검색 성공은1183→1199/1362, Top-1은1182→1198/1362. 자모를 추가한 별도 진단은 다음과 같다. 이 결과는 선택 정책을 바꾸는 데 사용하지 않았다.

{ab}

자모는 선택 구성 대비 정답9건을 추가 검색하지만 오답 target 총수도75→77로2개 늘었다. ngram은 이번 stress에서도 추가 이득이 없었다.

{strata}

단일 자음·모음·받침 오류는 기존 OSA도 이미 모두 복구한다. 두 모음 오류 등은 자모의 추가 이득을 볼 수 있지만, 접두2글자27개와 제품+제형 오타32개는 선택 구성에서 전부 실패한다. 후자는 `injeciton`을 제형 경계로 인식하지 않아 이름에 포함되는 경우다. 기존 parser 변경 금지에 따라 이번에 고치지 않았다.

## I. Retrieval recall

{recall_table}

분모는 **known 입력**이고, ranking을 적용하기 전 generator 순서에서 측정했다. 개선 K는 distinct target 수. 기존은 native raw alias20을 받은 뒤 target을 중복 제거한 순서이며, 비교 검증용 `raw_alias_recall`도 별도 저장했다. 이번 세트에서 두 정의의 @1/3/5/10/20 값은 같았다. LR 시스템의 retrieval recall이 대응 비LR 시스템과 같은 것은 동일 pool을 쓰기 때문이다.

## J. Ranking accuracy

F/H 표의 Top-k는 거리 또는 기존 LR 순위에서 동일 target alias를 중복 제거한 결과다. 검색 실패도 known 분모에 포함한다. 검색 성공 사례만 분모로 쓰는 수치는 K절에 별도로 표시한다.

LR의 가중치·표준화·feature26개·정책 threshold0.95/margin0.25/min length4는 유지했다. Baseline 연구 정책은 threshold0.95/margin0.15다. 점수 척도가 다르고 이번 실험에서 두 정책을 재최적화하지 않았으므로 보류율 차이를 모델 우월성으로 해석하지 않는다. 새 pool에 대한 점수 보정도 하지 않았다.

## K. Retrieval error vs Ranking error

{errors_table}

고정 test의 남은 ranking 오류: `로나핀` → 1위 blonanserin, 정답 zotepine은2위. Stress의 ranking 오류도 공백 변형 `로 나핀`이다. 선택 개선 stress의163개 retrieval failure는 [전체 오류 목록](CANDIDATE_RETRIEVAL_FAILURES_KO.md)에 모두 기록했다. 모든 시스템의 전체 사례·후보·판정은 [evaluation.json](../data/candidate_retrieval/evaluation.json)에 있다.

대표 검색 실패: `라가`→라가틸(접두만으로는2글자 정책 불충족), `나틸`→라가틸(삭제+교체), `래개틸`→라가틸(3글자 NFD budget1 초과), 제품명+`injeciton`(이름 경계 미분리). 짧은 입력 전체를 해결했다고 주장하지 않는다.

## L. Candidate explosion 분석

{explosion_table}

고정 세트의 전체 오답 target 수는17→17로 같고, 추가3개는 정답이었다. Stress는73→75로 증가한다. 평균·최대 기준의 대규모 후보 폭증은 없지만, unknown 생성 증가가 있으므로 **false candidate 증가 없이 개선됐다는 결론은 틀리다.**

전체 입력(빈 pool 포함)의 distinct target 통계다. 기존 stress raw alias 평균0.9798과 개선 target 평균0.9179를 직접 비교해 감소라고 주장하지 않는다. 같은 target 단위로 비교하면0.9049→0.9179다. short 생성률 분모는 길이2–3 전체 입력으로 fixed26개/stress247개이며 한글 전용 분모는 아니다. 길이별 한글 유형 결과는 H절에 있다.

개선 출력 한도는 일반20/2글자3이다. stress에서 실제 pre-cap 최대도3으로, 단순 cap 절단 때문에 작은 평균이 된 것은 아니다. 합성 고밀도 사전40 target을 주입한 단위 테스트에서 두 상한을 별도로 확인했다. 기존 pre-cap 필드는 legacy 반환 pool의 관측 크기이며 완전 무제한 alias 검색 수는 아니다.

## M. Unknown input 분석

기존 고정 unknown20개는 모두 무작위 형태라 두 시스템 모두 후보0개. 더 어려운 stress unknown26개에서는 후보 생성11→14개, 빈 pool 거절15→12개다. 증가3개는 `로핀`, `조핀`, `지돈`의 **unknown 의도** 사례다. 같은 문자열이 정답 삭제 오타일 수도 있어 문맥·사용자 확인 없이 해결할 수 없다.

Drug-like23개만 보면 기존11/23(47.83%) → 개선14/23(60.87%) 후보 생성. 무관3개는 둘 다0개다. 빈 pool 거절과 정책상 보류는 서로 다른 지표로 F/H에 표시했다.

기존 LR 정책은 기존/개선 pool 모두 다음 unknown5건을 통과시켰다. LR unknown 정책 거절률은21/26=80.77%, baseline 정책은26/26=100%. 이것은 오프라인 연구용 eligibility의 오류이고 실제 자동확정은 없다.

{unsafe_table}

## N. Safety / abstention

모든 새 review 결과는 `confirmed_drug=None`, `auto_accepted=False`, `needs_review=True`다. 실제 자동확정 보류100%, coverage0%. 후보에는 사용자가 확인하기 전 환산 권한이 없다. 새로운 앱 연결·자동 선택·외부 요청·처방 저장 기능을 추가하지 않았다.

짧은 이름, 낮은 score, 서로 다른 target 간 작은 margin, 명시적 formulation conflict는 기존 `decision` 사유로 보류한다. 제형 충돌 단위 테스트와 stress 제형 결과를 확인했다. 다만 XR/ER의 약별 적합성 DB가 없고 misspelled formulation을 전부 검출하지 못한다. Unknown 정책 통과5건이 보여주듯 연구용 `policy_eligible`은 실제 확인으로 사용할 수 없다. LR 점수는 `uncalibrated_ranking_score`다.

## O. Regression tests

- 변경 전 **198 passed**. 기존 테스트 파일은 수정하지 않았다.
- 새 **34개**: 짧은 입력의 제한/보류, 자모 채널 성공·경계거절·불완전 자모, 각 채널 단독 검색, target 중복제거와 provenance, unknown/drug-like unknown, 후보 상한, 제형 충돌·suffix 보존, LAI profile 분리, 결정성, 모델 없는 거리 fallback, 앱 baseline 유지, 원본 해시, stress 재현, limit 검증, 검색/순위 오류 분리.
- 최종 **232 passed**, skip 없음. 기존 환산/등가표/LAI/parser/UI/모델/고정 데이터와 기존 tests의 원본 해시 {len(audit['original_file_sha256'])}개가 유지된다.
- Node UI 검사: `UI request ordering, rounding, missing factors and escaping passed`. PATH의 오래된 Brackets Node는 실행 오류가 있어, 설치된 Codex Node의 절대경로로 실행했다.
- 단위 테스트 초안에서2개 자모 성공 예시가0.82 경계를 충족하지 않아 실패했다. 성공 조건을 만족하는 `헬로패리돌` 예시와 경계 미충족 `레스패리돈` 거절 검사를 분리했다. **검색 코드·정책·평가 데이터는 이를 위해 변경하지 않았다.**

## P. 한계점

1. 합성 데이터, 작은 사전, 독립 임상 검증 없음. Test의 원래 실패3건은 과제 시작 때 이미 알려져 있었으므로 완전히 눈가림된 새 holdout이라고 할 수 없다. 수치 선택은 validation만 사용했고 final 결과 기반 반복 조정은 하지 않았다.
2. Validation의 unknown20개는 너무 쉬워 자모의 이득·drug-like unknown 위험을 선택 단계에서 충분히 반영하지 못한다. 이미 본 stress로 threshold를 조정해서 다시 test라고 보고해서는 안 된다.
3. 2글자 가운데 삭제만 복구한다. 임의 약칭·앞/뒤 삭제·복합오류에는 제한적이다. 불완전 자모 보존으로 생긴 회귀2건을 그대로 보고했다.
4. 사전 route/profile은 기존 heuristic이다. 모든 제형·약품코드·지역 브랜드를 검증한 데이터베이스가 아니다. 등록명 자체의 오류 가능성도 남는다.
5. Target별 대표 alias 한 개를 LR에 넣어 다른 alias의 순위 feature 차이를 놓칠 수 있다. 이번 결과에서 LR 정확도 이득은 없으며 재학습하지 않았다.
6. Stress의 의도상 unknown과 typo label은 겹칠 수 있다. candidate 발생은 추천 노출 위험이지 자동 오투약률이 아니다. 수동 선택 정확도·검토 부담·지연시간·실사용 비용은 측정하지 않았다.
7. 사전 전체 순회 방식이다. 현재 사전 규모의 기능 검증이며 대규모 EDI/KD 사전의 처리량/latency benchmark는 아니다.

## Q. 실제 처방 데이터 확보 후 검증 계획

기관 승인 아래 약물명 토큰만 비식별 수집하고 실제 환자정보/처방 원문은 저장하지 않는다. 기관·시점·성분별 분할과 별도 calibration/validation/잠금 test를 정한다. 두 검토자가 성분·제품·제형·진짜 unknown·맥락 없이는 불명확한 입력을 독립 주석화한다. 클릭을 정답으로 간주하지 않는다.

2–3글자 약칭, 자모/OCR/키보드 모드 오류, compound typo, drug-like unknown, formulation typo, LAI profile 혼동을 충분히 포함한다. 새 validation에서만 정책을 선택하고, 한 번 잠근 새로운 외부 test에서 target recall·오답 후보·검토시간·사용자 정답 선택률을 비교한다. 먼저 shadow mode로 기록하며 자동확정은 계속 비활성으로 둔다.

## R. 다음 개발 단계 추천

우선순위는 **실제 데이터 검증 → 새로운 validation에서 제한적 자모/제형 경계 retrieval 실험 → 필요성이 확인된 경우 ranking 연구**다. 복잡한 모델부터 추가할 근거가 없다. 자모 채널의 stress 추가9건은 다음 독립 검증의 가설이며 production 승격 근거가 아니다.

마지막 질문에 대한 답:

1. **병목은 retrieval인가 ranking인가?** 기존 fixed는 검색3건/순위1건, stress는179건/1건으로 retrieval이 더 크다. 선택 개선 후 fixed는0/1이지만 stress는163/1로 retrieval 병목이 남는다.
2. **실제로 recall을 높였는가?** Fixed Recall@5 224/227→227/227(+1.32%p), stress1183/1362→1199/1362(+1.17%p). 개선은 관측됐지만 실사용 일반화는 미검증이다.
3. **False candidate 증가 없이 달성됐는가?** Fixed에서는 오답 target17개로 동일. Stress에서는73→75, unknown 후보 생성11/26→14/26으로 증가했다. 따라서 전체적으로는 아니다.
4. **개선 pool에서 LR이 baseline보다 도움이 되는가?** Top-1 fixed226/227, stress1198/1362로 거리순위와 동일하다. 연구 보류율은 낮지만 unknown5개를 잘못 통과시키므로 정확도·안전 이득의 근거가 아니다.
5. **ML production 활성화 근거가 있는가?** 없다. 합성만 평가했고 Top-1 이득이 없으며 어려운 unknown 정책 오류가 있다. 기존 production_enabled=false와 사용자 확인 요구를 유지한다.
6. **다음 단계는 무엇인가?** 실제 이름 데이터와 새 독립 validation/test 확보를 먼저 권고한다. 이후 제한적 자모와 제형 경계 개선을 평가하고, 다른 모델 실험은 뒤로 둔다.

## 변경 파일 및 재현

기존 파일 수정0개. 추가 코드는 `services/candidate_retrieval.py`, `scripts/audit_candidate_retrieval.py`, `scripts/evaluate_candidate_retrieval.py`, `scripts/make_retrieval_stress.py`, `scripts/evaluate_retrieval_channels.py`, `scripts/review_candidate_retrieval.py`, `scripts/write_candidate_retrieval_report.py`, `tests/test_candidate_retrieval.py`다. 문서3개와 `data/candidate_retrieval/` 감사·정책lock·validation·stress·평가 산출물을 추가했다.

최초 실행 순서는 audit → select → make stress → evaluate → channel diagnostic → tests → report다. audit/select/stress 생성은 보존된 파일을 덮어쓰지 않으므로 현재 산출물에서 다시 실행하지 않는다. 기존 synthetic 생성·train/evaluate_name_ranker 스크립트는 재실행하지 않았다.

```powershell
# work/ranker_update 에서. 저장된 lock과 고정 데이터를 읽기만 한다.
python scripts/evaluate_candidate_retrieval.py --evaluate
python scripts/evaluate_retrieval_channels.py
python scripts/review_candidate_retrieval.py 로핀 --lr
python -m pytest -q
& 'C:\\Users\\jyo52\\.cache\\codex-runtimes\\codex-primary-runtime\\dependencies\\node\\bin\\node.exe' tests/quick_check_ui.cjs
python scripts/write_candidate_retrieval_report.py
```

원본 dataset SHA256: `{e['policy']['dataset_sha256']}`. Stress SHA256: `{e['stress_sha256']}`. 구현/평가기/validation 해시는 `policy_lock.json`에 있다. Git push와 Render 배포는 수행하지 않았다.
'''
    (ROOT / 'docs/CANDIDATE_RETRIEVAL_REPORT_KO.md').write_text(text, encoding='utf-8')
    sections = ['# Candidate Retrieval 전체 오류 목록\n\n고정 정책의 저장된 평가 결과에서 추출. 평가 입력을 수정하거나 삭제하지 않았다.\n']
    for dataset in ('fixed', 'stress'):
        for system in ('A_existing', 'B_improved', 'C_improved_LR'):
            cases = [c for c in e[dataset][system]['cases'] if c['target_key'] is not None and c['ranking_rank'] != 1]
            sections.append(f'\n## {dataset} — {names[system]} ({len(cases)}건)\n\n')
            sections.append(table(['ID', '입력', '원형', '정답 target', '오류', '1위 target'],
                [[c['id'], c['original'], c['origin_alias'], c['target_key'],
                  'ranking' if c['retrieved'] else 'retrieval', c['top_target'] or '없음'] for c in cases]) + '\n')
    (ROOT / 'docs/CANDIDATE_RETRIEVAL_FAILURES_KO.md').write_text(''.join(sections), encoding='utf-8')
    print('Report and complete failure appendix written')


if __name__ == '__main__':
    main()
