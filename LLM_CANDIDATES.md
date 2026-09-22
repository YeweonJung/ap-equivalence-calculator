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
모델 시작이 느리면 Ollama에서 모델을 먼저 실행하거나 NAME_LLM_TIMEOUT_SECONDS를 조정합니다.
기본 HTTP 소켓 제한시간은 8초, 설정 범위는 1~30초입니다. 전체 작업의 절대 시간 제한은 아닙니다.
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

공식 문서: [Windows](https://docs.ollama.com/windows),
[Mac](https://docs.ollama.com/macos), [API](https://github.com/ollama/ollama/blob/main/docs/api.md),
[MLX LM](https://github.com/ml-explore/mlx-lm).
