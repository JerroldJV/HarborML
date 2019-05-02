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
@click.option('--model_name', default='', help='Directory of the project')
def train_model(train_model_file, container, dir, model_name):
    """Trains a model, and saves the results written to the "output" folder in the "model" folder

    TRAIN_MODEL_FILE: Name/path of file in src folder that will train a model and save the results to the "output" folder

    CONTAINER: Name of the container that the training script will run in
    """
    if model_name == '': 
        model_name = None
    _core.train_model(dir, container, train_model_file, model_name = model_name)

cli.add_command(train_model)

if __name__ == '__main__':
    cli()