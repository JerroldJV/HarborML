import pickle

with open('model/py_iris_model/output/iris.pkl', 'rb') as f:
    mdl = pickle.load(f)

def api_predict(data):
    return mdl.predict([data])[0]
