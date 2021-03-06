'''
NoI __init__

Creates globals
'''

from flask_assets import Bundle, Environment
from flask_security import Security
from flask_cache import Cache
from flask_babel import Babel
from flask_bcrypt import Bcrypt
from flask.ext.uploads import UploadSet, IMAGES
from celery import Celery
from flask_mail import Mail
from flask_s3 import FlaskS3
from flask_wtf.csrf import CsrfProtect

from slugify import slugify
from babel import Locale, UnknownLocaleError
import yaml
import locale

s3 = FlaskS3()
mail = Mail()
security = Security()
csrf = CsrfProtect()
babel = Babel()
bcrypt = Bcrypt()

celery = Celery(
    __name__,
    #broker=os.environ.get('REDISGREEN_URL', None),
    include=[]
)

assets = Environment()

main_css = Bundle('css/vendor/bootstrap.css',
                  output='gen/main_packed.%(version)s.css')
assets.register('main_css', main_css)

main_js = Bundle('js/plugins.js',
                 #filters='jsmin',
                 output='gen/main_packed.%(version)s.js')
assets.register('main_js', main_js)

photos = UploadSet('photos', IMAGES)

cache = Cache()

LEVELS = {'LEVEL_I_CAN_EXPLAIN': {'score': 2,
                                  'icon': '<i class="fa-fw fa fa-book"></i>',
                                  'label': 'I can explain'},
          'LEVEL_I_CAN_DO_IT': {'score': 5,
                                'icon': '<i class="fa-fw fa fa-cogs"></i>',
                                'label': 'I can do it'},
          'LEVEL_I_CAN_REFER': {'score': 1,
                                'icon': '<i class="fa-fw fa fa-mail-forward"></i>',
                                'label': 'I can refer you'},
          'LEVEL_I_WANT_TO_LEARN': {'score': -1,
                                    'icon': '<i class="fa-fw fa fa-question"></i>',
                                    'label': 'I want to learn'}}

VALID_SKILL_LEVELS = [v['score'] for k, v in LEVELS.iteritems()]

NOI_COLORS = '#D44330,#D6DB63,#BFD19F,#83C8E7,#634662,yellow,gray'.split(',')

DOMAINS = """Business Licensing and Regulation
Civil Society
Corporate Social Responsibility
Defense and Security
Economic Development
Education
Emergency Services
Environment
Extractives Industries
Governance
Health
Human Rights
Immigration and Citizenship Services
Judiciary
Labor
Legislature
Media and Telecommunications
Public Safety
Research
Sanitation
Social Care
Sub-National Governance
Talent Services
Transportation
Water and Electricity""".split('\n')

LOCALES = []
_LOCALE_CODES = set()
for l in locale.locale_alias.keys():
    if len(l) == 2 and l not in _LOCALE_CODES:
        _LOCALE_CODES.add(l)
for l in sorted(_LOCALE_CODES):
    try:
        LOCALES.append(Locale(l))
    except UnknownLocaleError:
        pass

ORG_TYPES = {'edu': 'Academia',
             'com': 'Private Sector',
             'org': 'Non Profit',
             'gov': 'Government',
             'other': 'Other'}

# Process YAML file
CONTENT = yaml.load(open('/noi/app/content.yaml'))
QUESTIONS_BY_ID = {}
for area in CONTENT['areas']:
    for topic in area.get('topics', []):
        for question in topic['questions']:
            question_id = slugify('_'.join([area['id'], topic['topic'], question['label']]))
            question['id'] = question_id
            question['area_id'] = area['id']
            question['topic'] = topic['topic']
            if question_id in QUESTIONS_BY_ID:
                raise Exception("Duplicate skill id {}".format(question_id))
            else:
                QUESTIONS_BY_ID[question_id] = question
