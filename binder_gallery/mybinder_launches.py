from datetime import datetime
from sqlalchemy import func
import pandas as pd
from binder_gallery.models import app, db, BinderLaunch, _strip, Repo


def mybinder_stream():

    with app.app_context():
        last_launch = BinderLaunch.query.filter(BinderLaunch.origin.in_(('gke.mybinder.org', 'ovh.mybinder.org'))).order_by(BinderLaunch.timestamp.desc()).first()  # with_entities(BinderLaunch.timestamp)
        print(last_launch)
        index = pd.read_json("https://archive.analytics.mybinder.org/index.jsonl", lines=True)
        for _, day in index.sort_index(ascending=True).iterrows():
            if last_launch and last_launch.timestamp.date > day.date:
                print('skipped', day.date)
                continue
            print(day.date)
            # continue

            if not last_launch:
                today_count = 0
            else:
                # FIXME
                today_count = BinderLaunch.query.filter(
                    BinderLaunch.origin.in_(('gke.mybinder.org', 'ovh.mybinder.org')),
                    func.DATE(BinderLaunch.timestamp) == last_launch.timestamp.date()).count()
                print(today_count)
            binder_launches = []
            provider_namespaces = {}
            for i, data in pd.read_json("https://archive.analytics.mybinder.org/{}".format(day['name']), lines=True).iterrows():
                if today_count > i:
                    continue

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
            break  # TODO renove this line


# TODO write a test if we have same launch numbers per day as here https://archive.analytics.mybinder.org/
