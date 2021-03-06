'''
NoI Models

Creates the app
'''

from app import ORG_TYPES, VALID_SKILL_LEVELS, QUESTIONS_BY_ID, LEVELS

from flask_sqlalchemy import SQLAlchemy
from flask_security import UserMixin, RoleMixin
from flask_babel import lazy_gettext

from sqlalchemy import orm, types, Column, ForeignKey, UniqueConstraint, func, desc
from sqlalchemy_utils import EmailType, CountryType, LocaleType
from sqlalchemy.ext.hybrid import hybrid_property

import datetime

db = SQLAlchemy()  #pylint: disable=invalid-name


class User(db.Model, UserMixin): #pylint: disable=no-init,too-few-public-methods
    '''
    User
    '''
    __tablename__ = 'users'

    id = Column(types.Integer, autoincrement=True, primary_key=True)  #pylint: disable=invalid-name

    first_name = Column(types.String, info={
        'label': lazy_gettext('First Name'),
    })
    last_name = Column(types.String, info={
        'label': lazy_gettext('Last Name'),
    })

    email = Column(EmailType, unique=True, nullable=False, info={
        'label': lazy_gettext('Email'),
    })
    password = Column(types.String, nullable=False, info={
        'label': lazy_gettext('Password'),
    })
    active = Column(types.Boolean, nullable=False)

    last_login_at = Column(types.DateTime())
    current_login_at = Column(types.DateTime())
    last_login_ip = Column(types.Text)
    current_login_ip = Column(types.Text)
    login_count = Column(types.Integer)

    position = Column(types.String, info={
        'label': lazy_gettext('Position'),
    })
    organization = Column(types.String, info={
        'label': lazy_gettext('Organization'),
    })
    organization_type = Column(types.String, info={
        'label': lazy_gettext('Type of Organization'),
        'placeholder': lazy_gettext('The type of organization you work for'),
        'choices': [(k, v) for k, v in ORG_TYPES.iteritems()]
    })
    country = Column(CountryType, info={
        'label': lazy_gettext('Country'),
    })

    city = Column(types.String, info={
        'label': lazy_gettext('City')
    })

    latlng = Column(types.String, info={
        'label': lazy_gettext('Location'),
        'placeholder': lazy_gettext('Enter your location')
    })

    projects = Column(types.Text, info={
        'label': lazy_gettext('Projects'),
        'placeholder': lazy_gettext(
            'Details about projects you have been involved with...')
    })

    created_at = Column(types.DateTime(), default=datetime.datetime.now)
    updated_at = Column(types.DateTime(), default=datetime.datetime.now,
                        onupdate=datetime.datetime.now)

    @property
    def helpful_users(self, limit=10):
        '''
        Returns a list of users with matching positive skills, ordered by the
        most helpful (highest score) descending.
        '''
        learn_level = LEVELS['LEVEL_I_WANT_TO_LEARN']['score']
        skills_needing_help = [s.name for s in self.skills if s.level == learn_level]
        user_id_scores = dict(db.session.query(UserSkill.user_id, func.sum(UserSkill.level)).\
                              filter(UserSkill.name.in_(skills_needing_help)).\
                              filter(UserSkill.level > learn_level).\
                              group_by(UserSkill.user_id).\
                              order_by(desc(func.sum(UserSkill.level))).\
                              limit(limit).all())
        users = db.session.query(User).\
                filter(User.id.in_(user_id_scores.keys())).all()
        for user in users:
            user.score = user_id_scores[user.id]
        return sorted(users, key=lambda x: x.score, reverse=True)

    @property
    def skill_levels(self):
        '''
        Dictionary of this user's entered skills, keyed by the id of the skill.
        '''
        return dict([(skill.name, skill.level) for skill in self.skills])

    def set_skill(self, skill_name, skill_level):
        '''
        Set the level of a single skill by name.
        '''
        if skill_name not in QUESTIONS_BY_ID:
            return
        try:
            if int(skill_level) not in VALID_SKILL_LEVELS:
                return
        except ValueError:
            return
        for skill in self.skills:
            if skill_name == skill.name:
                skill.level = skill_level
                db.session.add(skill)
                return
        db.session.add(UserSkill(user_id=self.id,
                                 name=skill_name,
                                 level=skill_level))

    roles = orm.relationship('Role', secondary='role_users',
                             backref=orm.backref('users', lazy='dynamic'))

    _expertise_domains = orm.relationship('UserExpertiseDomain', cascade='all,delete-orphan')
    _languages = orm.relationship('UserLanguage', cascade='all,delete-orphan')
    skills = orm.relationship('UserSkill', cascade='all,delete-orphan')

    @hybrid_property
    def expertise_domains(self):
        '''
        Convenient list of expertise domains by name.
        '''
        return [ed.name for ed in self._expertise_domains]

    @expertise_domains.setter
    def _expertise_domains_setter(self, values):
        '''
        Update expertise domains in bulk.  Values are array of names.
        '''
        # Only add new expertise
        for val in values:
            if val not in self.expertise_domains:
                db.session.add(UserExpertiseDomain(name=val,
                                                   user_id=self.id))

        # delete expertise no longer found
        for exp in self._expertise_domains:
            if exp.name not in values:
                self._expertise_domains.remove(exp)

    @hybrid_property
    def languages(self):
        '''
        Convenient list of locales for this user.
        '''
        return [l.locale for l in self._languages]

    @languages.setter
    def _languages_setter(self, values):
        '''
        Update locales for this user in bulk.  Values are an array of language
        codes.
        '''
        locale_codes = [l.language for l in self.languages]
        # only add new languages
        for val in values:
            if val not in locale_codes:
                db.session.add(UserLanguage(locale=val,
                                            user_id=self.id))

        # delete languages no longer found
        for lan in self._languages:
            if lan.locale.language not in values:
                self._languages.remove(lan)
                #db.session.delete(lan)


class UserExpertiseDomain(db.Model):  #pylint: disable=no-init,too-few-public-methods
    '''
    Expertise domain of a single user.  List is read from YAML.
    '''
    __tablename__ = 'user_expertise_domains'

    id = Column(types.Integer, autoincrement=True, primary_key=True)  #pylint: disable=invalid-name
    name = Column(types.String, nullable=False)

    user_id = Column(types.Integer(), ForeignKey('users.id'), nullable=False)

    constraint = UniqueConstraint('user_id', 'name')


class UserLanguage(db.Model):  #pylint: disable=no-init,too-few-public-methods
    '''
    Language of a single user.
    '''
    __tablename__ = 'user_languages'

    id = Column(types.Integer, autoincrement=True, primary_key=True)  #pylint: disable=invalid-name
    locale = Column(LocaleType, nullable=False)

    user_id = Column(types.Integer(), ForeignKey('users.id'), nullable=False)

    constraint = UniqueConstraint('user_id', 'locale')


class Role(db.Model, RoleMixin): #pylint: disable=no-init,too-few-public-methods
    '''
    User role for permissioning
    '''
    __tablename__ = 'roles'

    id = Column(types.Integer, autoincrement=True, primary_key=True)  #pylint: disable=invalid-name
    name = Column(types.Text, unique=True)
    description = Column(types.Text)


class RoleUser(db.Model): #pylint: disable=no-init,too-few-public-methods
    '''
    Join table between a user and her roles.
    '''
    __tablename__ = 'role_users'

    id = Column(types.Integer, autoincrement=True, primary_key=True)  #pylint: disable=invalid-name

    user_id = Column(types.Integer(), ForeignKey('users.id'), nullable=False)
    role_id = Column(types.Integer(), ForeignKey('roles.id'), nullable=False)

    constraint = UniqueConstraint('user_id', 'role_id')


class UserSkill(db.Model): #pylint: disable=no-init,too-few-public-methods
    '''
    Join table between users and their skills, which includes their level of
    knowledge for that skill (level).
    '''
    __tablename__ = 'user_skills'

    id = Column(types.Integer, autoincrement=True, primary_key=True)  #pylint: disable=invalid-name

    created_at = Column(types.DateTime(), default=datetime.datetime.now)
    updated_at = Column(types.DateTime(), default=datetime.datetime.now,
                        onupdate=datetime.datetime.now)

    level = Column(types.Integer, nullable=False)
    name = Column(types.String, nullable=False)

    user_id = Column(types.Integer, ForeignKey('users.id'), nullable=False)

    constraint = UniqueConstraint('user_id', 'name')
