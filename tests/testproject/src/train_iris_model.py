import pandas as pd
import sklearn
from sklearn.ensemble import RandomForestClassifier

iris = pd.read_csv('data/iris/iris.csv')
clf = RandomForestClassifier()

X = iris[['sepal_length', 'sepal_width', 'petal_length', 'petal_width']]
y = iris['species']
clf.fit(X, y)

import pickle
with open('output/iris.pkl', 'wb') as f:
    pickle.dump(clf, f)
