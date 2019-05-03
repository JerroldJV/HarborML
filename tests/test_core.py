import os
import sys
sys.path.insert(0, os.path.abspath('./')) # don't have to build wheel

import pytest
import harborml
import pickle
import sklearn  # need sklearn installed to test model results
import shutil
import warnings

testproject_dir = './tests/testproject/'

def setup_module(module):
    if os.path.isdir('./tests/testproject/model'):
        shutil.rmtree('./tests/testproject/model')
    if os.path.isdir('./tests/testproject/tmp'):
        shutil.rmtree('./tests/testproject/tmp')

    harborml.start_project(testproject_dir)

def teardown_module(module):
    if os.path.isdir('./tests/testproject/model'):
        shutil.rmtree('./tests/testproject/model')
    if os.path.isdir('./tests/testproject/tmp'):
        shutil.rmtree('./tests/testproject/tmp')

def test_build():
    harborml.build_container(testproject_dir, 'default')

#useless warnings filter
@pytest.mark.filterwarnings("ignore:numpy.ufunc size changed")
def test_train_and_deploy():
    harborml.train_model(
        testproject_dir,
        'default',
        'train_iris.py',
        'iris_model'
    )
    with open(testproject_dir + 'model/iris_model/output/iris.pkl', 'rb') as f:
        model = pickle.load(f)
    assert model.predict([[0.0, 0.0, 0.0, 0.0]])[0] == 'setosa'
    assert model.predict([[10.0, 10.0, 10.0, 10.0]])[0] == 'virginica'
    container = None
    try:
        container = harborml.deploy_model(
            './tests/testproject', 
            'default', 
            'deploy_iris.py', 
            'iris_model', 
            include_data = False)

        import requests
        import time
        time.sleep(3) # have to wait for flask to spin up
        import json
        r = requests.post('http://localhost:5000', json=[0.0, 0.0, 0.0, 0.0])
        assert json.loads(r.text) == 'setosa'
        r = requests.post('http://localhost:5000', json=[10.0, 10.0, 10.0, 10.0])
        assert json.loads(r.text) == 'virginica'
    finally:
        if container is not None:
            container.stop()

