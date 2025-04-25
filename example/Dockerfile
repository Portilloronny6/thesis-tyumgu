# Usamos Python 3.13.3-slim-bookworm como base. Puedes usar otra versión si gustas.
# Используем Python 3.13.3-slim-bookworm как основу. Вы можете использовать другую версию, если хотите.
FROM python:3.13.3-slim-bookworm

# 1. Instalar dependencias del sistema.
# - sudo, build-essential, git, etc. pueden ser necesarios para instalar extensiones o para crear usuarios.
# 1. Установить системные зависимости.
# - sudo, build-essential, git и т. д. могут понадобиться для установки расширений или создания пользователей.
RUN apt-get update && apt-get install -y \
    curl \
    sudo \
    build-essential \
    git \
    wget \
    nodejs \
    npm \
    locales \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Configurar locales, para evitar problemas con acentos/caracteres.
# Настройка локали, чтобы избежать проблем с акцентами/символами.
RUN sed -i '/es_ES.UTF-8/s/^# //g' /etc/locale.gen && locale-gen
ENV LANG=es_ES.UTF-8
ENV LANGUAGE=es_ES:es
ENV LC_ALL=es_ES.UTF-8

# 2. Instalar JupyterHub, JupyterLab y nbgrader (más otros paquetes necesarios).
# 2. Установить JupyterHub, JupyterLab и nbgrader (а также другие необходимые пакеты).
RUN pip install --no-cache-dir --upgrade \
    jupyterhub \
    jupyterlab \
    nbgrader \
    && npm install --global configurable-http-proxy


# *** Aquí agregas el symlink ***
RUN mkdir -p /tmp/exchange && \
chmod 777 /tmp/exchange && \
mkdir -p /usr/local/share/nbgrader && \
rm -rf /usr/local/share/nbgrader/exchange && \
ln -s /tmp/exchange /usr/local/share/nbgrader/exchange


# 3. Copiar configuraciones y script de setup.
# 3. Скопировать конфигурации и скрипт настройки.
COPY jupyterhub_config.py /srv/jupyterhub/jupyterhub_config.py
COPY jupyter_server_config.py /usr/local/etc/jupyter/jupyter_server_config.py
COPY course101_nbgrader_config.py /usr/local/etc/jupyter/course101_nbgrader_config.py
COPY course123_nbgrader_config.py /usr/local/etc/jupyter/course123_nbgrader_config.py
COPY global_nbgrader_config.py /usr/local/etc/jupyter/global_nbgrader_config.py
COPY setup.sh /usr/local/bin/setup.sh

# 4. Dar permisos de ejecución al script de setup.
# 4. Назначить права на выполнение скрипту настройки.
RUN chmod +x /usr/local/bin/setup.sh

# 5. Crear el directorio donde vivirá la base de datos de JupyterHub y sus secretos.
# 5. Создать каталог, где будет храниться база данных JupyterHub и его секреты.
RUN mkdir -p /srv/jupyterhub
WORKDIR /srv/jupyterhub

# 6. Exponer el puerto de JupyterHub (por defecto 8000).
# 6. Открыть порт JupyterHub (по умолчанию 8000).
EXPOSE 8000

# 7. Comando final: primero ejecutamos el setup, luego levantamos JupyterHub.
# 7. Финальная команда: сначала запускаем настройку, затем запускаем JupyterHub.
CMD ["/bin/bash", "-c", "/usr/local/bin/setup.sh && exec jupyterhub --config /srv/jupyterhub/jupyterhub_config.py"]