#!/usr/bin/env python3
"""generate_configs.py - Генерация конфигураций JupyterHub и nbgrader на основе CSV."""

import argparse
from pathlib import Path

from helpers import _parse_csv
from files_generators import (
    _gen_jupyterhub_config,
    _gen_nbgrader_configs,
    _gen_jupyter_server_config,
    _gen_global_nbgrader_config,
    _gen_setup_script,
    _gen_dockerfile,
)


# ---------------------------------------------------------------------------
# CLI – Основная точка входа в скрипт
# ---------------------------------------------------------------------------

def main():
    """Главная функция для парсинга аргументов и запуска генерации конфигураций."""

    p = argparse.ArgumentParser(description="Генерация конфигураций JupyterHub + nbgrader на основе CSV-файла")
    p.add_argument("csv", help="Путь к файлу users.csv")
    p.add_argument("--output-dir", default=".", help="Каталог для сохранения результатов")
    args = p.parse_args()

    csv_path = Path(args.csv).resolve()
    out_dir = Path(args.output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # Разбор CSV-файла
    users, courses = _parse_csv(csv_path)

    # Генерация всех необходимых файлов
    _gen_jupyterhub_config(users, courses, out_dir / "jupyterhub_config.py")
    _gen_nbgrader_configs(courses, out_dir)
    _gen_jupyter_server_config(out_dir / "jupyter_server_config.py")
    _gen_global_nbgrader_config(out_dir / "global_nbgrader_config.py")
    _gen_setup_script(users, courses, out_dir / "setup.sh")
    _gen_dockerfile(courses, out_dir / "Dockerfile")


# Точка входа
if __name__ == "__main__":
    main()
