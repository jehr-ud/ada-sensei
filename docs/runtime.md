# Runtime Requirements

| Concern          | Requirement                                                        |
| ---------------- | ------------------------------------------------------------------ |
| Language         | Python >= 3.11, `< 4.0`, declared in `pyproject.toml`              |
| OS               | macOS and Linux for the MVP (POSIX); Windows not required          |
| JDK              | JDK 17+ required to execute Gradle builds (AGP 8.x baseline)       |
| Android SDK      | Discovered via `ANDROID_HOME` / `ANDROID_SDK_ROOT` or `local.properties`; used only by Gradle |
| Gradle           | Prefer the repository wrapper (`./gradlew`); fall back to `gradle` on `PATH` |
| Subprocess timeout | Default 600 s per tool invocation, configurable (RQ-FND-017, RQ-FND-021) |
| Default LLM      | Ollama provider, model `qwen2.5-coder:7b` (RQ-FND-029)             |

Installation is available directly from GitHub:

```bash
pip install git+https://github.com/jehr-ud/ada-sensei.git
```

The default LLM (Ollama server + model) is provisioned automatically on first
use (RQ-FND-030), or via `install.sh` for a one-command setup.