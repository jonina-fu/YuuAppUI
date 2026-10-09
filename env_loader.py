"""加载同目录 .env 中的环境变量（已存在的不覆盖）。

敏感凭证（Twilio / LoginRadius / HASE 等）存放在 .env（已 gitignore），
代码统一通过 os.getenv 读取，避免硬编码入库。
"""
import os
from pathlib import Path

_env_file = Path(__file__).with_name(".env")
if _env_file.exists():
    for _line in _env_file.read_text(encoding="utf-8").splitlines():
        _line = _line.strip()
        if _line and not _line.startswith("#") and "=" in _line:
            _k, _, _v = _line.partition("=")
            os.environ.setdefault(_k.strip(), _v.strip())
