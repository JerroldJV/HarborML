# HarborML
Framework for building, training, and deploying machine learning and AI solutions via containers.

# Dependencies
- Python
- Docker

# Basics/Tutorial
First, you need to install HarborML and create a new project.  Make sure you have python and pip installed.
```bash
# install via pip
pip install git+git://github.com/JerroldJV/HarborML

# navigate to your project directory
cd path/to/my/project

# create a harborml project
python -m harborml start-project

# optional: explicitly provide path to project via --dir argument
# python -m harborml start-project --dir path/to/my/project
```
This will add several folders to your project, so that your project directory looks like this:
    
    project
    ├── containers          # Where dockerfiles will be kept
    │   └── includes        # Put anything needed in dockerfile build context here
    ├── data                # Any static data should be put here
    ├── model               # Trained models will end up here
    └── src                 # All source files (training, scoring, etc) should be put here

Now, we will want to create a new environment and a simple model training script.

Now, create a new file "project/containers/default.dockerfile" with the following contents:
```docker
FROM python
RUN pip install scikit-learn pandas
```
This dockerfile will be used to create a simple container with python and scikit-learn installed.

Next, download the iris dataset (can be found here https://gist.githubusercontent.com/curran/a08a1080b88344b0c8a7/raw/d546eaee765268bf2f487608c537c05e22e4b221/iris.csv) and save it in the project/data folder.

Finally, create a file "project/src/train_iris.py" in the src with the following contents:
```python
import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier

# Load data
iris = pd.read_csv('data/iris.csv')
# Train random forest model
clf = RandomForestClassifier()
X = iris[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]
y = iris['species']
clf.fit(X, y)
# Save trained model to output folder
import pickle
with open('output/iris.pkl', 'wb') as f:
    pickle.dump(clf, f)
```

Our project should now look like this:
    
    project
    ├── containers          
    │   ├── includes
    │   └── default.dockerfile
    ├── data                
    │   └── iris.csv
    ├── model             
    └── src
        └── train_iris.py

Now, we've got everything set to use HarborML to the the training script in our container and save the results.  Our project should 

To do so, run the following command on the command line:
```bash
python -m harborml train-model --model_name iris_model train_iris.py default
```
You should see the following output:
```
Building container...
Starting container...
Copying project to container...
Running command in container: bash -c  "cd \"/var/harborml\" && python \"train_iris.py\""
Copying output back to project
Run output written to .\tests\testproject\/model/train_iris
Stopping container...
```
And finally, there should be a new folder project/model containing our trained model!

    project
    ├── ...
    ├── model       
    │   └── iris_model
    │       └── output
    │           └── iris.pkl        # this is the pickle file we wrote in the training script
    └── ...

Next, we will want to deploy the model via a REST API.  To do so, we need to write a function to "score" new data.

In the "src" folder, create a new file "deploy_iris.py" with the following contents:
```python
import pickle

# Load our model
with open('model/iris_model/output/iris.pkl', 'rb') as f:
    mdl = pickle.load(f)

# Receive data and return the scored result
def predict(data):
    return mdl.predict([data])[0]
```

    project
    ├── ...
    └── src
        ├── deploy_iris.py      # this is our new file
        └── train_iris.py


Now we have everything we need to deploy a model as a REST API - HarborML takes care of the rest.  As long as there is a python file with a "predict" function inside HarborML can deploy it!  To deploy it, run the following command:

```bash
python -m harborml deploy-model --model_name iris_model deploy_iris.py default
```

Now we have our model available as a REST API locally.  To quickly test the API, navigate to http://localhost:5000/debug .  In the text area, enter in [0.0, 0.0, 0.0, 0.0], and press "Test".  You should see "setosa" appear.  What just happened is that HarborML deployed your model in a Flask API on your local machine on port 5000.  HarborML then provided an easy to use "debug" link that allowed you to test your API in the web browser.  The data you entered in was converted to JSON, passed to the Flask API, decoded into a python object, and passed to the "predict" function in deploy_iris.py.  The results were then coded into JSON and returned to your web browser!

If you want to test programatically accessing the API, here is some example code you can run after to API is running:

```python
import requests
import json
r = requests.post('http://localhost:5000', json=[0.0, 0.0, 0.0, 0.0])
print(r.text)
```

After you are done with the API, make sure to shut down your container.

```bash
# get the container ID
docker ps

# shut down the container
docker stop [CONTAINER_ID]
```