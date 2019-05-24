DATA_PATH = "data"
DOCKER_PATH = "containers"
DOCKER_INCLUDES = "containers/includes"
INI_PATH = "project.ini"
MODEL_PATH = "model"
OUTPUT_PATH = "output"
SOURCE_PATH = "src"
TMP_BUILD_PATH = "tmp"

DOCKER_TAG_SUFFIX = "harborml_"

DOCKERFILE_EXTENSION = ".dockerfile"

DEFAULT_CONTAINER_COMMAND = "tail -f /dev/null"

DEFAULT_DIR_IN_CONTAINER = "/var/harborml"

DEFAULT_DOCKERFILE_NAME = "default.dockerfile"
DEFAULT_DOCKERFILE_CONTENTS = """FROM python
RUN pip install scikit-learn pandas flask"""

DEFAULT_NGINX_NAME = "nginx"
DEFAULT_NGINX_CONTENTS = """FROM nginx:alpine
RUN apk update && apk add bash
COPY includes/nginx.conf /etc/nginx/nginx.conf
"""
NGINX_CONF_IN_CONTAINER_PATH = "/etc/nginx/nginx.conf"
