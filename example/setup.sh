#!/usr/bin/env bash
set -e

# Función para crear un directorio con permisos opcionales
# Функция создания каталога с дополнительными разрешениями
setup_directory () {
    local directory="${1}"
    local permissions="${2:-}"
    echo "Создание '${directory}' с разрешениями '${permissions}'"
    if [ ! -d "${directory}" ]; then
        mkdir -p "${directory}"
        if [[ ! -z "${permissions}" ]]; then
            chmod "${permissions}" "${directory}"
        fi
    fi
}

# Función para crear usuario (instructor/estudiante)
# Функция создания пользователя (преподаватель/студент)
make_user () {
    local user="${1}"
    echo "Создание пользователя '${user}'"
    useradd "${user}"
    yes "${user}" | passwd "${user}"
    mkdir "/home/${user}"
    chown "${user}:${user}" "/home/${user}"
}

# Configurar nbgrader para un usuario especificando un archivo de config a copiar
# Настройте nbgrader для пользователя, указав файл конфигурации для копирования.
setup_nbgrader () {
    USER="${1}"
    HOME_DIR="/home/${USER}"

    local CONFIG_FILE="${2}"
    local runas="sudo -u ${USER}"

    # Sustituye el placeholder {username} por el nombre real del usuario
    # Замените заполнитель {username} на фактическое имя пользователя.

    # Crear carpeta .jupyter si no existe y copiar nbgrader_config
    # Создайте папку .jupyter, если она не существует, и скопируйте nbgrader_config
    ${runas} mkdir -p "${HOME_DIR}/.jupyter"
    ${runas} cp "${CONFIG_FILE}" "${HOME_DIR}/.jupyter/nbgrader_config.py"
    ${runas} chown "${USER}:${USER}" "${HOME_DIR}/.jupyter/nbgrader_config.py"
}

# Configura las extensiones de nbgrader según el rol del usuario.
configure_role_extensions () {
    local USER="${1}"
    local ROLE="${2}"   # student | instructor | grader
    local runas="sudo -u ${USER}"

    # 1️⃣ Deshabilitar todo para partir de un estado limpio
    ${runas} jupyter labextension disable --level=user @jupyter/nbgrader:create-assignment || true
    ${runas} jupyter labextension disable --level=user @jupyter/nbgrader:assignment-list || true
    ${runas} jupyter labextension disable --level=user @jupyter/nbgrader:formgrader || true
    ${runas} jupyter labextension disable --level=user @jupyter/nbgrader:course-list || true

    ${runas} jupyter server extension disable --user nbgrader.server_extensions.formgrader || true
    ${runas} jupyter server extension disable --user nbgrader.server_extensions.assignment_list || true
    ${runas} jupyter server extension disable --user nbgrader.server_extensions.course_list || true

    # 2️⃣ Activar sólo lo necesario para el rol
    case "${ROLE}" in
        student)
            ${runas} jupyter labextension enable --level=user @jupyter/nbgrader:assignment-list
            ${runas} jupyter server extension enable --user nbgrader.server_extensions.assignment_list
            ;;
        instructor)
            ${runas} jupyter labextension enable --level=user @jupyter/nbgrader:assignment-list
            ${runas} jupyter server extension enable --user nbgrader.server_extensions.assignment_list
            ${runas} jupyter labextension enable --level=user @jupyter/nbgrader:course-list
            ${runas} jupyter server extension enable --user nbgrader.server_extensions.course_list
            ;;
        grader)
            ${runas} jupyter labextension enable --level=user @jupyter/nbgrader:create-assignment
            ${runas} jupyter labextension enable --level=user @jupyter/nbgrader:formgrader
            ${runas} jupyter server extension enable --user nbgrader.server_extensions.formgrader
            ;;
    esac
}

# Configurar JupyterHub
# Настроить JupyterHub
setup_jupyterhub () {
    local jupyterhub_root="/srv/jupyterhub/jupyterhub"

    echo "Настройка JupyterHub для работы в '${jupyterhub_root}'"

    setup_directory ${jupyterhub_root}

    rm -f "${jupyterhub_root}/jupyterhub.sqlite"
    rm -f "${jupyterhub_root}/jupyterhub_cookie_secret"

    # Copy config file.
}

create_course_structure () {
    local USER="${1}"
    local COURSE_NAME="${2}"
    local HOME_DIR="/home/${USER}"

    # Crear la carpeta base
    mkdir -p "${HOME_DIR}/${COURSE_NAME}"

    # Crear subcarpetas esenciales
    mkdir -p "${HOME_DIR}/${COURSE_NAME}/source"
    mkdir -p "${HOME_DIR}/${COURSE_NAME}/release"
    mkdir -p "${HOME_DIR}/${COURSE_NAME}/submitted"
    mkdir -p "${HOME_DIR}/${COURSE_NAME}/feedback"

    # (Opcional) Copiar la config nbgrader del instructor a la carpeta
    if [ -f "${HOME_DIR}/.jupyter/nbgrader_config.py" ]; then
        cp "${HOME_DIR}/.jupyter/nbgrader_config.py" "${HOME_DIR}/${COURSE_NAME}/nbgrader_config.py"
    fi

    chown -R "${USER}:${USER}" "${HOME_DIR}/${COURSE_NAME}"
}

get_token () {
    local jupyterhub_root="${1}"
    local user="${2}"
    local currdir="$(pwd)"
    cd "${jupyterhub_root}"
    local token=$(jupyterhub token "${2}")
    cd "${currdir}"
    echo "$token"
}

# --------------------------------------------------
# Añadir estudiantes a la base de datos de nbgrader
# --------------------------------------------------
add_students_to_nbgrader_db () {
    local GRADER_USER="${1}"   # Cuenta asociada al curso, ej. grader-course101
    local COURSE_NAME="${2}"   # Nombre del curso, ej. course101
    shift 2
    local STUDENT_LIST=("$@")  # El resto de los argumentos son los estudiantes

    local COURSE_DIR="/home/${GRADER_USER}/${COURSE_NAME}"
    local runas="sudo -u ${GRADER_USER}"

    for student in "${STUDENT_LIST[@]}"; do
        echo "Añadiendo ${student} a la base de datos de nbgrader del curso ${COURSE_NAME}"
        ${runas} bash -c "cd ${COURSE_DIR} && nbgrader db student add ${student}"
    done
}

echo "=== Запуск setup.sh ==="

# 1. Configurar JupyterHub (borra DB vieja, etc.)
# 1. Настройте JupyterHub (удалите старую БД и т. д.)
jupyterhub_root="${1}"
setup_jupyterhub "${jupyterhub_root}"

# 2. Crear un directorio de intercambio para nbgrader
# (donde se depositan tareas para que los estudiantes las puedan descargar)

# 2. Создайте каталог подкачки для nbgrader
# (где хранятся задания, чтобы студенты могли их скачать)
setup_directory "/tmp/exchange" 777

# 3. Crear 3 instructores
# 3. Создайте 3 инструкторов
make_user instructor1
make_user instructor2
make_user grader-course101
make_user grader-course123

# 4. Crear 3 estudiantes
# 4. Создайте 3 учеников
make_user student1
make_user student2

# Install global nbgrader config file.
mkdir -p /etc/jupyter/
cp /usr/local/etc/jupyter/global_nbgrader_config.py /etc/jupyter/nbgrader_config.py

# 5. Configurar nbgrader + extensiones para instructores
# 5. Настройте nbgrader + расширения для инструкторов
courses=(course101 course123)
instructors=(instructor1 instructor2)

for index in "${!courses[@]}"; do
    course="${courses[${index}]}"
    instructor="${instructors[${index}]}"

    # Get the JupyterHub API token and update the JupyterHub config with it.
    token=$(get_token "${jupyterhub_root}" "${instructor}")
    config="/srv/jupyterhub/jupyterhub_config.py"
    new_config=$(sed "s/{{${course}_token}}/${token}/g" "${config}")
    echo "${new_config}" > "${config}"

    # Setup nbgrader configuration for grading account.
    setup_nbgrader "grader-${course}" "/usr/local/etc/jupyter/${course}_nbgrader_config.py"
    create_course_structure "grader-${course}" "${course}"

    configure_role_extensions "grader-${course}" "grader"

done

for instructor in ${instructors[@]}; do
    configure_role_extensions "${instructor}" "instructor"
done

# 6. Configurar nbgrader + extensiones para estudiantes
# 6. Настройка nbgrader + расширения для студентов
students=(student1 student2)

# Añadir todos los estudiantes al registro de nbgrader de cada curso
for index in "${!courses[@]}"; do
    course="${courses[${index}]}"
    grader_user="grader-${course}"
    add_students_to_nbgrader_db "${grader_user}" "${course}" "${students[@]}"
done

for student in ${students[@]}; do
    configure_role_extensions "${student}" "student"
done

echo "=== setup.sh: Готово ==="