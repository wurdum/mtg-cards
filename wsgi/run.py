from flask import Flask, render_template, request, url_for, redirect
import ext
import scraper
import db
import filters

app = Flask(__name__)
filters.register(app)


@app.route("/", methods=['GET'])
def index():
    return render_template('upload.html', cards_lists=db.get_last_cards_lists())


@app.route('/', methods=['POST'])
def upload():
    f = request.files['cards_list']
    if f:
        token = db.get_unique_token()

        try:
            content = ext.read_file(f.stream)
            cards = scraper.resolve_cards_async(content)
        except:
            return redirect(url_for('error'))
        else:
            db.save_cards(token, cards)

            if len([c for c in cards if not c.has_info or not c.has_prices]) > 0:
                return redirect(url_for('stats', token=token))

            return redirect(url_for('cards', token=token, repr='l'))

    return render_template('upload.html', has_error=True)


@app.route('/<token>/l', defaults={'repr': 'l'}, methods=['GET'])
@app.route('/<token>/<repr>', methods=['GET'])
def cards(token, repr):
    cards = db.get_cards(token, only_resolved=True)
    sort = ext.result_or_default(lambda: request.args['sort'], default='name', prevent_empty=True)
    order = ext.result_or_default(lambda: request.args['order'], default='asc', prevent_empty=True)

    key_for_sort = lambda c: c.name if sort == 'name' else filters.price(c, 'low')
    templ_data = {'token': token, 'cards': sorted(cards, key=key_for_sort, reverse=order == 'desc'),
                  'repr': repr, 'sort': sort, 'order': order}

    if repr == 'l':
        return render_template('cards_list.html', **templ_data)
    elif repr == 't':
        return render_template('cards_table.html', **templ_data)
    else:
        return render_template('error.html')


@app.route('/<token>/s', methods=['GET'])
def stats(token):
    cards = db.get_cards(token)
    return render_template('upload_stats.html', token=token, cards=cards)

@app.route('/<token>/shop/tcg/av', defaults={'list_type': 'av'}, methods=['GET'])
@app.route('/<token>/shop/tcg/<list_type>', methods=['GET'])
def tcg(token, list_type):
    if list_type not in ['av', 'al']:
        list_type = 'av'

    cards = db.get_cards(token, only_resolved=True)
    sellers = scraper.get_tcg_sellers_async(cards)

    if list_type == 'av':
        sellers = filter(lambda s: s.has_all_cards(cards), sellers)
        sellers = sorted(sellers, key=lambda s: s.calculate_cards_cost(cards))
    else:
        sellers = sorted(sellers, key=lambda s: s.get_available_cards_num(cards), reverse=True)

    return render_template('cards_ggc_sellers.html', token=token, cards=cards, sellers=sellers, list_type=list_type)


@app.route('/delete', methods=['POST'])
def delete():
    if 'token' in request.form:
        token = request.form['token']
        db.delete_cards(token)

    return redirect(url_for('index'))


@app.route('/err')
@app.errorhandler(403)
@app.errorhandler(404)
@app.errorhandler(410)
@app.errorhandler(500)
def error(e=None):
    return render_template('error.html')


if __name__ == "__main__":
    app.run(debug="True")