FROM python:3.7.3-stretch

LABEL maintainer="notebooks@gesis.org"

RUN apt-get update -y && \
    apt-get install -yq \
    vim \
    htop \
    less && \
    apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# upgrade pip
RUN pip install --no-cache-dir --upgrade pip

# We copy just the requirements.txt first to leverage Docker cache
COPY requirements.txt /requirements.txt

RUN pip install --no-cache-dir -r /requirements.txt

COPY . /binder_gallery

WORKDIR /binder_gallery

ENV PYTHONUNBUFFERED=1

# tell the port number the container should expose
EXPOSE 5000

# run the application
CMD ["python", "-m", "binder_gallery"]
# run the application behind Gunicorn WSGI HTTP Server
#CMD ["gunicorn", "-b", "0.0.0.0:5000", "binder_gallery:app"]
# run the application behind Gunicorn WSGI HTTP Server with 4 worker processes
#CMD ["gunicorn", "-b", "0.0.0.0:5000", "-w", "4", "binder_gallery:app"]
