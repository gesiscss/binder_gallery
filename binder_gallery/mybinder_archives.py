import pandas as pd

from time import sleep
from datetime import datetime
from sqlalchemy import func

from .models import app, db, Repo, BinderLaunch


def save_launches(new_launches):
    provider_namespaces = {}
    for i, data in new_launches.sort_index(ascending=True).iterrows():
        origin = data.get('origin', 'mybinder.org')
        if origin == "notebooks.gesis.org" or origin == "notebooks-test.gesis.org":
            continue
        timestamp = data['timestamp'].replace(tzinfo=None)
        launch = BinderLaunch(schema=data['schema'],
                              version=data['version'],
                              timestamp=timestamp,
                              # NOTE: launches of version 1 and 2 from mybinder.org have origin as 'mybinder.org'
                              # even it actually does not exist in archives
                              origin=origin,
                              provider=data['provider'],
                              spec=data['spec'],
                              status=data['status'])

        # binder_launches.append(launch)
        provider_namespace = launch.provider_namespace
        if provider_namespace in provider_namespaces:
            provider_namespaces[provider_namespace].append(launch)
        else:
            provider_namespaces[provider_namespace] = [launch]

    for provider_namespace, launches in provider_namespaces.items():
        repo = Repo.query.filter_by(provider_namespace=provider_namespace).first()
        # description = launches[0].get_repo_description()
        description = ""
        if repo:
            repo.launches.extend(launches)
            # repo.description = description
        else:
            repo = Repo(provider_namespace=provider_namespace, description=description, launches=launches)
            db.session.add(repo)
        for launch in launches:
            db.session.add(launch)
    db.session.commit()


def parse_mybinder_archives(binder, all_events=False):
    app.logger.info(f"parse_mybinder_archives: started at {datetime.utcnow()} [UTC]")
    with app.app_context():
        origins = app.binder_origins[binder]['origins']
        if all_events is True:
            last_launch_date = datetime(2000, 1, 1).date()
        else:
            # get last saved mybinder launch
            # parse archives after date of last launch
            last_launch = BinderLaunch.query.\
                          filter(BinderLaunch.origin.in_(origins)).\
                          order_by(BinderLaunch.timestamp.desc()).first()  # with_entities(BinderLaunch.timestamp)
            last_launch_date = last_launch.timestamp.date()

        # get new or unfinished archives to parse
        index = pd.read_json("https://archive.analytics.mybinder.org/index.jsonl", lines=True)
        archives = []
        for i, d in index.sort_index(ascending=True).iterrows():
            if d['date'].date() >= last_launch_date:

                archives.append([d['name'], d['date'].date(), d['count']])

        total_count = 0
        total_a_count = 0
        for a_name, a_date, a_count in archives:
            if a_date == last_launch_date:
                today_count = BinderLaunch.query.\
                              filter(BinderLaunch.origin.in_(origins),
                                     func.DATE(BinderLaunch.timestamp) == last_launch_date).\
                              count()
            else:
                # parse all launches of this archive
                today_count = 0
            total_a_count = total_a_count + a_count - today_count
            app.logger.info(f"parse_mybinder_archives: "
                            f"parse after {today_count} launches of {a_name} - {a_date}")

            frame = pd.read_json(f"https://archive.analytics.mybinder.org/{a_name}", lines=True)
            new_launches = frame[today_count:]
            new_launches_count = len(new_launches)
            save_launches(new_launches)
            # app.logger.info(f"parse_mybinder_archives: done: for {a_name} - {a_date}")
            app.logger.info(f"parse_mybinder_archives: done: "
                            f"{new_launches_count} new launches saved for {a_name} - {a_date}")
            total_count += new_launches_count
            sleep(30)

    app.logger.info(f"parse_mybinder_archives: done at {datetime.utcnow()} [UTC]:"
                    f" {total_count}:{total_a_count} new launches saved")
    # assert total_a_count == total_count
