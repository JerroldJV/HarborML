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

Now, modify the file "project/containers/default.dockerfile" to include the following contents:
```docker
FROM python
RUN pip install scikit-learn pandas
```
This dockerfile will be used to create a simple container with python and scikit-learn installed.

Next, download the iris dataset (can be found here https://bit.ly/2ow0oJO) and save it in the project/data folder.

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

Now, we've got everything set to use HarborML to run the training script in our container and save the results.

To do so, run the following command on the command line:
```bash
python -m harborml train-model train_iris.py default
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
    ├── containers          
    │   ├── includes
    │   └── default.dockerfile
    ├── data                
    │   └── iris.csv
    ├── model       
    │   └── train_iris
    │       └── output
    │           └── iris.pkl        # this is the pickle file we wrote in the training script
    └── src
        └── train_iris.py

# TODO
Still need deployment default process