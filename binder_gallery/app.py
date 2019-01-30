import os
from flask import Flask, render_template, abort, request, url_for
from .popular_repos import get_launch_data, process_launch_data, get_popular_repos
from .utilities import get_created_by_gesis
from copy import deepcopy
from .models import db
from flask_admin import Admin
from flask_admin.contrib.sqla import ModelView
from .models import CreatedByGesis, User
from flask_login import LoginManager, login_required, login_user
from .forms import LoginForm

# app = Flask(__name__, template_folder='../templates/orc_site')
app = Flask(__name__)
staging = os.environ.get('DEPLOYMENT_ENV') == 'staging'
production = os.environ.get('DEPLOYMENT_ENV') == 'production'
site_url = 'https://notebooks{}.gesis.org'.format('-test' if staging else '')

# set optional bootswatch theme
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
admin = Admin(app, name='binder_gallery', template_mode='bootstrap3')


@login_required
def admin_view():
    admin.add_view(ModelView(CreatedByGesis, db.session))


app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['BG_DATABASE_URL']
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    # Here we use a class of some kind to represent and validate our
    # client-side form data. For example, WTForms is a library that will
    # handle this for us, and we use a custom LoginForm to validate.
    form = LoginForm()
    if form.validate_on_submit():
        # Login and validate the user.
        # user should be an instance of your `User` class
        login_user(User)

        Flask.flash('Logged in successfully.')

        next = Flask.request.args.get('next')
        # is_safe_url should check if the url is safe for redirects.
        # See http://flask.pocoo.org/snippets/62/ for an example.
        if not is_safe_url(next):
            return Flask.abort(400)

        return Flask.redirect(next or Flask.url_for('index'))
    return Flask.render_template('login.html', form=form)

# set optional bootswatch theme
app.config['FLASK_ADMIN_SWATCH'] = 'cerulean'
admin = Admin(app, template_mode='bootstrap3')
admin.add_view(ModelView(CreatedByGesis, db.session))

context = {
    'staging': staging,
    'production': production,
    'version': 'beta',
    # 'shibboleth_entityID': f'{site_url}/shibboleth',

    'gallery_url': '/',
    'jhub_url': '/jupyter/',
    'gesis_login_url': f'{site_url}/Shibboleth.sso/Login?SAMLDS=1&'
                       f'target={site_url}/hub/login&'
                       f'entityID=https%3A%2F%2Fidp.gesis.org%2Fidp%2Fshibboleth',
    'about_url': '/about/',
    'tou_url': '/terms_of_use/',
    'imprint_url': 'https://www.gesis.org/en/institute/imprint/',
    'data_protection_url': 'https://www.gesis.org/en/institute/data-protection/',
    'gesis_url': 'https://www.gesis.org/en/home/',
    # 'help_url': 'https://www.gesis.org/en/help/',
}


@app.route('/')
def gallery():
    # get all launch count data (in last 90 days)
    launch_data = get_launch_data()
    launch_data = process_launch_data(launch_data)

    popular_repos_all = [
        (1, 'Last 24 hours', get_popular_repos(deepcopy(launch_data), '24h'), '24h', ),
        (2, 'Last week', get_popular_repos(deepcopy(launch_data), '7d'), '7d', ),
        (3, 'Last 30 days', get_popular_repos(deepcopy(launch_data), '30d'), '30d', ),
        (4, 'Last 60 days', get_popular_repos(deepcopy(launch_data), '60d'), '60d', ),
    ]

    created_by_gesis = get_created_by_gesis()

    context.update({'active': 'gallery',
                    'popular_repos_all': popular_repos_all,
                    'created_by_gesis': created_by_gesis,
                    })
    return render_template('gallery.html', **context)


@app.route('/popular_repos/<string:time_range>')
def popular_repos(time_range):
    titles = {'24h': 'Popular repositories in last 24 hours',
              '7d': 'Popular repositories in last week',
              '30d': 'Popular repositories in last 30 days',
              '60d': 'Popular repositories in last 60 days'}
    if time_range not in titles:
        abort(404)
    # get all launch count data (in last 90 days)
    launch_data = get_launch_data()
    launch_data = process_launch_data(launch_data)
    context.update({'active': 'gallery',
                    'title': titles[time_range],
                    'popular_repos': get_popular_repos(launch_data, time_range)})
    return render_template('popular_repos.html', **context)


@app.errorhandler(404)
def not_found(error):
    context.update({'status_code': error.code,
                    'status_message': error.name,
                    'message': error.description,
                    'active': None})
    return render_template('error.html', **context), 404


def run_app():
    app.run(debug=False, host='0.0.0.0')


main = run_app

if __name__ == '__main__':
    main()

