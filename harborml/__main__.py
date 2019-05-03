import click
from . import core as _core

@click.group()
def cli():
    pass

@click.command()
@click.option('--dir', default='./', help='Directory of the project')
def start_project(dir):
    """Starts a new project"""
    _core.start_project(dir)

cli.add_command(start_project)

@click.command()
@click.argument('container')
@click.option('--dir', default='./', help='Directory of the project')
def build_container(container, dir):
    """Builds a container

    CONTAINER: Name of the container that the training script will run in
    """
    return _core.build_container(dir, container)

cli.add_command(build_container)

@click.command()
@click.argument('train_model_file')
@click.argument('container')
@click.option('--dir', default='./', help='Directory of the project')
@click.option('--model_name', default='', help='Name of the model')
def train_model(train_model_file, container, dir, model_name):
    """Trains a model, and saves the results written to the "output" folder in the "model" folder

    TRAIN_MODEL_FILE: Name/path of file in src folder that will train a model and save the results to the "output" folder

    CONTAINER: Name of the container that the training script will run in
    """
    if model_name == '': 
        model_name = None
    _core.train_model(dir, container, train_model_file, model_name = model_name)

cli.add_command(train_model)

@click.command()
@click.argument('model_scorer')
@click.argument('container')
@click.option('--dir', default='./', help='Directory of the project')
@click.option('--model_name', default='', help='Name of the model')
@click.option('--include_data', default='0', help='Whether the data directory should be copied to the container')
def deploy_model(model_scorer, container, dir, model_name, include_data):
    """Deploys a model in a docker container.

    MODEL_SCORER: File in source that has a "predict" function that takes data and returns a prediction

    CONTAINER: Name of the container that the training script will run in
    """
    _core.deploy_model(dir, container, model_scorer, model_name, include_data = include_data)

cli.add_command(deploy_model)

if __name__ == '__main__':
    cli()