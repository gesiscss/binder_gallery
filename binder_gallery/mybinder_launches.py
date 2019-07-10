from datetime import datetime
from sqlalchemy import func
import pandas as pd
from binder_gallery.models import app, db, BinderLaunch, _strip, Repo


def add_json(frame):
    binder_launches = []
    provider_namespaces = {}
    for i, data in frame.sort_index(ascending=True).iterrows():
        timestamp = data['timestamp'].replace(tzinfo=None)  # TODO test if this is the correct format
        launch = BinderLaunch(schema=data['schema'],
                              version=data['version'],
                              timestamp=timestamp,
                              origin=data.get('origin', 'mybinder.org'),  # TODO version 1 with origin??
                              provider=data['provider'],
                              spec=data['spec'],
                              status=data['status'])
        binder_launches.append(launch)

        # # TODO repos without desc
        provider_spec = launch.provider_spec

        if launch.provider_prefix == 'zenodo':
            # zenodo has no ref info
            provider_namespace = provider_spec
        else:
            provider_spec_parts = provider_spec.split('/')
            # strip ref info from provider_spec_parts
            if launch.provider_prefix in ['gh', 'gl']:
                # gh and gl branches can contain "/"
                provider_spec_parts = provider_spec_parts[:3]
            else:
                # git and gist have ref only as commit SHA
                provider_spec_parts = provider_spec_parts[:-1]
            provider_namespace = _strip('suffix',
                                        "/".join(provider_spec_parts),
                                        ['.git'])
        if provider_namespace in provider_namespaces:
            provider_namespaces[provider_namespace].append(launch)
        else:
            provider_namespaces[provider_namespace] = [launch]
    print(provider_namespaces)
    # TODO try bulk update and bulk save for repos
    for provider_namespace, launches in provider_namespaces.items():
        repo = Repo.query.filter_by(provider_namespace=provider_namespace).first()
        # description = launches[0].get_repo_description()  # TODO uncomment
        description = ""
        if repo:
            repo.launches.append(launches)
            repo.description = description
        else:
            repo = Repo(provider_namespace=provider_namespace, description=description, launches=launches)
            db.session.add(repo)
    # db.session.bulk_insert_mappings(BinderLaunch, binder_launches)
    db.session.bulk_save_objects(binder_launches)
    db.session.commit()


def mybinder_stream():

    with app.app_context():
        last_launch = BinderLaunch.query.filter(BinderLaunch.origin.in_(('gke.mybinder.org', 'ovh.mybinder.org', 'mybinder.org'))).order_by(BinderLaunch.timestamp.desc()).first()  # with_entities(BinderLaunch.timestamp)
        index = pd.read_json("https://archive.analytics.mybinder.org/index.jsonl", lines=True)
        if last_launch:
            left = []
            for i, d in index.sort_index(ascending=True).iterrows():
                if (d['date'].date() >= last_launch.timestamp.date()):
                    left.append(d['name'])
                for n in left:
                    today_count = BinderLaunch.query.filter(
                        BinderLaunch.origin.in_(('gke.mybinder.org', 'ovh.mybinder.org')),
                        func.DATE(BinderLaunch.timestamp) == last_launch.timestamp.date()).count()
                    frame = pd.read_json("https://archive.analytics.mybinder.org/{}".format(n), lines=True)
                    add_json(frame[today_count:])
        else:
            print('in right place')
            for i, data in index.sort_index(ascending=True).iterrows():
                frame = pd.read_json("https://archive.analytics.mybinder.org/{}".format(data['name']), lines=True)
                add_json(frame)


# TODO write a test if we have same launch numbers per day as here https://archive.analytics.mybinder.org/
