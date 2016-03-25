from models import Athlete
from flask.ext.wtf import Form
from wtforms import (
    StringField,
    TextAreaField,
    SelectField,
    FileField,
    PasswordField,
    FloatField,
    IntegerField,
    BooleanField,
)
from wtforms.validators import (
    DataRequired,
    InputRequired,
    Optional,
    Length,
)
from util.tools import (
    pounds_to_kilos,
    get_weight_class,
    allowed_image_type,
)


# class AddMinutesForm(Form):
#     pdf_file = FileField(validators=DataRequired())
#     date
#     title
#     content


class AddMeetForm(Form):
    excel_files = FileField('Add Meet Excel Files', validators=[DataRequired(message='Please choose a file.')])
    update_athletes = BooleanField('Update Athlete Bios')

    # def __init__(self):
    #     super(AddMeetForm, self).__init__()
    #     self.update_athletes.data = True
    # always keeps True even when unchecked! forms.AddMeetForm(update_athletes=True) used instead


class AddBioForm(Form):
    usa_id = IntegerField('USA Weightlifting Member ID', validators=[InputRequired()])
    firstname = StringField(
        'First Name', validators=[
            DataRequired(),
            Length(min=1, max=80)
        ]
    )
    lastname = StringField(
        'Last Name', validators=[
            DataRequired(),
            Length(min=1, max=80)
        ]
    )
    snatch = IntegerField('Best Snatch', validators=[InputRequired()])
    snatch_unit = SelectField(choices=[('kg', 'kilograms'), ('lb', 'pounds')])
    clean_jerk = IntegerField('Best C & J', validators=[InputRequired()])
    clean_jerk_unit = SelectField(choices=[('kg', 'kilograms'), ('lb', 'pounds')])
    gender = SelectField('Gender', choices=[('m', 'Male'), ('f', 'Female')])
    weight = FloatField('Weight', validators=[Optional()])
    weight_unit = SelectField(choices=[('kg', 'kilograms'), ('lb', 'pounds')])
    weight_class_male = SelectField('Weight Class', choices=[
        ('auto', 'Auto'),
        ('56', '56 kg (123 lb)'),
        ('62', '62 kg (137 lb)'),
        ('69', '69 kg (152 lb)'),
        ('77', '77 kg (170 lb)'),
        ('85', '85 kg (187 lb)'),
        ('94', '94 kg (207 lb)'),
        ('105', '105 kg (231 lb)'),
        ('105+', '105 kg+ (231 lb+)'),
    ])
    weight_class_female = SelectField('Weight Class', choices=[
        ('auto', 'Auto'),
        ('48', '48 kg (106 lb)'),
        ('53', '53 kg (117 lb)'),
        ('58', '58 kg (128 lb)'),
        ('63', '63 kg (139 lb)'),
        ('69', '69 kg (152 lb)'),
        ('75', '75 kg (165 lb)'),
        ('75+', '75 kg+ (165 lb+)'),
    ])
    photo = FileField('Photo', validators=[Optional()])
    description = TextAreaField('Description', validators=[Optional()])

    def __init__(self, athlete=None):
        super(AddBioForm, self).__init__()
        self.weight_class = None
        self.weight_class_by_gender = {
            'm': self.weight_class_male,
            'f': self.weight_class_female,
        }
        self.athlete = athlete

    def autofill(self):
        if self.athlete:
            self.usa_id.data = self.athlete.id
            self.firstname.data = self.athlete.firstname
            self.lastname.data = self.athlete.lastname
            self.snatch.data = self.athlete.snatch
            self.clean_jerk.data = self.athlete.clean_jerk
            self.gender.data = self.athlete.gender
            self.weight.data = self.athlete.body_weight
            self.weight_class_by_gender[self.gender.data].data = self.athlete.weight_class
            self.description.data = self.athlete.description
        else:
            raise Exception('autofill FAILED: No athlete specified during form construction.')

    def validate(self):
        base_validate = super(AddBioForm, self).validate()

        if self.athlete:
            if self.athlete.id != self.usa_id.data:
                existing_athlete = Athlete.query.filter_by(id=self.usa_id.data).first()
                if existing_athlete:
                    self.usa_id.errors.append("%s already exists" % existing_athlete)
        else:
            self.athlete = Athlete.query.filter_by(id=self.usa_id.data).first()
            if self.athlete:
                self.usa_id.errors.append("%s already exists" % self.athlete)

        if self.weight_unit.data == 'lb' and self.weight.data:
            self.weight.data = round(pounds_to_kilos(self.weight.data), 2)

        self.weight_class = self.weight_class_by_gender[self.gender.data]
        if self.weight_class.data == 'auto':
            if self.weight.data:
                self.weight_class.data = get_weight_class(self.gender.data, self.weight.data)
            else:
                self.weight.errors.append("Weight Class is 'Auto'")

        if self.photo.data:
            if not allowed_image_type(self.photo.data):
                self.photo.errors.append("Invalid file or image format.")

        if not base_validate or self.usa_id.errors or self.weight.errors or self.photo.errors:
            return False

        if self.snatch_unit.data == 'lb':
            self.snatch.data = int(pounds_to_kilos(self.snatch.data))

        if self.clean_jerk_unit.data == 'lb':
            self.clean_jerk.data = int(pounds_to_kilos(self.clean_jerk.data))

        return True


class AddArticleForm(Form):
    title = StringField('Title', validators=[DataRequired()])
    images = FileField('Add Image(s)')
    img_caption_0 = StringField('Caption', validators=[Optional()])
    video_src = StringField('Youtube Video Source or Embed Code')
    pdf = FileField('PDF File')
    body = TextAreaField('Body')
    type = SelectField('Type', choices=[
        ('text_only', 'Text Only'),
        ('images', 'Image(s)'),
        ('video', 'Video'),
        ('pdf', 'PDF')
    ])
    wrap_text = BooleanField('Wrap Text')

    def __init__(self, article=None):
        super(AddArticleForm, self).__init__()
        self.article = article

    def autofill(self):
        if self.article:
            self.title.data = self.article.title
            self.body.data = self.article.body
            self.video_src.data = self.article.video_src
            self.type.data = self.article.type
            self.wrap_text.data = self.article.wrap_text
        else:
            raise Exception('autofill FAILED: No article specified during form construction.')

    def validate(self):
        base_validate = super(AddArticleForm, self).validate()

        type_to_required_field = {
            'text_only': self.body,
            'images': self.images,
            'video': self.video_src,
            'pdf': self.pdf
        }
        required_field = type_to_required_field[self.type.data]
        if not required_field.data:
            if required_field is self.images and self.article and len(self.article.images.all()):
                pass
            else:
                required_field.errors.append('This field is required.')

        if required_field == self.pdf and 'pdf' not in str(self.pdf.data.mimetype):
            required_field.errors.append('Invalid file format.')

        if not base_validate or required_field.errors: # self.body.errors or self.images.errors or self.video_src.errors or self.pdf.errors:
            return False

        if not self.body.data:
            self.wrap_text.data = False

        return True


class FilterMeetsForm(Form):

    year = SelectField('Year')

    def __init__(self, years, default, **kwargs):
        kwargs.setdefault('year', default)
        super(FilterMeetsForm, self).__init__(**kwargs)
        self.year.choices = [('all', 'All')] + [(str(y), str(y)) for y in years]


class FilterResultsForm(Form):

    gender = SelectField('Gender')
    weight_class = SelectField('Weight Class')

    def __init__(self, genders, weight_classes):
        super(FilterResultsForm, self).__init__()
        self.gender.choices = []
        if 'm' in genders:
            self.gender.choices.append(('m', 'Male'))
        if 'f' in genders:
            self.gender.choices.append(('f', 'Female'))
        self.weight_class.choices = [('all', 'All')] + [(wc, wc) for wc in weight_classes]


class FilterAthletesForm(Form):
    name = StringField('Name', validators=[Optional()])
    usa_id = StringField('USA Weightlifting ID', validators=[Optional()])
    gender = SelectField('Gender', choices=[('all', 'All'), ('m', 'male'), ('f', 'female')])
    weight_class_male = SelectField('Weight Class Male', choices=[
        ('all', 'All'),
        ('56', '56 kg (123 lb)'),
        ('62', '62 kg (137 lb)'),
        ('69', '69 kg (152 lb)'),
        ('77', '77 kg (170 lb)'),
        ('85', '85 kg (187 lb)'),
        ('94', '94 kg (207 lb)'),
        ('105', '105 kg (231 lb)'),
        ('105+', '105 kg+ (231 lb+)'),
    ])
    weight_class_female = SelectField('Weight Class Female', choices=[
        ('all', 'All'),
        ('48', '48 kg (106 lb)'),
        ('53', '53 kg (117 lb)'),
        ('58', '58 kg (128 lb)'),
        ('63', '63 kg (139 lb)'),
        ('69', '69 kg (152 lb)'),
        ('75', '75 kg (165 lb)'),
        ('75+', '75 kg+ (165 lb+)'),
    ])
    sort_by = SelectField('Sort By', choices=[
        ('name', 'Name'),
        ('weight_class', 'Weight Class'),
        ('snatch', 'Snatch'),
        ('clean_jerk', 'Clean and Jerk'),
    ])
    int_sort_order = SelectField('Order', choice=[('lg', 'Least to Greatest'), ('gl', 'Greatest to Least')])
    str_sort_order = SelectField('Order', choice=[('az', 'A to Z'), ('za', 'Z to A')])


class DeleteAthleteForm(Form):
    athlete_id = IntegerField('Delete Athlete by ID', validators=[Optional()])


class DeleteArticleImageForm(Form):
    article_image_id = IntegerField('Delete ArticleImage by ID', validators=[DataRequired()])


class DeleteArticleForm(Form):
    article_id = IntegerField('Delete Article by ID', validators=[DataRequired()])


class DeleteMeetForm(Form):
    meet_id = IntegerField('Delete Meet by ID', validators=[DataRequired()])


class LoginForm(Form):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')


class ChangePasswordForm(Form):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired(), Length(min=8)])

    def validate(self):
        base_validate = super(ChangePasswordForm, self).validate()

        if self.current_password.data == self.new_password.data:
            self.new_password.errors.append("Matches input for current password")

        if not base_validate or self.new_password.errors:
            return False

        return True
