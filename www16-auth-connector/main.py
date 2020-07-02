import os
import json
import portalocker
import hmac
import re
from flask import Flask, request, jsonify

AUTH_FILE_NAME = "/share/authorized.json"
DJANGO_API_KEY_ENV_NAME = "DJANGO_API_KEY"

if DJANGO_API_KEY_ENV_NAME not in os.environ:
    print("[ERROR] Please provide an api key!")
    exit(0)

if not os.path.isfile(AUTH_FILE_NAME):
    print("[ERROR] Mount the auth file to the container!")
    exit(0)

DJANGO_API_KEY = os.environ[DJANGO_API_KEY_ENV_NAME]

app = Flask(__name__)

def mutate_auth_db(mutation):
    with portalocker.Lock(AUTH_FILE_NAME, 'r+', timeout=1) as fh:
        data = json.loads(fh.read())
        new_data = json.dumps(mutation(data), ensure_ascii=True)
        fh.seek(0)
        fh.write(new_data)
        fh.truncate()
        fh.flush()
        os.fsync(fh.fileno())

@app.route('/')
def index():
    return "Welcome to the k8s auth microservice!"

@app.route('/authorize', methods=['POST'])
def authorize():
    if request.method == 'POST':
        content = request.json
        if "api_key" not in content or not isinstance(content["api_key"], str):
            return jsonify(error="Please provide an api key")
        if not hmac.compare_digest(content["api_key"], DJANGO_API_KEY):
            return jsonify(error="Invalid API key!")
        if "username" not in content or not isinstance(content["username"], str):
            return jsonify(error="Please provide an username")
        if not re.match(r"^[A-Za-z0-9]{2,64}$", content["username"]):
            return jsonify(error="Invalid username")
        if "password" not in content or not isinstance(content["password"], str):
            return jsonify(error="Please provide an password")
        if not re.match(r"^[A-Za-z0-9]{2,64}$", content["password"]):
            return jsonify(error="Invalid password")

        username = content["username"]
        password = content["password"]
        def mutation(db):
            db[username] = password
            return db
        mutate_auth_db(mutation)
        return jsonify(ok="ok")
    else:
        return jsonify(error="Invalid method")

if __name__ == '__main__':
    app.run(debug=False)
