import os
from flask import Flask
from flask import render_template
from flask import request

app = Flask(__name__)

#Create our index or root / route
@app.route("/")
@app.route("/index")
def index():
    return render_template('load.html')


if __name__ == "__main__":
    app.run(debug="True")
