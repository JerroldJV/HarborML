import os
import sys
sys.path.insert(0, os.path.abspath('./')) # don't have to build wheel

import pytest
import harborml
import pickle
import shutil
import warnings

#useless warnings filter
@pytest.mark.filterwarnings("ignore:numpy.ufunc size changed")
def test_train():
    if os.path.isdir('./tests/testproject/model'):
        shutil.rmtree('./tests/testproject/model')
    if os.path.isdir('./tests/testproject/tmp'):
        shutil.rmtree('./tests/testproject/tmp')
    testproject_dir = './tests/testproject/'
    harborml.start_project(testproject_dir)
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
    if os.path.isdir('./tests/testproject/model'):
        shutil.rmtree('./tests/testproject/model')
    if os.path.isdir('./tests/testproject/tmp'):
        shutil.rmtree('./tests/testproject/tmp')
