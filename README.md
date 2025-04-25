# README – Генератор конфигурации JupyterHub + nbgrader

### Что делают эти скрипты?

Поддерживать вручную все конфигурации **JupyterHub** и **nbgrader** при десятках курсов и сотнях пользователей — задача неблагодарная. Набор скриптов берёт&nbsp;один‑единственный `users.csv` и автоматически создаёт:

* `jupyterhub_config.py` с группами, правами и сервисами.
* `global_nbgrader_config.py` с общими настройками.
* `<course>_nbgrader_config.py` — по одному на курс.
* `jupyter_server_config.py` — базовые CSP‑заголовки.
* `setup.sh` — Bash‑скрипт, который заводит пользователей и включает расширения.
* `Dockerfile` — собирает образ со всем выше перечисленным.

### Требования

| Инструмент | Минимальная версия |
|------------|-------------------|
| Python     | 3.9 |
| pip        | 23 |
| nbgrader   | 0.9.x |
| JupyterHub | 4.x |

Установка зависимостей (пример):

```bash
python -m venv venv
source venv/bin/activate
pip install jupyterhub nbgrader jupyterlab
```

### Формат `users.csv`

Обязательные колонки:

```
username,role,courses,email,firstname,lastname
```

* **`username`** — системное имя пользователя, которое станет и паролем.
* **`role`** — `instructor` или `student`. `grader` добавляется автоматически для каждого курса.
* **`courses`** — список через `;`. Пробелы, «‑» и «_» будут удалены при формировании `course_id`.
* `email`, `firstname`, `lastname` — опционально.

Пример:

```csv
username,role,courses
ivanov,instructor,intro‑python;data‑structures
stud0001,student,intro‑python
stud0002,student,data‑structures
```

### Быстрый старт

```bash
# 1. Генерируем конфиги
python generate_configs.py users.csv --output-dir build

# 2. Собираем Docker‑образ
cd build
docker build -t jhub-nbgrader .

# 3. Запускаем контейнер
docker run -d --name jhub -p 8000:8000 jhub-nbgrader
```

Порты сервисов *Formgrader* назначаются, начиная с `9999` и дальше вниз. При необходимости поменяйте константы в `files_generators.py`.

### Кастомизация

1. **Базовый образ** — правьте строку `FROM python:3.13.3-slim-bookworm` в генераторе `Dockerfile`.
2. **Расширения Jupyter** — функция `_gen_setup_script()` в `files_generators.py`.
3. **Настройки nbgrader на курс** — `_gen_nbgrader_configs()`.
4. **Дополнительные роли** — расширьте `helpers._parse_csv()`.

---
