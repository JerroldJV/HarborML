import configparser as _configparser
import docker as _docker
import errno as _errno
import nginx as _nginx
import os as _os
import pkg_resources as _pkg_resources
import random as _random
import tarfile as _tarfile
import time as _time
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
    if not _os.path.isfile(file_path):
        raise FileNotFoundError("Provided path is not a valid file: {}",format(file_path))
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
    #tmp_container_path = _build_relative_path(tmp_build_path, container_dockerfile)
    docker_includes_path = _build_relative_path(project_root_dir, _constants.DOCKER_INCLUDES)
    try:
        _os.mkdir(tmp_build_path)
        _shutil.copy(container_path, tmp_build_path)
        _shutil.copytree(docker_includes_path, _build_relative_path(tmp_build_path, 'includes'))
        client = _docker_client()
        #with open(tmp_container_path, 'rb') as f:
        client.images.build(
            #fileobj = f,
            path = tmp_build_path,
            dockerfile = container_dockerfile,
            tag = container_tag,
            quiet = False
        )
    finally:
        _shutil.rmtree(tmp_build_path, ignore_errors=True)
        pass
    return container_tag

def _start_container(image_tag, port_mappings = {}, hostname = None) -> _docker.models.containers.Container:
    client = _docker_client()
    container = client.containers.run(
        image_tag, 
        command = _constants.DEFAULT_CONTAINER_COMMAND,
        ports = port_mappings,
        detach = True,
        #remove = True,
        hostname = hostname)
    
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
        container.exec_run('mkdir -p "' + dstpath + '"', detach = True)
        # introducing potential race condition :::::((((((  but the above exec fails sometimes for no reason and hangs
        _time.sleep(.1)
        container.put_archive(dstpath, data)
    finally:
        _os.remove(tar_file)

def _copy_project_to_container(project_root_dir, container, include_data = True, include_model = None):
    src_src_path = _build_relative_path(project_root_dir, _constants.SOURCE_PATH)
    src_dst_path = _constants.DEFAULT_DIR_IN_CONTAINER + '/' + _constants.SOURCE_PATH
    _copy_directory_to_container(project_root_dir, src_src_path, src_dst_path, container)
    if include_data:
        data_src_path = _build_relative_path(project_root_dir, _constants.DATA_PATH)
        data_dst_path = _constants.DEFAULT_DIR_IN_CONTAINER + '/' + _constants.DATA_PATH
        _copy_directory_to_container(project_root_dir, data_src_path, data_dst_path, container)
    if include_model is not None:
        mdl_src_path = _build_relative_path(
            _build_relative_path(project_root_dir, _constants.MODEL_PATH),
            include_model)
        mdl_dst_path = _build_relative_path(
            _build_relative_path(_constants.DEFAULT_DIR_IN_CONTAINER, _constants.MODEL_PATH),
            include_model)
        _copy_directory_to_container(project_root_dir, mdl_src_path, mdl_dst_path, container)

def _copy_output_to_project(project_root_dir, container, relative_target_directory):
    src_path = _constants.DEFAULT_DIR_IN_CONTAINER + '/' + _constants.OUTPUT_PATH
    dst_path = _build_relative_path(project_root_dir, relative_target_directory)
    _mkdir_p(dst_path)
    with open(dst_path + '.tar', 'wb') as f:
        bits, _ = container.get_archive(src_path)
        for chunk in bits:
            f.write(chunk)
    
    with _tarfile.open(dst_path + '.tar') as tf:
        tf.extractall(dst_path)
    
    source_dir = _build_relative_path(dst_path, 'output')
    for filename in _os.listdir(source_dir):
        srcfile = _build_relative_path(source_dir, filename)
        tgtfile = _build_relative_path(dst_path, filename)
        _shutil.move(srcfile, tgtfile)
    _shutil.rmtree(source_dir)
    _os.remove(dst_path + '.tar')
    return dst_path

def _copy_data_to_project(project_root_dir, container, model_name):
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

def _get_file_type(file_name):
    if len(file_name) > 3 and file_name[-3:].lower() == '.py':
        return 'python'
    elif len(file_name) > 2 and file_name[-2:].lower() == '.r':
        return 'r'
    return None

def _extract_refresh_data_name(data_refresh_file):
    filename = _os.path.basename(data_refresh_file)
    filename = filename.split('.')[0]
    filename_split = filename.split('_')
    if len(filename_split) <= 1 or filename_split[0].lower() not in _constants.REFRESH_FILE_SUFFIXES:
        raise IOError("Cannot extract valid dataset_name from file, please manually provide dataset_name")
    return '_'.join(filename_split[1:]).lower()

def _extract_train_model_name(train_model_file):
    filename = _os.path.basename(train_model_file)
    filename = filename.split('.')[0]
    filename_split = filename.split('_')
    if len(filename_split) <= 1 or filename_split[0].lower() not in _constants.TRAIN_FILE_SUFFIXES:
        raise IOError("Cannot extract valid model_name from file, please manually provide model_name")
    return '_'.join(filename_split[1:]).lower()
    
def _extract_deploy_model_name(model_api_file):
    filename = _os.path.basename(model_api_file)
    filename = filename.split('.')[0]
    filename_split = filename.split('_')
    if len(filename_split) <= 1 or filename_split[0].lower() not in _constants.DEPLOY_FILE_SUFFIXES:
        raise IOError("Cannot extract valid model_name from file, please manually provide model_name")
    return '_'.join(filename_split[1:]).lower()

def _get_train_model_command(train_model_file):
    commands = []
    commands.append('cd "' + _constants.DEFAULT_DIR_IN_CONTAINER + '"')
    file_type = _get_file_type(train_model_file)
    if file_type == 'python':
        tmf_path = _build_relative_path(_constants.SOURCE_PATH, train_model_file)
        commands.append('python "' +  tmf_path + '" |& tee -a ./output/log.log')
    elif file_type == 'r':
        tmf_path = _build_relative_path(_constants.SOURCE_PATH, train_model_file)
        commands.append('Rscript "' +  tmf_path + '" |& tee -a ./output/log.log')
    cmd = 'bash -c  "' + ' && '.join(commands).replace('"', '\\"') + '"'
    return cmd

def _get_refresh_data_command(data_refresh_file):
    return _get_train_model_command(data_refresh_file)

def _get_flask_deploy_command(flask_path):
    commands = []
    commands.append('cd "' + _constants.DEFAULT_DIR_IN_CONTAINER + '"')
    api_path = _build_relative_path(_constants.DEFAULT_DIR_IN_CONTAINER, flask_path)
    commands.append('export FLASK_APP="' +  api_path + '"')
    commands.append('export FLASK_ENV=development')
    commands.append('flask run --host=0.0.0.0 |& tee -a ./output/log.log')
    cmd = 'bash -c  "' + ' && '.join(commands).replace('"', '\\"') + '"'
    return cmd

def _get_plumber_deploy_command(plumber_path):
    commands = []
    commands.append('cd "' + _constants.DEFAULT_DIR_IN_CONTAINER + '"')
    api_path = _build_relative_path(_constants.DEFAULT_DIR_IN_CONTAINER, plumber_path)
    #commands.append('export FLASK_APP="' +  api_path + '"')
    #commands.append('export FLASK_ENV=development')
    #commands.append('flask run --host=0.0.0.0 >> log.log')
    commands.append('R -e \'plumber::plumb(\\"{}\\")$run(host=\\"0.0.0.0\\", port=5000)\' |& tee -a ./output/log.log'.format(api_path))
    cmd = 'bash -c  "' + ' && '.join(commands) + '"'
    return cmd

def _random_hex(num_digits):
    return ''.join(_random.choice('0123456789abcdef') for n in range(num_digits))

def _get_project_config(project_root_dir):
    config = _configparser.ConfigParser()
    config.read(
        _build_relative_path(
            project_root_dir,
            _constants.INI_PATH))
    return config

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
    dockerfile = _build_relative_path(
        _build_relative_path(project_root_dir, _constants.DOCKER_PATH),
        _constants.DEFAULT_DOCKERFILE_NAME)
    with open(dockerfile, 'w') as f:
        f.write(_constants.DEFAULT_DOCKERFILE_CONTENTS)
    
    # copy the default nginx.conf to the docker includes
    _shutil.copy(
        _pkg_resources.resource_filename('harborml', 'static/nginx/nginx.conf'),
        _build_relative_path(project_root_dir, _constants.DOCKER_INCLUDES))

    nginxdockerfile = _build_relative_path(
        _build_relative_path(project_root_dir, _constants.DOCKER_PATH),
        _constants.DEFAULT_NGINX_NAME)
    with open(nginxdockerfile + ".dockerfile", 'w') as f:
        f.write(_constants.DEFAULT_NGINX_CONTENTS)
    
    # build default config
    config = _configparser.ConfigParser()
    config['DEFAULT'] = {
        'PROJECT_ID': _random_hex(32)
    }
    with open(_build_relative_path(project_root_dir, _constants.INI_PATH), 'w') as configfile:
        config.write(configfile)

def build_container(project_root_dir, container_name):
    """Inteface for building a specific container.  This is useful for testing container builds work correctly

    Args:
        project_root_dir: The root directory of the project
        container_name: The name of the container
    """
    _check_project_dir(project_root_dir)
    return _build_container(project_root_dir, container_name)

def train_model(project_root_dir, container_name, train_model_file, model_name = None, save_history = False, 
    stop_container = True):
    if model_name is None:
        model_name = _extract_train_model_name(train_model_file)

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
            raise RuntimeError("Error while running container command: " + str(result.output))
        print("Copying output back to project")
        output_dir = _copy_output_to_project(project_root_dir, container, _build_relative_path(_constants.MODEL_PATH, model_name))
        print("Run output written to " + output_dir)
    finally:
        if stop_container and container != None:
            print("Stopping container...")
            container.stop(timeout = 0)
        if not stop_container and container != None:
            print("Container still running")
            return container

def _deploy_flask_model(project_root_dir, model_api_file, container):
    # create a temporary flask folder, and fill it up
    tmp_flask_root = _build_relative_path(
        _build_relative_path(project_root_dir, _constants.TMP_BUILD_PATH),
        'flask')
    dst_flask_root = _build_relative_path(_constants.DEFAULT_DIR_IN_CONTAINER, 'flask')
    _mkdir_p(tmp_flask_root)
    _shutil.copy(
        _pkg_resources.resource_filename('harborml', 'static/flask/app.py'),
        tmp_flask_root)
    _shutil.copy(
        _pkg_resources.resource_filename('harborml', 'static/flask/loader.py'),
        tmp_flask_root)
    model_api_module = _os.path.splitext(model_api_file)[0]
    with open(_build_relative_path(tmp_flask_root, 'loader.py'), 'a') as f:
        f.write("import sys\n")
        f.write("sys.path.append('{}')\n".format(
            _build_relative_path(
                _constants.DEFAULT_DIR_IN_CONTAINER, 
                _constants.SOURCE_PATH)))
        f.write("import {} as model\n".format(model_api_module))
    # Copy the flask folder to the container
    _copy_directory_to_container(
        project_root_dir, 
        tmp_flask_root, 
        dst_flask_root,
        container)
    _shutil.rmtree(tmp_flask_root)
    # Run the flask app
    cmd = _get_flask_deploy_command('flask/app.py')
    return cmd

def _deploy_plumber_model(project_root_dir, model_api_file, container):
    # create a temporary plumber folder, and fill it up
    tmp_plumber_root = _build_relative_path(
        _build_relative_path(project_root_dir, _constants.TMP_BUILD_PATH),
        'plumber')
    dst_plumber_root = _build_relative_path(_constants.DEFAULT_DIR_IN_CONTAINER, 'plumber')
    _mkdir_p(tmp_plumber_root)
    _shutil.copy(
        _pkg_resources.resource_filename('harborml', 'static/plumber/plumber.R'),
        tmp_plumber_root)
    _shutil.copy(
        _pkg_resources.resource_filename('harborml', 'static/plumber/loader.R'),
        tmp_plumber_root)    
    with open(_build_relative_path(tmp_plumber_root, 'loader.R'), 'a') as f:
        # source the file
        f.write("source('{}')\n".format(
            _build_relative_path(
                _build_relative_path(
                    _constants.DEFAULT_DIR_IN_CONTAINER, 
                    _constants.SOURCE_PATH),
                model_api_file)))

    # Copy the plumber folder to the container
    _copy_directory_to_container(
        project_root_dir, 
        tmp_plumber_root, 
        dst_plumber_root,
        container)
    _shutil.rmtree(tmp_plumber_root)
    # Run the plumber app
    cmd = _get_plumber_deploy_command('plumber/plumber.R')
    return cmd

def _get_docker_name(project_root_dir, model_name):
    proj_id = _get_project_config(project_root_dir)['DEFAULT']['PROJECT_ID']
    return "deploy-{}-{}".format(proj_id, model_name)

def _deploy_reverse_proxy(project_root_dir):
    d_client = _docker_client()
    base_name = _get_docker_name(project_root_dir, '')
    new_name = "reverse_proxy-" + base_name
    already_running = d_client.containers.list(all=True, filters={'name':new_name})
    if len(already_running) > 0:
        if already_running[0].status == 'running':
            print("Reverse proxy already running")
            return already_running[0]
        else:
            already_running[0].remove()

    print("Building reverse proxy container...")
    image_tag = _build_container(project_root_dir, _constants.DEFAULT_NGINX_NAME)
    print("Starting reverse proxy container...")
    rev_proxy = _start_container(image_tag, port_mappings = {5000:5000})
    d_client.api.rename(rev_proxy.id, new_name)
    return rev_proxy

def _get_current_deploy_version(project_root_dir, model_name):
    d_client = _docker_client()
    base_name = _get_docker_name(project_root_dir, model_name)
    deploy_container_names = [x.name for x in d_client.containers.list(all=True, filters = {'name':base_name})]
    version = -1
    for n in deploy_container_names:
        potential_id = int(n.split("-")[-1])
        if version < potential_id:
            version = potential_id
    return version

def _copy_down_nginx_conf(project_root_dir, container):
    src_path = _constants.NGINX_CONF_IN_CONTAINER_PATH
    rng_file_name = _random_file_name()
    dst_path = _build_relative_path(
        _build_relative_path(project_root_dir, _constants.TMP_BUILD_PATH),
        rng_file_name)
        
    _mkdir_p(dst_path)
    with open(dst_path + '.tar', 'wb') as f:
        bits, _ = container.get_archive(src_path)
        for chunk in bits:
            f.write(chunk)
    
    with _tarfile.open(dst_path + '.tar') as tf:
        tf.extractall(dst_path)
    _os.remove(dst_path + '.tar')
    return dst_path

def _copy_up_nginx_conf(project_root_dir, conf_dir, container):
    _copy_directory_to_container(project_root_dir, conf_dir, 'tmp/conf/', container)
    container.exec_run('cp {} {}'.format('tmp/conf/nginx.conf', _constants.NGINX_CONF_IN_CONTAINER_PATH), detach = True)
    _time.sleep(.1)

def _edit_nginx_entry(project_root_dir, rev_proxy_container, model_name, hostname, ip_port, old_hostname = None):
    conf_dir = _copy_down_nginx_conf(project_root_dir, rev_proxy_container)
    try:
        conf_file = _build_relative_path(conf_dir,'nginx.conf')
        c = _nginx.loadf(conf_file)
        http = c.filter('Http')[0]

        endpoint_url = '/{}/'.format(model_name)
        # check for existing upstream entry for item, edit as needed
        if old_hostname is not None:
            for ups in http.filter('Upstream'):
                if ups.value == old_hostname:
                    http.remove(ups)
        # create new hostname entry
        upstream = _nginx.Upstream(hostname)
        upstream.add(_nginx.Key('server', ip_port))
        http.add(
            upstream
        )
        # check for existing location entry and remove if present
        servers = http.filter('Server')
        add2http = False
        if len(servers) > 0:
            server = servers[0]
            for loc in server.filter('Location'):
                if loc.value == endpoint_url:
                    server.remove(loc)
        else:
            add2http = True
            server = _nginx.Server()
            server.add(_nginx.Key('listen', '5000'))
        
        location = _nginx.Location(endpoint_url)
        location.add(
            _nginx.Key('proxy_pass', 'http://{}/'.format(hostname)),
            _nginx.Key('proxy_redirect', 'off'),
            _nginx.Key('proxy_set_header', 'Host $host'),
            _nginx.Key('proxy_set_header', 'X-Real-IP $remote_addr'),
            _nginx.Key('proxy_set_header', 'X-Forwarded-For $proxy_add_x_forwarded_for'),
            _nginx.Key('proxy_set_header', 'X-Forwarded-Host $server_name')
        )

        server.add(location)
        if add2http:
            http.add(server)
        _nginx.dumpf(c, conf_file)
        _copy_up_nginx_conf(project_root_dir, conf_dir, rev_proxy_container)
        # reload nginx on server
        rev_proxy_container.exec_run('/usr/sbin/nginx', detach = True)
        rev_proxy_container.exec_run('/usr/sbin/nginx -s reload', detach = True)
    finally:
        _shutil.rmtree(conf_dir, ignore_errors=True)

def deploy_model(project_root_dir, container_name, model_api_file, model_name = None, include_data = False):
    if model_name is None:
        model_name = _extract_deploy_model_name(model_api_file)
    d_client = _docker_client()
    _check_project_dir(project_root_dir)
    print("Building container...")
    image_tag = _build_container(project_root_dir, container_name)
    print("Starting container...")
    old_version = _get_current_deploy_version(project_root_dir, model_name)
    print("Deployment version {}".format(old_version + 1))
    base_name = _get_docker_name(project_root_dir, model_name)
    new_name = base_name + "-" + str(old_version + 1)
    old_name = base_name + "-" + str(old_version)
    container = _start_container(image_tag, hostname = new_name)
    d_client.api.rename(container.id, new_name)
    print("Copying project to container...")
    _copy_project_to_container(project_root_dir, container, include_data = include_data, include_model = model_name)
    
    file_type = _get_file_type(model_api_file)
    if file_type == 'python':
        cmd = _deploy_flask_model(project_root_dir, model_api_file, container)
    elif file_type == 'r':
        cmd = _deploy_plumber_model(project_root_dir, model_api_file, container)
    else:
        raise NotImplementedError("No deployment option available for file {}".format(model_api_file))

    print("Running command in container: " + cmd)
    container.exec_run(cmd, detach = True)

    rev_proxy = _deploy_reverse_proxy(project_root_dir)
    api_ip_address = d_client.api.inspect_container(container.id)['NetworkSettings']['IPAddress']
    _edit_nginx_entry(project_root_dir, rev_proxy, model_name, new_name, api_ip_address + ':5000', old_hostname=old_name)
    #TODO: add test for making sure new endpoint is up?
    # Kill old container
    old_container = d_client.containers.list(all=True, filters={'name':old_name})
    if len(old_container) > 0:
        old_container[0].stop(timeout = 0)
    return container

def undeploy_single_model(project_root_dir, model_name):
    d_client = _docker_client()
    _check_project_dir(project_root_dir)
    old_version = _get_current_deploy_version(project_root_dir, model_name)
    if old_version == -1:
        print(f"No currently running endpoint for model {model_name}")
        return
    print("Undeploying {} version {}".format(model_name, old_version))
    base_name = _get_docker_name(project_root_dir, model_name)
    old_name = base_name + "-" + str(old_version)
    old_container = d_client.containers.list(all=True, filters={'name':old_name})
    if len(old_container) == 0:
        print(f"No currently running endpoint for model {model_name}")
        return
    old_container.stop(timeout = 0)

def undeploy_all(project_root_dir):
    d_client = _docker_client()
    base_name = _get_docker_name(project_root_dir, '')
    # base_name will be deploy-PROJECTID
    already_running = d_client.containers.list(filters={'name':base_name})
    print("Undeploying all models in project")
    for con in already_running:
        con.stop(timeout=0)

def refresh_data(project_root_dir, container_name, data_refresh_file, dataset_name = None, stop_container = True):
    if dataset_name is None:
        dataset_name = _extract_refresh_data_name(data_refresh_file)

    _check_project_dir(project_root_dir)
    print("Building container...")
    image_tag = _build_container(project_root_dir, container_name)
    print("Starting container...")
    container = _start_container(image_tag)
    try:
        print("Copying project to container...")
        _copy_project_to_container(project_root_dir, container)
        cmd = _get_refresh_data_command(data_refresh_file)
        print("Running command in container: " + cmd)
        result = container.exec_run(cmd)
        if result.exit_code != 0:
            raise RuntimeError("Error while running container command: " + str(result.output))
        print("Copying output back to project")
        
        output_dir = _copy_output_to_project(project_root_dir, container, _build_relative_path(_constants.DATA_PATH, dataset_name))
        print("Run output written to " + output_dir)
    finally:
        if stop_container and container != None:
            print("Stopping container...")
            container.stop(timeout = 0)
        if not stop_container and container != None:
            print("Container still running")
            return container

