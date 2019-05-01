import docker as _docker
import errno as _errno
import os as _os
import random as _random
import tarfile as _tarfile
import shutil as _shutil

from . import constants as _constants

def _check_project_dir(project_root_dir):
    if not _os.path.isdir(project_root_dir):
        raise FileNotFoundError("Provided path is not a valid directory")

def _fix_path(path):
    return path.replace('\\', '/')

def _build_relative_path(project_root_dir, relative_path):
    project_root_dir = _fix_path(project_root_dir)
    relative_path = _fix_path(relative_path)
    if len(project_root_dir) > 0 and project_root_dir[-1] != '/':
        project_root_dir += '/'
    x = project_root_dir + relative_path
    return _fix_path(x)

def _check_and_format_file(project_root_dir, relative_path):
    file_path = _build_relative_path(project_root_dir, relative_path)
    if not _os.path.isfile(project_root_dir + relative_path):
        raise FileNotFoundError("Provided path is not a valid file")
    return file_path

def _mkdir_p(path):
    try:
        _os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == _errno.EEXIST and _os.path.isdir(path):
            pass
        else:
            raise

def _docker_client():
    return _docker.from_env()

def _docker_image_tag(container_name):
    return _constants.DOCKER_TAG_SUFFIX + container_name + ":latest"

def _build_container(project_root_dir, container_name):
    container_dockerfile = container_name + _constants.DOCKERFILE_EXTENSION
    container_path = _check_and_format_file(project_root_dir, _constants.DOCKER_PATH + '/' + container_dockerfile)
    container_tag = _docker_image_tag(container_name)
    tmp_build_path = _build_relative_path(project_root_dir, _constants.TMP_BUILD_PATH + '/' + container_name)
    tmp_container_path = _build_relative_path(tmp_build_path, container_dockerfile)
    docker_includes_path = _build_relative_path(project_root_dir, _constants.DOCKER_INCLUDES)
    try:
        _os.mkdir(tmp_build_path)
        _shutil.copy(container_path, tmp_build_path)
        _shutil.copytree(docker_includes_path, _build_relative_path(tmp_build_path, _constants.DOCKER_INCLUDES))
        client = _docker_client()
        with open(tmp_container_path, 'rb') as f:
            client.images.build(
                fileobj = f,
                path = tmp_build_path,
                tag = container_tag,
                quiet = False
            )
    finally:
        _shutil.rmtree(tmp_build_path)
        pass
    return container_tag

def _start_container(image_tag) -> _docker.models.containers.Container:
    client = _docker_client()
    container = client.containers.run(
        image_tag, 
        command = _constants.DEFAULT_CONTAINER_COMMAND,
        detach = True)
    
    container.exec_run("mkdir " + _constants.DEFAULT_DIR_IN_CONTAINER)
    container.exec_run(
        "mkdir " + _build_relative_path(_constants.DEFAULT_DIR_IN_CONTAINER, _constants.OUTPUT_PATH))
    return container

def _random_file_name(length = 16):
    validchars = "0123456789abcdefghijklmnopqrstuvwxyz"
    filename = ''
    for _ in range(length):
        filename += _random.choice(validchars)
    return filename

def _tar_it(project_root_dir, file_dir):
    rand_file_name = _build_relative_path(
        project_root_dir, _constants.TMP_BUILD_PATH
        ) + '/' + _random_file_name() + '.tar'
    tar = _tarfile.open(rand_file_name, mode='w')
    try:
        tar.add(file_dir, arcname='')
    finally:
        tar.close()
    return rand_file_name

def _copy_directory_to_container(project_root_dir, srcpath, dstpath, container):
    tar_file = _tar_it(project_root_dir, srcpath)
    try:
        data = open(tar_file, 'rb').read()
        container.exec_run('mkdir -p "' + dstpath + '"')
        container.put_archive(dstpath, data)
    finally:
        _os.remove(tar_file)

def _copy_project_to_container(project_root_dir, container):
    src_src_path = _build_relative_path(project_root_dir, _constants.SOURCE_PATH)
    src_dst_path = _constants.DEFAULT_DIR_IN_CONTAINER + '/' + _constants.SOURCE_PATH
    _copy_directory_to_container(project_root_dir, src_src_path, src_dst_path, container)
    
    data_src_path = _build_relative_path(project_root_dir, _constants.DATA_PATH)
    data_dst_path = _constants.DEFAULT_DIR_IN_CONTAINER + '/' + _constants.DATA_PATH
    _copy_directory_to_container(project_root_dir, data_src_path, data_dst_path, container)

def _copy_output_to_project(project_root_dir, container, model_name):
    src_path = _constants.DEFAULT_DIR_IN_CONTAINER + '/' + _constants.OUTPUT_PATH
    dst_path = _build_relative_path(
        _build_relative_path(project_root_dir, _constants.MODEL_PATH),
        model_name)
    _mkdir_p(dst_path)
    with open(dst_path + '.tar', 'wb') as f:
        bits, _ = container.get_archive(src_path)
        for chunk in bits:
            f.write(chunk)
    
    with _tarfile.open(dst_path + '.tar') as tf:
        tf.extractall(dst_path)
    _os.remove(dst_path + '.tar')
    return dst_path

def _get_train_model_command(train_model_file):
    commands = []
    commands.append('cd "' + _constants.DEFAULT_DIR_IN_CONTAINER + '"')
    if len(train_model_file) > 3 and train_model_file[-3:] == '.py':
        tmf_path = _build_relative_path(_constants.SOURCE_PATH, train_model_file)
        commands.append('python "' +  tmf_path + '"')
    cmd = 'bash -c  "' + ' && '.join(commands).replace('"', '\\"') + '"'
    return cmd


def start_project(project_root_dir):
    """Creates a new harborml project in the provided directory

    Args:
        project_root_dir: The root directory of the project"""
    _check_project_dir(project_root_dir)
    _mkdir_p(_build_relative_path(project_root_dir, _constants.TMP_BUILD_PATH))
    _mkdir_p(_build_relative_path(project_root_dir, _constants.DATA_PATH))
    _mkdir_p(_build_relative_path(project_root_dir, _constants.DOCKER_PATH))
    _mkdir_p(_build_relative_path(project_root_dir, _constants.DOCKER_INCLUDES))
    _mkdir_p(_build_relative_path(project_root_dir, _constants.MODEL_PATH))
    _mkdir_p(_build_relative_path(project_root_dir, _constants.SOURCE_PATH))

def train_model(project_root_dir, container_name, train_model_file, model_name = None, save_history = False, 
    stop_container = True):
    if model_name is None:
        model_name, _ = _os.path.splitext(train_model_file)
        model_name = model_name.replace('/', '-')

    _check_project_dir(project_root_dir)
    print("Building container...")
    image_tag = _build_container(project_root_dir, container_name)
    print("Starting container...")
    container = _start_container(image_tag)
    try:
        print("Copying project to container...")
        _copy_project_to_container(project_root_dir, container)
        cmd = _get_train_model_command(train_model_file)
        print("Running command in container: " + cmd)
        result = container.exec_run(cmd)
        if result.exit_code != 0:
            raise RuntimeError("Error while running container command: " + result.output)
        print("Copying output back to project")
        output_dir = _copy_output_to_project(project_root_dir, container, model_name)
        print("Run output written to " + output_dir)
    finally:
        if stop_container and container != None:
            print("Stopping container...")
            #container.stop()
        if not stop_container and container != None:
            print("Container still running")
            return container
    
