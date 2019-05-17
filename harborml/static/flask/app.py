from flask import Flask, jsonify, request
app = Flask(__name__)

from loader import model #pylint: disable=no-name-in-module
import json

@app.route('/', methods = ['POST'])
def predict():
    return jsonify(model.api_predict(request.get_json(force=True)))

@app.route('/debug', methods = ['GET'])
def debug():
    return """
    <html>
    <body>
    <form action='' method='post'>
        <textarea name="jsondata" cols="100" rows="20"></textarea><br/>
        <button>Test</button>
    </form>
    </body>
    </html>
    """

@app.route('/debug', methods = ['POST'])
def debug_post():
    return jsonify(model.api_predict(json.loads(request.form['jsondata'])))
