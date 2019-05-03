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

## To have custom configuration

1. Create a config file `local_config.py` under project folder `binder_gallery`

2. Put your custom configuration:

```python
from config import Config as BaseConfig


class Config(BaseConfig):
    # add your custom configuration here
```

3. `export BG_APPLICATION_SETTINGS=local_config.Config`

## Run gallery in docker

```bash
cd binder_gallery

# build
docker build -t binder-gallery:test .

# run with default config
docker run --name binder-gallery -it --rm \
    -p 5000:5000 \
    --env FLASK_ENV=production \
    binder-gallery:test

# run with custom config (you have to create a `docker_config.py` which includes your config)
# and also run with base url (`/gallery/`)
docker run --name binder-gallery -it --rm \
    -p 5000:5000 \
    --env FLASK_ENV=production \
    --env BG_BASE_URL=/gallery/ \
    --env BG_APPLICATION_SETTINGS=docker_config.Config \
    -v $(pwd)/docker_config.py:/binder_gallery/docker_config.py \
    binder-gallery:test
```

## TODOs

1. Remove GESIS related parts (templates, static files...)?
