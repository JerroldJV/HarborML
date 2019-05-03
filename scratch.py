import harborml

harborml.start_project('./tests/testproject')
harborml.deploy_model(
    './tests/testproject', 
    'default', 
    'deploy_iris.py', 
    'iris_model', 
    include_data = False)
    