import json
import pandas as pd
import urllib.request
from .models import BinderLaunch
from . import db


def mybinder_stream():
    objects = BinderLaunch.query.filter(BinderLaunch.origin.in_(('gke.mybinder.org', 'ovh.mybinder.org'))).all()
    if not objects:
        index = pd.read_json("https://archive.analytics.mybinder.org/index.jsonl", lines=True)
        json_obj = []
        for idx, day in index.sort_index(ascending=False).iterrows():
            json_data = urllib.request.urlopen("https://archive.analytics.mybinder.org/{}".format(day['name']))
            json_obj.extend(json_data.readlines())
        binder_launches = []
        for i in range(0, len(json_obj)):
            binder_launches.append(json.loads(json_obj[i].decode()))
            if len(binder_launches) % 10000 == 0:
                db.session.bulk_insert_mappings(BinderLaunch, binder_launches)
                db.session.commit()
                binder_launches = []
        db.session.bulk_insert_mappings(BinderLaunch, binder_launches)
        db.session.commit()
    return ""

