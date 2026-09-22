"""Start the local calculator with an installed Ollama model (Windows/macOS)."""
import json
import os
from pathlib import Path
import subprocess
import sys
from urllib.request import urlopen


def main():
    os.chdir(Path(__file__).resolve().parent)
    model = os.environ.get('NAME_LLM_MODEL', 'qwen2.5:7b')
    try:
        with urlopen('http://127.0.0.1:11434/api/tags', timeout=5) as response:
            installed = json.load(response)
        if model not in {entry['name'] for entry in installed.get('models', [])}:
            print(f'Model missing. Run: ollama pull {model}', flush=True)
            return 1
    except Exception:
        print('Start Ollama first, then run this launcher again.', flush=True)
        return 1
    os.environ.update(NAME_LLM_ENABLED='1', NAME_LLM_BACKEND='ollama',
                      NAME_LLM_URL='http://127.0.0.1:11434')
    os.environ.setdefault('NAME_LLM_TIMEOUT_SECONDS', '120')
    port = os.environ.get('LOCAL_APP_PORT', '5055')
    print(f'Local calculator: http://127.0.0.1:{port} | model: {model}', flush=True)
    return subprocess.call([sys.executable, '-m', 'flask', '--app', 'app', 'run',
                            '--host', '127.0.0.1', '--port', port, '--no-reload'])


if __name__ == '__main__':
    raise SystemExit(main())
