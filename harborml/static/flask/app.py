from flask import Flask, jsonify, request
app = Flask(__name__)

from loader import model #pylint: disable=no-name-in-module

@app.route('/', methods = ['POST'])
def predict():
    #return "HELP ME"
    return jsonify(model.predict(request.get_json(force=True)))

@app.route('/debug')
def debug():
    return 'Hello!'