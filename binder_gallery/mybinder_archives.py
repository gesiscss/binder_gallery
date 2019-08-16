import pandas as pd

from time import sleep
from datetime import datetime, timedelta, date
from sqlalchemy import func

from .models import app, db, Repo, BinderLaunch


def save_launches(new_launches, with_description):
    provider_namespaces = {}
    for i, data in new_launches.sort_index(ascending=True).iterrows():
        origin = data.get('origin', 'mybinder.org')
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
        description = launches[0].get_repo_description() if with_description else ""
        if launches[-1].provider_prefix == "zenodo":
            last_ref = ""
        else:
            last_ref = launches[-1].spec.split('/')[-1]

        if repo:
            repo.launches.extend(launches)
            if with_description:
                repo.description = description
            repo.last_ref = last_ref
        else:
            repo = Repo(provider_namespace=provider_namespace, description=description,
                        launches=launches, last_ref=last_ref)
            db.session.add(repo)
        for launch in launches:
            db.session.add(launch)
    db.session.commit()


def parse_mybinder_archives(binder='mybinder', all_events=False, with_description=False):
    app.logger.info(f"parse_mybinder_archives: started at {datetime.utcnow()} [UTC]")
    with app.app_context():
        origins = app.binder_origins[binder]['origins']
        if all_events is True:
            last_launch_timestamp = None
            last_launch_date = date(2000, 1, 1)
        else:
            # get last saved mybinder launch
            # parse archives after date of last launch
            last_launch = BinderLaunch.query.\
                          filter(BinderLaunch.origin.in_(origins)).\
                          order_by(BinderLaunch.timestamp.desc()).first()  # with_entities(BinderLaunch.timestamp)
            last_launch_timestamp = last_launch.timestamp
            last_launch_date = last_launch_timestamp.date()

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

            _frame = pd.read_json(f"https://archive.analytics.mybinder.org/{a_name}", lines=True)
            # events-2019-06-12.jsonl has mixed rows: with and without origin value
            if a_name == "events-2019-06-12.jsonl":
                _frame['origin'].fillna('mybinder.org', inplace=True)
            # in some archives Gist launches have wrong provider (GitHub)
            elif a_name == "events-2018-11-25.jsonl":
                _frame.loc[_frame['spec'] == "https%3A%2F%2Fgist.github.com%2Fjakevdp/256c3ad937af9ec7d4c65a29e5b6d454",
                           "provider"] = "Gist"
                _frame.loc[_frame['spec'] == "https%3A%2F%2Fgist.github.com%2Fjakevdp/256c3ad937af9ec7d4c65a29e5b6d454",
                           "spec"] = "jakevdp/256c3ad937af9ec7d4c65a29e5b6d454"
            elif a_name == "events-2019-01-28.jsonl":
                _frame.loc[_frame['spec'] == "loicmarie/ade5ea460444ea0ff72d5c94daa14500",
                           "provider"] = "Gist"
            elif a_name == "events-2019-02-22.jsonl":
                _frame.loc[_frame['spec'] == "minrk/6d61e5edfa4d2947b0ee8c1be8e79154",
                           "provider"] = "Gist"
            # get launches of mybinder federation of this date
            frame = _frame.loc[_frame['origin'].isin(origins) &
                               (_frame['timestamp'] >= datetime.combine(a_date, datetime.min.time())) &
                               (_frame['timestamp'] <= datetime.combine(a_date, datetime.max.time()))]
            app.logger.info(f"parse_mybinder_archives: "
                            f"{len(_frame)} - {len(frame)} = {len(_frame) - len(frame)} "
                            f"launches are excluded from frame.")
            # real archive count, because some archives have launch data from previous day (eg events-2019-02-22.jsonl)
            # those launches from prev day, they will be saved into database, because we save the whole frame
            a_count_real = len(frame)
            a_count_diff = a_count - a_count_real
            a_count = a_count_real
            if a_count_saved > a_count:
                app.logger.error(f"parse_mybinder_archives: "
                                 f"Error saved ({a_count_saved}) > in archive ({a_count}) for {a_name} - {a_date}")
                continue
            elif a_count_saved == a_count:
                app.logger.info(f"parse_mybinder_archives: "
                                f"everything is already saved. {a_count} - {a_count_saved} = {a_count-a_count_saved} "
                                f"launches of {a_name} - {a_date}")
                continue
            app.logger.info(f"parse_mybinder_archives: "
                            f"parsing {a_count} - {a_count_saved} = {a_count-a_count_saved} (?+{a_count_diff}) "
                            f"launches of {a_name} - {a_date}")

            new_launches = []
            if last_launch_timestamp is not None and last_launch_date == a_date:
                # delete launches of last launch in order to prevent double data in db
                # they will be re-saved
                # because archives are updated partially during the day and it is possible last launches in
                # batch x have the same timestamp with first launches in batch x+1
                # https://docs.sqlalchemy.org/en/latest/orm/query.html?highlight=delete#sqlalchemy.orm.query.Query.delete
                deleted = BinderLaunch.query.\
                          filter(BinderLaunch.origin.in_(origins)).\
                          filter(BinderLaunch.timestamp == last_launch_timestamp).\
                          delete(synchronize_session=False)
                db.session.commit()
                sleep(30)
                app.logger.info(f"parse_mybinder_archives: "
                                f"deleted last {deleted} launches at {last_launch_timestamp} -> {a_name} - {a_date}")
                new_launches = frame.loc[frame['timestamp'] >= last_launch_timestamp]
            elif a_count_saved == 0:
                # first time parsing this archive
                new_launches = frame
                # new_launches = frame[a_count_saved:]
            new_launches_count = len(new_launches)
            save_launches(new_launches, with_description)
            app.logger.info(f"parse_mybinder_archives: "
                            f"saved {new_launches_count} new launches for {a_name} - {a_date}")
            total_count += new_launches_count
            # sleepig half a second is also good to catch container logs
            sleep(30)
            a_count_saved = BinderLaunch.query.\
                            filter(BinderLaunch.origin.in_(origins),
                                   func.DATE(BinderLaunch.timestamp) == a_date).\
                            count()
            app.logger.info(f"parse_mybinder_archives: "
                            f"there are now total {a_count_saved} launches for {a_name} - {a_date}")

    app.logger.info(f"parse_mybinder_archives: done at {datetime.utcnow()} [UTC]: "
                    f"total {total_count} new launches saved")
    sleep(60)
