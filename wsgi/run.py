from flask import Flask, render_template, request, url_for, redirect
import ext
import scraper
import db
import filters

app = Flask(__name__)
filters.register(app)


@app.route("/", methods=['GET'])
def index():
    return render_template('load.html')


@app.route('/', methods=['POST'])
def upload():
    f = request.files['cards_list']
    if f:
        token = ext.get_token()

        try:
            content = ext.read_file(f.stream)
            parser = scraper.MagiccardsScraper()

            cards = parser.process_cards(content)
        except:
            return redirect(url_for('error'))
        else:
            db.save_cards(token, cards)

            if len([c for c in cards if not c.has_info or not c.has_prices]) > 0:
                return redirect(url_for('stats', token=token))

            return redirect(url_for('cards', token=token, repr='l'))

    return render_template('load.html', has_error=True)


@app.route('/<repr>/<token>', methods=['GET'])
def cards(token=None, repr='l'):
    cards = filter(lambda c: c.has_info and c.has_prices, db.get_cards(token))
    sort = request.args.get('sort', 'name')
    order = request.args.get('order', 'asc')
    key_for_sort = lambda c: c.name if sort == 'name' else filters.price(c, 'low')

    templ_data = {'token': token, 'cards': sorted(cards, key=key_for_sort, reverse=order == 'desc'),
                  'repr': repr, 'sort': sort, 'order': order}

    if repr == 'l':
        return render_template('cards_list.html', **templ_data)
    elif repr == 't':
        return render_template('cards_table.html', **templ_data)
    else:
        return render_template('error.html')


@app.route('/s/<token>', methods=['GET'])
def stats(token=None):
    return token


@app.route('/err')
def error():
    return render_template('error.html')


if __name__ == "__main__":
    app.run(debug="True")