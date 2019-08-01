import pandas as pd

from time import sleep
from datetime import datetime, timedelta
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


def parse_mybinder_archives(binder='mybinder', all_events=False):
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
            if d['date'].date() >= last_launch_date-timedelta(days=1):
                # make sure also that everything of previous day is saved
                archives.append([d['name'], d['date'].date(), d['count']])

        total_count = 0
        for a_name, a_date, a_count in archives:
            a_count_saved = BinderLaunch.query.\
                            filter(BinderLaunch.origin.in_(origins),
                                   func.DATE(BinderLaunch.timestamp) == a_date).\
                            count()
            if a_count_saved > a_count:
                app.logger.error(f"parse_mybinder_archives: "
                                 f"Error saved ({a_count_saved}) > in archive ({a_count}) for {a_name} - {a_date}")
                continue
            elif a_count_saved == a_count:
                app.logger.info(f"parse_mybinder_archives: "
                                f"everything is already saved {a_count} - {a_count_saved} = {a_count-a_count_saved} "
                                f"launches of {a_name} - {a_date}")
                continue
            app.logger.info(f"parse_mybinder_archives: "
                            f"parsing {a_count} - {a_count_saved} = {a_count-a_count_saved} "
                            f"launches of {a_name} - {a_date}")

            frame = pd.read_json(f"https://archive.analytics.mybinder.org/{a_name}", lines=True)
            new_launches = frame[a_count_saved:]
            new_launches_count = len(new_launches)
            assert new_launches_count == a_count-a_count_saved
            save_launches(new_launches)
            app.logger.info(f"parse_mybinder_archives: "
                            f"saved {new_launches_count} new launches for {a_name} - {a_date}")
            total_count += new_launches_count
            sleep(30)

    app.logger.info(f"parse_mybinder_archives: done at {datetime.utcnow()} [UTC]: "
                    f"total {total_count} new launches saved")
