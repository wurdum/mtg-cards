from flask import Flask, render_template, request, url_for, redirect
import ext
import scraper
import db

app = Flask(__name__)

@app.route("/", methods=['GET'])
def index():
    return render_template('load.html')


@app.route('/', methods=['POST'])
def upload():
    f = request.files['cards_list']
    if f:
        token = ext.get_token()

        cards = []
        try:
            content = ext.read_file(f.stream)
            parser = scraper.MagiccardsScraper()

            cards = parser.process_cards(content)
        except Exception, ex:
            return redirect(url_for('error'))
        else:
            db.save_cards(token, cards)

            if len([c for c in cards if not c.is_resolved]) > 0:
                return redirect(url_for('stats', token=token))

            return redirect(url_for('cards', token=token))

    return render_template('load.html', has_error=True)


@app.route('/l/<token>', methods=['GET'])
def cards(token=None):
    return token


@app.route('/s/<token>', method=['GET'])
def stats(token=None):
    return token

@app.route('/err')
def error():
    return render_template('error.html')

if __name__ == "__main__":
    app.run(debug="True")
