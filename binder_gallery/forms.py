from .models import db, User
from wtforms import form, fields, validators


# Define login and registration forms (for flask-login)
class LoginForm(form.Form):
    name = fields.StringField(validators=[validators.data_required()])
    password = fields.PasswordField(validators=[validators.data_required()])

    def validate_name(self, field):
        user = self.get_user()
        if user is None:
            raise validators.ValidationError('Invalid user')

        if not user.check_password(self.password.data):
            raise validators.ValidationError('Invalid password')

    def get_user(self):
        return db.session.query(User).filter_by(name=self.name.data).first()
