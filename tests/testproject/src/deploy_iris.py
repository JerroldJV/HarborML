import pickle

with open('model/iris_model/output/iris.pkl', 'rb') as f:
    mdl = pickle.load(f)

def api_predict(data):
    return mdl.predict([data])[0]
