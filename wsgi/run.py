import random
import string
import os
from flask import Flask, url_for, redirect
from flask import render_template
from flask import request
from werkzeug.utils import secure_filename

app = Flask(__name__)


def get_token(size=6, chars=string.ascii_lowercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))

@app.route("/", methods=['GET'])
def index():
    return render_template('load.html')


@app.route('/', methods=['POST'])
def upload():
    f = request.files['cards_list']
    if f:
        # content = f.stream.getvalue()
        token = get_token()

        return redirect(url_for('cards', token=token))

    return render_template('load.html', has_error=True)


@app.route('/l/<token>', methods=['GET'])
def cards(token=None):
    return token


if __name__ == "__main__":
    app.run(debug="True")
