# 개선 후보 검색 앱 연결

2026-09-21. 오프라인 평가 후 사용자의 별도 요청에 따라 Git/Render 앱 연결을 진행한 릴리스다. 이전 CANDIDATE_RETRIEVAL_REPORT_KO.md의 '배포하지 않음/기존 파일 수정 없음'은 오프라인 실험 당시 기록이다.

## 동작

- 한 줄 검사, CSV/Excel 업로드, 빠른 Excel 내보내기가 같은 `services/manual_suggestions.py`를 사용한다.
- 현재 `osa + short_hangul + hangul_jamo + normalized_alias`를 사용한다. 최초 validation 선택 구성에 사용자의 후속 활성화 요청으로 기존 자모 채널을 추가했다. ngram은 비활성이다.
- `로핀 / 조핀 / 지돈` 입력은 후보가 표시되며, 사용자가 후보 버튼을 선택해 수정 문자열을 제출하기 전에는 환산되지 않는다.
- LR 모델을 읽거나 활성화하지 않는다. NAME_RANKER_ENABLED 설정이 있어도 앱의 이 경로에는 영향을 주지 않는다.
- 후보는 confirmed_drug=None, auto_accepted=False, needs_review=True다. 근거는 API/Excel에 보존하고 UI에는 글자 차이와 짧은 이름 확인 안내를 표시한다.
- 용량·단위·빈도·제형 suffix와 환산 공식·등가표·LAI 로직은 유지한다.

## 장애 대응과 버전

`NAME_RETRIEVAL_ENABLED=0`을 설정하고 서비스를 재시작하면 기존 spelling baseline으로 돌아간다. 새 검색의 데이터/설정 오류에도 기존 baseline을 반환한다. 로그에 입력 처방 문자열이나 예외 메시지를 남기지 않는다.

`/version`은 `2026.09.21-candidate-retrieval-jamo-manual`, 실제 Render commit, name_retrieval, name_retrieval_channels, name_ranker_enabled=false, automatic_confirmation_enabled=false를 제공한다.

## 자모 채널 활성화

`헬로패리돌`처럼 두 모음이 바뀐 입력에서 `할로페리돌` 후보를 추가 검색한다. NFD 자모 거리·유사도 threshold는 기존 평가된 값 그대로이며 재학습하거나 test로 조정하지 않았다. 과거 validation 선택 기록과 평가 결과는 그대로 보존한다.

기존 stress 진단에서 자모 추가는 검색 성공1199→1208/1362, 오답 target75→77이었다. 사용자의 요청에 따라 수동 추천에만 활성화하며 LR 또는 자동확정을 활성화한 것이 아니다. 일반 후보20개/짧은 입력3개 상한, 화면 기본3개와 수동 선택 후 환산은 유지된다.

코드 공유 방법은 [코드 공유 안내](CODE_SHARING_KO.md)에 정리했다.

## 원격 충돌 복구

작업 도중 원격 main에 c236035(기존 ranker와 정리 작업), c837a5c(미해결 stash conflict)가 추가됐다. c837a5c의13개 파일에는 충돌 표시, 과거 파서 분기, 중복 helper가 들어가 있었다. 정상 동작하던 c236035의 구현을 기준으로 충돌 파일을 복구하고 이번 연결 변경을 적용한다. 원격 커밋 이력과 c236035의 정리는 보존하며 force push를 사용하지 않는다.

## 평가 보존

기존 test247개, 모델 가중치, 사전, 검색 구현, threshold는 수정하지 않았다. 원본 실험은 별도 `ranker_update` 폴더에 그대로 남는다. Git의 Windows/Linux 줄바꿈 차이 때문에 보호 소스 검사는 LF 정규화 해시로 이식했고, 앱/frames/version의 의도된 변경3개만 integration_manifest에 명시했다. 모델·데이터·검색 코드는 기존 byte hash를 유지하도록 .gitattributes로 고정했다. 평가기의 수식은 그대로이며 원본 감사 guard만 integration manifest를 이해하도록 바꿨다. 이전 평가기 hash도 policy lock에 보존한다.

검증 명령: `python -m pytest -q`, `node tests/quick_check_ui.cjs`, `node tests/manual_suggestions_ui.cjs`, `python scripts/build_equivalence_lookup.py` 후 lookup diff 확인. 합성 입력으로 운영 API와 실제 후보 선택 UI를 별도 확인한다.
