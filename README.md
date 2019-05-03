# Binder Gallery

Binder Gallery for [GESIS Notebooks](https://notebooks.gesis.org/)

## Run the gallery locally

1. Clone the repository and get into it
    ```bash
    git clone https://github.com/gesiscss/binder_gallery.git
    cd binder_gallery
    ```

2. [Create and activate a virtual environment](http://flask.pocoo.org/docs/1.0/installation/#virtual-environments)
with python version at least 3.7.

3. Install dependencies: 
    ```bash
    pip install -r dev_requirements.txt
    ```
    
4. Set required environment variables
    ```bash
    export FLASK_APP=binder_gallery
    export FLASK_ENV=development
    ```

5. Create a local sqlite3 db and apply migrations
    ```bash
    python manage.py db upgrade
    ```

6. Run the application
    ```bash
    flask run
    ```
### Create user

1. With `create-user` command:

    ```bash
    flask create-user <name> <password>
    ```

2. With flask shell:

    2.1 Start a flask shell

    ```bash
    flask shell
    ```

    2.2 Run this code to create a user:

    ```python
    from binder_gallery.models import User
    User.create_user("name", "password")
    ```

## To have custom configuration

1. Create a config file `local_config.py` under project folder `binder_gallery`

2. Put your custom configuration:

```python
from config import Config as BaseConfig


class Config(BaseConfig):
    # add your custom configuration here
```

3. `export BG_APPLICATION_SETTINGS=local_config.Config`

## TODOs

1. Remove GESIS related parts (templates, static files...)?
