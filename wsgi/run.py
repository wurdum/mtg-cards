from flask import Flask, render_template, request, url_for, redirect
import ext
import scrapers
import db
import filters

app = Flask(__name__)
filters.register(app)


@app.route("/", methods=['GET'])
def index():
    # lists = db.get_last_cards_lists()
    lists = []
    return render_template('upload.html', cards_lists=lists)


@app.route('/', methods=['POST'])
def upload():
    f = request.files['cards_list']
    list_type = ext.result_or_default(lambda: request.form['list_type'], default='public', prevent_empty=True)
    if f:
        content = ext.read_file(f.stream)
        cards = scrapers.resolve_cards_async(content)
        cards = ext.merge_pups(cards)

        token = db.get_unique_token()
        db.save_cards(token, list_type, cards)

        if len(filter(lambda c: not c.is_resolved, cards)) > 0:
            return redirect(url_for('stats', token=token))

        return redirect(url_for('cards', token=token, repr='l'))

    return render_template('upload.html', has_error=True)


@app.route('/<token>/l', defaults={'repr': 'l'}, methods=['GET'])
@app.route('/<token>/<repr>', methods=['GET'])
def cards(token, repr):
    cards = db.get_cards(token, only_resolved=True)
    sort = ext.result_or_default(lambda: request.args['sort'], default='name', prevent_empty=True)
    order = ext.result_or_default(lambda: request.args['order'], default='asc', prevent_empty=True)

    key_for_sort = lambda c: c.name if sort == 'name' else c.get_avg_prices()['low']
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


@app.route('/<token>/shop/tcg', methods=['GET'])
def tcg(token):
    cards = db.get_cards(token, only_resolved=True)
    sellers = scrapers.get_tcg_sellers_async(cards)

    sellers_av = filter(lambda s: s.has_all_cards(cards), sellers)
    sellers_av = sorted(sellers_av, key=lambda s: s.cards_cost)
    sellers_al = sorted(sellers, key=lambda s: s.available_cards_num, reverse=True)

    return render_template('cards_tcg_sellers.html', token=token, cards=cards,
                           sellers_groups={'av': sellers_av[:10], 'al': sellers_al[:30]})


@app.route('/<token>/shop/bm', methods=['GET'])
def bm(token):
    cards = db.get_cards(token, only_resolved=True)
    offers = scrapers.get_buymagic_offers_async(cards)

    return render_template('cards_bm_offers.html', token=token, cards=cards, offers=offers)


@app.route('/<token>/shop/ss', methods=['GET'])
def ss(token):
    cards = db.get_cards(token, only_resolved=True)
    offers = scrapers.get_spellshop_offers_async(cards)

    return render_template('cards_ss_offers.html', token=token, cards=cards, offers=offers)


@app.route('/privateclists', methods=['GET'])
def pcl():
    return render_template('cards_private_lists.html',
                           cards_lists=db.get_last_cards_lists(show_private=True, lists_number=100))


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