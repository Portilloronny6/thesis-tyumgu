#!/usr/bin/env python3
"""generate_configs.py - Генерация конфигураций JupyterHub и nbgrader на основе файла `users.csv`.

*Нет необходимости вручную добавлять пользователей `grader-<курс>` в CSV.* Скрипт сам создаёт этих пользователей
на основе курсов.

Формат CSV (обязательные заголовки):
    username,role,courses,email,firstname,lastname
    instructor1,instructor,курс1;курс2
    student1,student,курс1

Вывод (директория `--output-dir`):
    jupyterhub_config.py
    setup.sh
    <курс>_nbgrader_config.py

Пример запуска:
    python generate_configs.py users.csv --output-dir generated/
"""

import datetime as _dt
from pathlib import Path
from typing import Dict, List

from helpers import _bash_array

# ---------------------------------------------------------------------------
# Константы
# ---------------------------------------------------------------------------

# Заголовок для автогенерируемых файлов
_HEADER = (
    "# --------------------------------------------------------------\n"
    "#  THIS FILE IS AUTO‑GENERATED                                   \n"
    "#  Generated: {timestamp} UTC                                    \n"
    "# --------------------------------------------------------------"
)


# ---------------------------------------------------------------------------
# Генераторы файлов
# ---------------------------------------------------------------------------


def _gen_jupyterhub_config(users: Dict, courses: Dict, out_path: Path):
    """Генерация файла jupyterhub_config.py."""

    timestamp = _dt.datetime.now().isoformat()
    L: List[str] = []

    L.append(_HEADER.format(timestamp=timestamp))
    L.append("c = get_config()\n")

    # Разрешённые пользователи
    L.append("# Список пользователей, разрешённых для входа")
    allowed = sorted(users.keys())
    allowed_users_formatted = "[\n" + "\n".join(f"    '{user}'," for user in allowed) + "\n]"
    L.append(f"c.Authenticator.allowed_users = {allowed_users_formatted}\n")

    L.append("# Список администраторов")
    instructors_all = [u for u, info in users.items() if info["role"] == "instructor"]
    L.append(f"c.Authenticator.admin_users = {instructors_all}\n")

    # Группы пользователей
    L.append("# Группы пользователей для nbgrader")
    L.append("c.JupyterHub.load_groups = {")

    L.append(f"    'instructors': {instructors_all},")

    for cid, buckets in courses.items():
        fg_members = sorted(buckets["instructors"] + buckets["graders"])
        nb_members = sorted(buckets["instructors"] + buckets["students"])
        L.append(f"    'formgrade-{cid}': {fg_members},")
        L.append(f"    'nbgrader-{cid}': {nb_members},")
    L.append("}\n")

    # Назначение ролей
    L.append("# Назначение ролей пользователям")
    L.append("c.JupyterHub.load_roles = roles = [")

    L.append("    {")
    L.append("        'name': 'instructor',")
    L.append("        'groups': ['instructors'],")
    L.append("        'scopes': ['admin:users', 'admin:servers'],")
    L.append("    },")

    L.append("    {")
    L.append("        'name': 'server',")
    L.append("        'scopes': ['inherit'],")
    L.append("    },")

    for cid in sorted(courses):
        L.append(f"    {{")
        L.append(f"        'name': 'formgrade-{cid}',")
        L.append(f"        'groups': ['formgrade-{cid}'],")
        L.append(f"        'scopes': ['access:services!service={cid}'],")
        L.append(f"    }},")

        L.append(f"    {{")
        L.append(f"        'name': 'nbgrader-{cid}',")
        L.append(f"        'groups': ['nbgrader-{cid}'],")
        L.append(f"        'scopes': ['list:services', 'read:services!service={cid}'],")
        L.append(f"    }},")

    L.append("]\n")

    # Сервисы для каждого курса
    L.append("# Определение сервисов для курсов")
    L.append("c.JupyterHub.services = [")

    port_start = 9999
    for idx, cid in enumerate(sorted(courses)):
        port = port_start - idx
        guser = f"grader-{cid}"
        service_block = f"""    {{
        'name': '{cid}',
        'url': 'http://127.0.0.1:{port}',
        'command': [
            'jupyterhub-singleuser',
            '--debug',
        ],
        'user': '{guser}',
        'cwd': '/home/{guser}',
        'environment': {{'JUPYTERHUB_DEFAULT_URL': '/lab'}},
        'api_token': '{{{{{cid}_token}}}}',
    }},"""
        L.append(service_block)
    L.append("]\n")

    out_path.write_text("\n".join(L))
    print(f"✅ jupyterhub_config -> {out_path}")


def _gen_nbgrader_configs(courses: Dict, out_dir: Path):
    """Генерация индивидуальных конфигураций nbgrader для каждого курса."""

    ts = _dt.datetime.now().isoformat()
    for cid in courses:
        root = f"/home/grader-{cid}/{cid}"
        cfg = _HEADER.format(timestamp=ts) + (
            f"\nc = get_config()\n"
            f"c.CourseDirectory.root = '{root}'\n"
            f"c.CourseDirectory.course_id = '{cid}'\n"
        )
        # Сохраняем конфигурацию курса
        (out_dir / f"{cid}_nbgrader_config.py").write_text(cfg)
        print(f"✅ {cid}_nbgrader_config -> {out_dir / f'{cid}_nbgrader_config.py'}")

    print("\n✅ Все nbgrader-конфигурации сгенерированы\n")


def _gen_global_nbgrader_config(out_path: Path):
    """Генерация глобального конфигурационного файла nbgrader, который будет использоваться всеми пользователями."""

    content = (
            _HEADER.format(timestamp=_dt.datetime.now().isoformat())
            + "\n"
            + "from nbgrader.auth import JupyterHubAuthPlugin\n"
            + "c = get_config()\n"
            + "c.Exchange.path_includes_course = True\n"
            + "c.Authenticator.plugin_class = JupyterHubAuthPlugin\n"
    )
    out_path.write_text(content)
    print(f"✅ global_nbgrader_config -> {out_path}")


def _gen_jupyter_server_config(out_path: Path):
    """Создание минимальной конфигурации Jupyter Server для ослабления CSP-политики (необходимое для nbgrader)."""

    content = (
            _HEADER.format(timestamp=_dt.datetime.now().isoformat())
            + "\n"
            + "c = get_config()\n"
            + "c.ServerApp.tornado_settings = {}\n"
            + 'c.ServerApp.tornado_settings["headers"] = {\n'
            + "    \"Content-Security-Policy\": \"frame-ancestors 'self'\"\n"
            + "}\n"
    )
    out_path.write_text(content)
    print(f"✅ jupyter_server_config -> {out_path}")


def _gen_setup_script(users: Dict, courses: Dict, out_path: Path):
    """Генерация Bash-скрипта setup.sh для автоматической настройки JupyterHub и пользователей."""

    ts = _dt.datetime.now().isoformat()

    # Списки пользователей и курсов
    instructors = sorted([u for u, info in users.items() if info["role"] == "instructor"])
    students = sorted([u for u, info in users.items() if info["role"] == "student"])
    graders = sorted([u for u, info in users.items() if info["role"] == "grader"])
    course_ids = sorted(courses.keys())

    L: List[str] = [_HEADER.format(timestamp=ts)]

    # Начало скрипта Bash
    L += [
        "#!/usr/bin/env bash",
        "set -e",
        "",
        # Функция создания директории с правами доступа
        'setup_directory () {',
        '    local directory="${1}"',
        '    local permissions="${2:-}"',
        '    echo "Создание \'${directory}\' с разрешениями \'${permissions}\'"',
        '    if [ ! -d "${directory}" ]; then',
        '        mkdir -p "${directory}"',
        '        if [[ ! -z "${permissions}" ]]; then',
        '            chmod "${permissions}" "${directory}"',
        '        fi',
        '    fi',
        '}',
        "",
        # Функция создания пользователя
        'make_user () {',
        '    local user="${1}"',
        '    echo "Создание пользователя \'${user}\'"',
        '    useradd "${user}"',
        '    yes "${user}" | passwd "${user}"',
        '    mkdir "/home/${user}"',
        '    chown "${user}:${user}" "/home/${user}"',
        '}',
        "",
        # Функция получения токена для пользователя
        'get_token () {',
        '    local jupyterhub_root="${1}"',
        '    local user="${2}"',
        '    local currdir="$(pwd)"',
        '    cd "${jupyterhub_root}"',
        '    local token=$(jupyterhub token "${user}")',
        '    cd "${currdir}"',
        '    echo "$token"',
        '}',
        "",
        # Функция настройки nbgrader
        'setup_nbgrader () {',
        '    USER="${1}"',
        '    HOME_DIR="/home/${USER}"',
        '    local CONFIG_FILE="${2}"',
        '    local runas="sudo -u ${USER}"',
        '',
        '    ${runas} mkdir -p "${HOME_DIR}/.jupyter"',
        '    ${runas} cp "${CONFIG_FILE}" "${HOME_DIR}/.jupyter/nbgrader_config.py"',
        '    ${runas} chown "${USER}:${USER}" "${HOME_DIR}/.jupyter/nbgrader_config.py"',
        '}',
        "",
        # Функция конфигурации расширений Jupyter в зависимости от роли
        'configure_role_extensions () {',
        '    local USER="${1}"',
        '    local ROLE="${2}"',
        '    local runas="sudo -u ${USER}"',
        '',
        '    ${runas} jupyter labextension disable --level=user @jupyter/nbgrader:create-assignment || true',
        '    ${runas} jupyter labextension disable --level=user @jupyter/nbgrader:assignment-list || true',
        '    ${runas} jupyter labextension disable --level=user @jupyter/nbgrader:formgrader || true',
        '    ${runas} jupyter labextension disable --level=user @jupyter/nbgrader:course-list || true',
        '',
        '    ${runas} jupyter server extension disable --user nbgrader.server_extensions.formgrader || true',
        '    ${runas} jupyter server extension disable --user nbgrader.server_extensions.assignment_list || true',
        '    ${runas} jupyter server extension disable --user nbgrader.server_extensions.course_list || true',
        '',
        '    case "${ROLE}" in',
        '        student)',
        '            ${runas} jupyter labextension enable --level=user @jupyter/nbgrader:assignment-list',
        '            ${runas} jupyter server extension enable --user nbgrader.server_extensions.assignment_list',
        '            ;;',
        '        instructor)',
        '            ${runas} jupyter labextension enable --level=user @jupyter/nbgrader:assignment-list',
        '            ${runas} jupyter server extension enable --user nbgrader.server_extensions.assignment_list',
        '            ${runas} jupyter labextension enable --level=user @jupyter/nbgrader:course-list',
        '            ${runas} jupyter server extension enable --user nbgrader.server_extensions.course_list',
        '            ;;',
        '        grader)',
        '            ${runas} jupyter labextension enable --level=user @jupyter/nbgrader:create-assignment',
        '            ${runas} jupyter labextension enable --level=user @jupyter/nbgrader:formgrader',
        '            ${runas} jupyter server extension enable --user nbgrader.server_extensions.formgrader',
        '            ;;',
        '    esac',
        '}',
        "",
        # Функция очистки старых данных JupyterHub
        'setup_jupyterhub () {',
        '    local jupyterhub_root="/srv/jupyterhub/jupyterhub"',
        '',
        '    echo "Настройка JupyterHub для работы в \'${jupyterhub_root}\'"',
        '',
        '    setup_directory ${jupyterhub_root}',
        '',
        '    rm -f "${jupyterhub_root}/jupyterhub.sqlite"',
        '    rm -f "${jupyterhub_root}/jupyterhub_cookie_secret"',
        '}',
        "",
        # Функция создания структуры курса
        'create_course_structure () {',
        '    local USER="${1}"',
        '    local COURSE_NAME="${2}"',
        '    local HOME_DIR="/home/${USER}"',
        '',
        '    mkdir -p "${HOME_DIR}/${COURSE_NAME}/source"',
        '    mkdir -p "${HOME_DIR}/${COURSE_NAME}/release"',
        '    mkdir -p "${HOME_DIR}/${COURSE_NAME}/submitted"',
        '    mkdir -p "${HOME_DIR}/${COURSE_NAME}/feedback"',
        '',
        '    if [ -f "${HOME_DIR}/.jupyter/nbgrader_config.py" ]; then',
        '        cp "${HOME_DIR}/.jupyter/nbgrader_config.py" "${HOME_DIR}/${COURSE_NAME}/nbgrader_config.py"',
        '    fi',
        '',
        '    chown -R "${USER}:${USER}" "${HOME_DIR}/${COURSE_NAME}"',
        '}',
    ]

    # Arrays пользователей и курсов для Bash
    L += [
        "",
        _bash_array('instructors', instructors),
        _bash_array('students', students),
        _bash_array('graders', graders),
        _bash_array('courses', course_ids),
    ]

    # Основной процесс скрипта
    L += [
        "",
        'echo "=== Запуск setup.sh ==="',
        "",
        "# 1. Настроить JupyterHub",
        'jupyterhub_root="$1"',
        'setup_jupyterhub "$jupyterhub_root"',
        "",
        "# 2. Создать директорию обмена для nbgrader",
        'setup_directory "/tmp/exchange" 777',
        "",
        "# 3. Создать пользователей",
        'for u in "${instructors[@]}"; do make_user "$u"; done',
        'for u in "${graders[@]}"; do make_user "$u"; done',
        'for u in "${students[@]}"; do make_user "$u"; done',
        "",
        "# 4. Установить глобальный nbgrader config",
        "mkdir -p /etc/jupyter/",
        "cp /usr/local/etc/jupyter/global_nbgrader_config.py /etc/jupyter/nbgrader_config.py",
        "",
        "# 5. Настроить nbgrader и расширения",
        'for index in "${!courses[@]}"; do',
        '    course="${courses[${index}]}"',
        '    instructor="${instructors[$(( index % ${#instructors[@]} ))]}"',
        '    token=$(get_token "$jupyterhub_root" "$instructor")',
        '    config="/srv/jupyterhub/jupyterhub_config.py"',
        '    new_config=$(sed "s/{{${course}_token}}/${token}/g" "$config")',
        '    echo "$new_config" > "$config"',
        "",
        '    setup_nbgrader "grader-${course}" "/usr/local/etc/jupyter/${course}_nbgrader_config.py"',
        '    create_course_structure "grader-${course}" "$course"',
        '    configure_role_extensions "grader-${course}" "grader"',
        "done",
        "",
        'for instructor in "${instructors[@]}"; do',
        '    configure_role_extensions "$instructor" "instructor"',
        "done",
        "",
        "# 6. Настроить расширения для студентов",
        'for student in "${students[@]}"; do',
        '    configure_role_extensions "$student" "student"',
        "done",
        "",
        'echo "=== setup.sh: Готово ==="',
    ]

    L.append("echo '✔️  Настройка завершена.'")

    out_path.write_text("\n".join(L))
    out_path.chmod(0o755)
    print(f"✅ setup.sh -> {out_path}")


def _gen_dockerfile(courses: Dict, out_path: Path):
    """Генерация Dockerfile, который копирует по одному конфигурационному файлу nbgrader для каждого курса."""

    L: List[str] = []

    # Заголовок Dockerfile
    L.append("# Автоматически сгенерированный Dockerfile на основе users.csv")
    L.append("# -----------------------------------------------------------")
    L.append("FROM python:3.13.3-slim-bookworm")
    L.append("")

    # 1. Установка системных зависимостей
    L.append("# 1. Системные зависимости")
    L.append("RUN apt-get update && apt-get install -y \\")
    L.append("    curl sudo build-essential git wget nodejs npm locales \\")
    L.append("    && apt-get clean && rm -rf /var/lib/apt/lists/*")
    L.append("")

    # Настройка локали
    L.append("# Настройка локали на испанский язык")
    L.append("RUN sed -i '/es_ES.UTF-8/s/^# //g' /etc/locale.gen && locale-gen")
    L.append("ENV LANG=es_ES.UTF-8")
    L.append("ENV LANGUAGE=es_ES:es")
    L.append("ENV LC_ALL=es_ES.UTF-8")
    L.append("")

    # 2. Установка Python-пакетов и Jupyter пакетов
    L.append("# 2. Установка пакетов Python и Jupyter")
    L.append("RUN pip install --no-cache-dir --upgrade \\")
    L.append("    jupyterhub jupyterlab nbgrader \\")
    L.append("    && npm install --global configurable-http-proxy")
    L.append("")

    # 3. Создание символьной ссылки для каталога обмена nbgrader
    L.append("# 3. Символическая ссылка для каталога обмена nbgrader")
    L.append("RUN mkdir -p /tmp/exchange && chmod 777 /tmp/exchange && \\")
    L.append("    mkdir -p /usr/local/share/nbgrader && \\")
    L.append("    rm -rf /usr/local/share/nbgrader/exchange && \\")
    L.append("    ln -s /tmp/exchange /usr/local/share/nbgrader/exchange")
    L.append("")

    # 4. Копирование конфигурационных файлов в контейнер
    L.append("# 4. Копирование конфигураций в контейнер")
    L.append("COPY jupyterhub_config.py /srv/jupyterhub/jupyterhub_config.py")
    L.append("COPY jupyter_server_config.py /usr/local/etc/jupyter/jupyter_server_config.py")

    for cid in sorted(courses):
        L.append(f"COPY {cid}_nbgrader_config.py /usr/local/etc/jupyter/{cid}_nbgrader_config.py")

    L.append("COPY global_nbgrader_config.py /usr/local/etc/jupyter/global_nbgrader_config.py")
    L.append("COPY setup.sh /usr/local/bin/setup.sh")
    L.append("")

    # Сделать скрипт setup.sh исполняемым
    L.append("RUN chmod +x /usr/local/bin/setup.sh")
    L.append("")

    # Настройка рабочей директории
    L.append("RUN mkdir -p /srv/jupyterhub")
    L.append("WORKDIR /srv/jupyterhub")
    L.append("")

    # Открыть порт для JupyterHub
    L.append("EXPOSE 8000")
    L.append("")

    # Команда запуска контейнера
    L.append(
        'CMD ["/bin/bash", "-c", "/usr/local/bin/setup.sh && exec jupyterhub --config /srv/jupyterhub/jupyterhub_config.py"]')

    out_path.write_text("\n".join(L) + "\n")
    print(f"✅ Dockerfile -> {out_path}")
