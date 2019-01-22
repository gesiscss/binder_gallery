from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class CreatedByGesis(db.Model):

    __tablename__ = 'created_by_gesis'

    ID = db.Column(db.Integer, primary_key=True)
    repo_name = db.Column(db.String())
    repo_url = db.Column(db.String())
    org_user = db.Column(db.String())
    provider = db.Column(db.String())
    # binder_url = db.Column(db.String())
    description = db.Column(db.String())

    def __init__(self, repo_name, repo_url, org_user, provider, description):
        self.repo_name = repo_name
        self.author = repo_url
        self.org_user = org_user
        self.provider = provider
        # self.binder_url = binder_url
        self.description = description

    def __repr__(self):
        return '<id {}>'.format(self.id)

    def serialize(self):
        return {
            'id': self.ID,
            'repo_name': self.repo_name,
            'repo_url': self.repo_url,
            'org_user': self.org_user,
            'provider': self.provider,
            # 'binder_url': self.binder_url,
            'description': self.description
        }




