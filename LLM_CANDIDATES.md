# 선택형 LLM 약물명 후보 보충

기존 사전/철자/짧은 한글 검색에서 후보가 없을 때만 LLM을 호출합니다.
기본값은 꺼짐이며, 활성화해도 후보 선택 전에는 약물이나 용량을 확정하지 않습니다.
LLM의 high/low는 검증된 확률이 아닙니다. 성능 개선 여부는 별도 평가가 필요합니다.

## Windows와 Mac: Ollama 공통 실행

공식 Ollama를 설치하고 앱을 실행한 뒤 모델을 준비합니다.

```sh
ollama pull qwen2.5:7b
```

Python 의존성은 기존 requirements.txt를 사용합니다. Ollama용 Python 패키지는 필요 없습니다.
아래 명령은 프로젝트 루트에서 실행합니다. Ollama 서버와 Flask 앱이 같은 컴퓨터에서 동작하는 예입니다.

Windows PowerShell:

```powershell
$env:NAME_LLM_ENABLED = "1"
$env:NAME_LLM_BACKEND = "ollama"
$env:NAME_LLM_MODEL = "qwen2.5:7b"
$env:NAME_LLM_URL = "http://127.0.0.1:11434"
python -m flask --app app run --host 127.0.0.1 --port 5000
```

Mac 터미널:

```sh
export NAME_LLM_ENABLED=1
export NAME_LLM_BACKEND=ollama
export NAME_LLM_MODEL=qwen2.5:7b
export NAME_LLM_URL=http://127.0.0.1:11434
python3 -m flask --app app run --host 127.0.0.1 --port 5000
```

브라우저에서 http://127.0.0.1:5000 을 엽니다.
설치 후에는 `python start_local_llm.py`로도 시작할 수 있습니다(Mac: `python3`).
이 실행기는 설치된 모델을 확인하고 Ollama 연결을 활성화한 로컬 계산기를
http://127.0.0.1:5055 에 실행합니다. 공개 Render 사이트의 설정은 변경하지 않습니다.
모델 시작이 느리면 Ollama에서 모델을 먼저 실행하거나 NAME_LLM_TIMEOUT_SECONDS를 조정합니다.
기본 HTTP 소켓 제한시간은 8초, 설정 범위는 로컬 1~120초/원격 1~30초입니다.
로컬 실행기는 첫 모델 로딩과 CPU 실행을 위해 120초를 사용합니다. 전체 작업의 절대 시간 제한은 아닙니다.
동시 추론은 프로세스당 1개이며 바쁜 동안 추가 LLM 요청은 후보 없이 반환합니다.
파일 입력은 미확인 약물마다 순차 호출할 수 있으므로 대량 처리에서는 LLM을 끄는 편이 적합합니다.

## Apple Silicon Mac: 원래 MLX 코드 사용

선택적으로 `python3 -m pip install mlx-lm` 후:

```sh
export NAME_LLM_ENABLED=1
export NAME_LLM_BACKEND=mlx
export NAME_LLM_MODEL=mlx-community/Qwen2.5-7B-Instruct-4bit
python3 -m flask --app app run --host 127.0.0.1 --port 5000
```

MLX는 필요할 때만 import/load합니다. 모델 경로 변경 시 다시 로드하고 동시 접근을 잠급니다.
MLX 직접 실행에는 HTTP 제한시간이 적용되지 않으므로 로컬 개발용입니다.
Windows에서는 `ollama`를 선택하세요. Ollama 모델 태그와 MLX 모델 경로는 서로 다릅니다.

## Render 연결

### 이 컴퓨터의 모델을 연결하는 worker 방식

Render에서 NAME_LLM_ENABLED=1, NAME_LLM_BACKEND=worker와 32자 이상 전용
NAME_LLM_WORKER_KEY를 설정합니다. 이 컴퓨터에는 같은 키와 사이트 주소를
Git에서 제외한 `.env.llm-worker`에 저장합니다:

```dotenv
NAME_LLM_SITE_URL=https://ap-equivalence-calculator.onrender.com
NAME_LLM_WORKER_KEY=<dedicated-random-secret>
NAME_LLM_MODEL=qwen2.5:7b
```

Ollama 실행 후 `python run_render_worker.py` 또는 Windows의
`start_render_worker.cmd`를 실행합니다. worker는 사이트에 HTTPS로 접속해
작업을 가져오며, PC에 외부 접속 포트를 열지 않습니다. PC/인터넷/worker가
중지되면 AI 보충이 중지되고 기존 계산과 사전 검색은 계속 동작합니다.
worker가 다시 켜지면 같은 사이트 주소로 재연결합니다.

대기열은 Render 인스턴스의 임시 SQLite 파일을 이용하므로 동일 인스턴스의
Gunicorn 프로세스들이 공유합니다. 여러 인스턴스로 확장하는 구성에는 사용할 수 없습니다.
약물 이름/제형 힌트/사전 예시만 포함하며 용량과 처방 전체는 저장하지 않습니다.
최대 4건, 유효시간 90초, 요청 대기 최대 85초입니다. 완료 후 삭제하며
만료 작업은 다음 큐 접근 시 삭제합니다. 응답은 기존 허용목록 검증을 다시 거칩니다.
키 없는 작업 조회/완료 요청은 거부합니다. `/version`에서 연결 상태를 확인할 수 있습니다.
worker는 주기적으로 접속하므로 실행 중에는 Render 무료 인스턴스가 유휴 상태로
전환되지 않을 수 있습니다. 실행 시간은 기존 무료 사용량에 포함됩니다.

### 별도 추론 서버를 직접 호출하는 방식

Render의 localhost는 사용자 Mac/Windows가 아니라 Render 서버입니다.
공개 사이트에서 LLM을 쓰려면 Render에서 접근 가능한 Ollama 호환 서버가 별도로 필요합니다.
이 변경은 서버를 설치하거나 인터넷에 노출하거나 공개 배포를 자동으로 활성화하지 않습니다.
원격 서버를 준비한 다음 설정할 값:

| 변수 | 값 |
| --- | --- |
| NAME_LLM_ENABLED | 1 |
| NAME_LLM_BACKEND | ollama |
| NAME_LLM_URL | 인증 프록시의 HTTPS 기본 주소 (/api/chat 제외) |
| NAME_LLM_API_KEY | 프록시가 검증하는 Bearer 토큰 |
| NAME_LLM_MODEL | 서버에 설치된 모델 태그 |

원격 주소에는 HTTPS와 토큰을 요구하며 리다이렉트를 따라가지 않습니다.
Ollama 앞단 서버에서 실제 인증을 강제해야 합니다. 이 클라이언트는 토큰을 보내는 역할만 합니다.
NAME_LLM_ENABLED=0으로 즉시 비활성화할 수 있습니다.
NAME_RETRIEVAL_ENABLED=0은 기존 철자 추천으로 되돌아가며 LLM도 호출하지 않습니다.

## 입력과 결과 처리

- 이름 토큰(영문/한글 2~40자), 제형 힌트, 허용 성분명 목록만 모델에 전달합니다.
- 한국어 대응을 돕기 위해 앱 사전에서 글자 모양이 가까운 이름 예시 12개도 함께 전달합니다.
- 전체 처방, 용량, 빈도는 전송하지 않습니다. 단순 글자 검사는 개인정보 제거를 보장하지 않으므로 약물명만 입력해야 합니다.
- 주사제/LAI, 복수 단어/문장, 제조사만 적힌 일부 입력은 보충 대상에서 제외합니다.
- JSON 객체/후보 배열/필드 자료형/허용 목록을 검증하고 중복 제거 후 최대 2개만 표시합니다.
- 제품을 특정할 수 없는 주사제는 기존 직접 수정 절차를 이용합니다.
- 모델 실패/시간초과/잘못된 응답은 빈 후보로 처리합니다. 오류 로그에 입력과 응답을 남기지 않습니다.
- 후보는 AI 미확인 후보로 표시합니다. 확인 후 원래 용량/빈도/제형 접미사를 유지해 기존 파서로 다시 계산합니다.
- 기존 피드백은 계속 별도 동의가 필요하며 자동 학습하지 않습니다.

## 검증 범위

`python -m pytest tests/test_llm_candidates.py -q`는 모의 모델 응답으로
검증, 미확인 상태 유지, 요청 중복 방지, 파일 내보내기, 실패 복구를 확인합니다.
실제 모델의 정확도나 Mac 하드웨어 실행을 검증하는 테스트는 아닙니다.

2026-09-22 Windows 실제 모델 확인: Qwen2.5 7B 다운로드/추론 성공.
사전 예시 보강 후 로컬 앱 합성 사례에서 `리쓰페리도오온`은 risperidone,
`쿠에티아피이인`은 quetiapine 후보를 반환했습니다(각 8.53초/26.90초).
zzzzzz와 제조사만 적힌 주사제는 후보 없이 반환했습니다. 이는 소수 연결
시험이며 정확도 평가가 아닙니다. 앞선 원형 프롬프트에서 오추천이 관찰됐고,
사전 보강 후에도 오추천 가능성이 남으므로 수동 확인은 항상 필요합니다.

공식 문서: [Windows](https://docs.ollama.com/windows),
[Mac](https://docs.ollama.com/macos), [API](https://github.com/ollama/ollama/blob/main/docs/api.md),
[MLX LM](https://github.com/ml-explore/mlx-lm).
