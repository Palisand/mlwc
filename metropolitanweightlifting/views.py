from metropolitanweightlifting import app, db, login_manager  # bcrypt

import forms
from models import Athlete, User, Meet, MeetResult, Article, ArticleImage
from util import events
from util.tools import (
    get_formatted_meet_results,
    get_meet_dict_from_csv,
    allowed_image_type,
    can_wrap_text,
    get_image_dimensions,
    get_video_source,
    ArticleImageInfo,
    save_article_image,
    save_athlete_images,
    remove_athlete_images,
    WEIGHT_CLASSES,
    get_bylaws,
    get_fail_gif_random,
)
from flask import flash, render_template, request, redirect, url_for, session
from flask.ext.login import current_user, login_user, logout_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash


@app.route('/')
def index():
    upcoming_events = events.get_latest(3)
    latest_meet = Meet.query.order_by(db.desc(Meet.date)).first()
    latest_article = Article.query.order_by(db.desc(Article.created_at)).first()
    if latest_meet:
        meet_results = get_formatted_meet_results(latest_meet.results)
    else:
        meet_results = None
    return render_template('main/latest.html',
                           upcoming_events=upcoming_events,
                           article=latest_article,
                           latest_meet=latest_meet,
                           results=meet_results)


@app.route('/calendar')
def calendar():
    iframe_src = "https://www.google.com/calendar/embed?src=metropolitanweightlifting%40gmail.com&ctz=America/New_York"
    return render_template('main/calendar.html', src=iframe_src)


@app.route('/results/', methods=['GET', 'POST'])
@app.route('/results/<int:meet_id>', methods=['GET', 'POST'])
def results(meet_id=None):
    if meet_id:
        meet = Meet.query.filter_by(id=meet_id).first()
        if not meet:
            return redirect(url_for('results'))
        meet_results = get_formatted_meet_results(meet.results)

        available_genders = [g for (g, wc) in meet_results.iteritems()]
        gender_data = request.args.get('gender', available_genders[0])
        available_weight_classes = [wc for (wc, r) in meet_results[gender_data].iteritems()]

        form = forms.FilterResultsForm(available_genders, available_weight_classes)
        form.gender.data = gender_data
        form.weight_class.data = request.args.get('weight_class', 'all')

        if form.weight_class.data == 'all':
            weight_classes = WEIGHT_CLASSES[gender_data]
        else:
            weight_classes = [form.weight_class.data]

        delete_form = forms.DeleteMeetForm()
        if request.method == 'POST' and delete_form.validate_on_submit:
            app.logger.debug("Deleting %s" % meet)
            for result in meet.results:
                db.session.delete(result)
            db.session.delete(meet)
            db.session.commit()
            return redirect(url_for('results'))

        return render_template('main/results_meet.html',
                               meet=meet,
                               results=meet_results,
                               form=form,
                               gender=form.gender.data,
                               weight_classes=weight_classes,
                               delete_form=delete_form)

    form = None
    if current_user.is_authenticated():
        form = forms.AddMeetForm()
        if request.method == 'POST' and form.validate_on_submit():

            # TODO: use form.file like athlete save photo
            csv_file = request.files.get(form.csv_file.name)
            if csv_file and csv_file.content_type == 'text/csv':
                try:
                    app.logger.debug('Uploading meet info csv file %s' % csv_file.filename)
                    meet_data = get_meet_dict_from_csv(csv_file)
                except Exception as e:
                    form.csv_file.errors.append('Error extracting information from file.')
                    form.csv_file.errors.append('DETAILS: ' + str(e))
                else:
                    existing_meet = Meet.query.filter_by(sanction_number=meet_data['sanction_number']).first()
                    if existing_meet:
                        # TODO: DictDiffer() compare db result to current and UPDATE instead of REPLACE
                        for result in existing_meet.results:
                            db.session.delete(result)
                        db.session.delete(existing_meet)
                        db.session.commit()
                        flash("REMOVED old meet %s." % existing_meet.sanction_number)

                    meet = Meet(
                        meet_data['sanction_number'],
                        meet_data['name'],
                        meet_data['date'],
                        meet_data['city'],
                        meet_data['state'],
                    )
                    db.session.add(meet)
                    db.session.commit()
                    flash("ADDED meet %s (%s : %s)." % (meet.sanction_number, meet.date, meet.name))

                    for result in meet_data['results']:
                        meet_result = MeetResult(
                            result['gender'],
                            result['member_id'],
                            result['weight_class'],
                            result['place'],
                            result['name'],
                            result['body_weight'],
                            result['snatch_1'],
                            result['snatch_2'],
                            result['snatch_3'],
                            result['snatch_best'],
                            result['clean_jerk_1'],
                            result['clean_jerk_2'],
                            result['clean_jerk_3'],
                            result['clean_jerk_best'],
                            result['total'],
                            meet.id,
                        )
                        db.session.add(meet_result)

                        if form.update_athletes.data:
                            athlete = Athlete.query.filter_by(id=result['member_id']).first()
                            if athlete:
                                athlete.snatch = max(athlete.snatch, result['snatch_best'])
                                athlete.clean_jerk = max(athlete.clean_jerk, result['clean_jerk_best'])
                                athlete.weight_class = result['weight_class']
                                athlete.body_weight = result['body_weight']

                        db.session.commit()

                    return redirect(url_for('results'))
            else:
                form.csv_file.errors.append('Submitted file is not a CSV file.')

    session['meet_year'] = request.args.get('year') or session.get('meet_year', 'all')
    available_years = set([m.date.year for m in Meet.query.all()])
    filter_form = forms.FilterMeetsForm(sorted(available_years, reverse=True), session['meet_year'])

    if session['meet_year'] == 'all':
        meets = Meet.query.order_by(db.desc(Meet.date)).all()
    else:
        meets = Meet.query.filter(db.extract('year', Meet.date) == session['meet_year'])
    return render_template('main/results.html', form=form, filter_form=filter_form, meets=meets)


@app.route('/articles/')
@app.route('/articles/<int:article_id>', methods=['GET', 'POST'])
def articles(article_id=None):
    if article_id:
        delete_form = forms.DeleteArticleForm()
        if request.method == 'POST' and delete_form.validate_on_submit():
            article = Article.query.filter_by(id=delete_form.article_id.data).first()
            app.logger.debug("Deleting %s" % article)
            db.session.delete(article)
            db.session.commit()
            return redirect(url_for('articles'))

        article = Article.query.filter_by(id=article_id).first()
        if not article:
            return redirect(url_for('articles'))

        return render_template('main/article.html', article=article, delete_form=delete_form)

    articles_ = Article.query.order_by(db.desc(Article.created_at)).all()
    return render_template('main/articles.html', articles=articles_)


def validate_image_files(files, form):
    for image_file in files:
        if not allowed_image_type(image_file):
            form.images.errors.append("Invalid file or image format: %s." % image_file.filename)


def save_article_images(image_files, image_container, form):
    for caption_id_num, image_file in enumerate(image_files):
        try:
            image_src = save_article_image(image_file)
        except Exception:
            # TODO: test exception and all possible errors for this form!!!
            error_message = "Error saving image: %s." % image_file.filename
            form.images.errors.append(error_message)
            app.logger.exception(error_message)
        else:
            width, height = get_image_dimensions(image_src, app.config['ARTICLE_IMAGE_UPLOAD_FOLDER'])
            caption_id = '_'.join(('img_caption', str(caption_id_num)))
            caption = request.form[caption_id]
            image_container.append(ArticleImageInfo(image_src, caption, width, height))


@app.route('/add_article', methods=['GET', 'POST'])
@login_required
def add_article():

    form = forms.AddArticleForm()

    if request.method == 'POST' and form.validate_on_submit():

        images = []
        if form.type.data == 'images':
            image_files = request.files.getlist("images")
            validate_image_files(image_files, form)
            if form.images.errors:
                return render_template('main/articles_admin.html', form=form, type='Add')
            save_article_images(image_files, images, form)
            if form.images.errors:
                return render_template('main/articles_admin.html', form=form, type='Add')

        # wrap_text check
        if len(images) == 1:
            if not can_wrap_text(images[0]):
                form.wrap_text.data = False
        else:
            form.wrap_text.data = False

        if form.type.data == 'video':
            video_src = get_video_source(form.video_src.data)
        else:
            video_src = None

        article = Article(
            form.type.data,
            form.title.data,
            form.body.data,
            video_src,
            form.wrap_text.data
        )
        db.session.add(article)
        db.session.commit()

        if images:
            for image in images:
                article_image = ArticleImage(
                    image.src,
                    image.caption,
                    image.width,
                    image.height,
                    article.id
                )
                db.session.add(article_image)
            db.session.commit()

        return redirect(url_for('articles'))

    return render_template('main/articles_admin.html', form=form, type='Add')


@app.route('/edit_article/<int:article_id>', methods=['GET', 'POST'])
@login_required
def edit_article(article_id):

    article = Article.query.filter_by(id=article_id).first()
    form = forms.AddArticleForm(article)
    delete_form = forms.DeleteArticleImageForm()

    if request.method == 'GET':
        form.autofill()

    if request.method == 'POST':

        if delete_form.validate_on_submit():
            article_image = ArticleImage.query.filter_by(id=delete_form.article_image_id.data).first()
            app.logger.debug("Deleting %s" % article_image)  # not the file though
            db.session.delete(article_image)
            db.session.commit()
            return redirect(url_for('edit_article', article_id=article.id))

        if form.validate_on_submit():
            added_images = []
            if form.type.data == 'images' and form.images.data:
                image_files = request.files.getlist("images")
                validate_image_files(image_files, form)
                if form.images.errors:
                    return render_template('main/articles_admin.html', form=form, type='Edit',
                                           delete_form=delete_form, article=article)
                save_article_images(image_files, added_images, form)
                if form.images.errors:
                    return render_template('main/articles_admin.html', form=form, type='Edit',
                                           delete_form=delete_form, article=article)
            # wrap_text check
            if len(added_images) == 1:
                if not can_wrap_text(added_images[0]):
                    form.wrap_text.data = False
            elif len(article.images.all()) == 1:
                if not can_wrap_text(article.images.first()):
                    form.wrap_text.data = False
            else:
                form.wrap_text.data = False

            if form.type.data == 'video':
                video_src = get_video_source(form.video_src.data)
            else:
                video_src = None

            article.type = form.type.data
            article.title = form.title.data
            article.body = form.body.data
            article.video_src = video_src
            article.wrap_text = form.wrap_text.data
            db.session.commit()

            for image in article.images:
                caption_id = 'img_existing_caption_{}'.format(image.id)
                image.caption = request.form[caption_id]
            db.session.commit()

            if added_images:
                for image in added_images:
                    article_image = ArticleImage(
                        image.src,
                        image.caption,
                        image.width,
                        image.height,
                        article.id
                    )
                    db.session.add(article_image)
                db.session.commit()

            return redirect(url_for('articles') + str(article.id))

    return render_template('main/articles_admin.html', form=form, type='Edit',
                           delete_form=delete_form, article=article)


@app.route('/minutes')
def minutes():
    return render_template('main/minutes.html')


@app.route('/bylaws')
def bylaws():
    contents = get_bylaws()
    return render_template('main/bylaws.html', contents=contents)


@app.route('/bios', methods=['GET', 'POST'])
def bios():
    delete_form = forms.DeleteAthleteForm()
    if request.method == 'POST' and delete_form.validate_on_submit():
        athlete = Athlete.query.filter_by(id=delete_form.athlete_id.data).first()
        app.logger.debug("Deleting %s" % athlete)
        if athlete.has_photo:
            remove_athlete_images(athlete)
        db.session.delete(athlete)
        db.session.commit()
        return redirect(url_for('bios'))
    athletes = Athlete.query.all()  # TODO: paginate with load more
    return render_template('main/bios.html', delete_form=delete_form, athletes=athletes)


@app.route('/add_bio', methods=['GET', 'POST'])
@login_required
def add_bio():

    form = forms.AddBioForm()

    if request.method == 'POST' and form.validate_on_submit():
        try:
            photo_src = save_athlete_images(form.usa_id.data, form.photo.data)
        except Exception:
            form.photo.errors.append("Error saving submitted photo.")
            app.logger.exception("Error saving submitted photo.")
        else:
            athlete = Athlete(
                form.usa_id.data,
                form.gender.data,
                form.firstname.data.title(),
                form.lastname.data.title(),
                form.weight.data,
                form.weight_class.data,
                form.snatch.data,
                form.clean_jerk.data,
                form.description.data,
                has_photo=bool(photo_src)
            )

            app.logger.debug("Adding new %r to database" % athlete)
            db.session.add(athlete)
            db.session.commit()

            flash("ADDED athlete bio for ' %s %s '." % (athlete.firstname, athlete.lastname))
            return redirect(url_for('add_bio'))

    return render_template('main/bios_admin.html', form=form, type='Add')


@app.route('/edit_bio/<int:athlete_id>', methods=['GET', 'POST'])
@login_required
def edit_bio(athlete_id):

    athlete = Athlete.query.filter_by(id=athlete_id).first()
    form = forms.AddBioForm(athlete)

    if request.method == 'GET':
        form.autofill()

    if request.method == 'POST' and form.validate_on_submit():
        try:
            photo_src = save_athlete_images(athlete.id, form.photo.data)
        except Exception:
            form.photo.errors.append("Error saving submitted photo.")
            app.logger.exception("Error saving submitted photo.")
        else:
            athlete.gender = form.gender.data
            athlete.firstname = form.firstname.data.title()
            athlete.lastname = form.lastname.data.title()
            athlete.body_weight = form.weight.data
            athlete.weight_class = form.weight_class.data
            athlete.snatch = form.snatch.data
            athlete.clean_jerk = form.clean_jerk.data
            athlete.description = form.description.data
            athlete.has_photo = athlete.has_photo or bool(photo_src)

            db.session.commit()

            return redirect(url_for('bios', _anchor=athlete_id))

    return render_template('main/bios_admin.html', form=form, type='Edit', athlete=athlete)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.route('/login', methods=['GET', 'POST'])
def login():
    error = None
    form = forms.LoginForm()
    if request.method == 'POST' and form.validate_on_submit():
        valid_user = User.query.filter_by(username=form.username.data).first()
        # if valid_user and bcrypt.check_password_hash(valid_user.password, form.password.data):
        if valid_user and check_password_hash(valid_user.password, form.password.data):
            login_user(valid_user, remember=form.remember.data)
            return redirect(url_for('login'))
        else:
            error = 'Incorrect password or username.'
    return render_template('main/login.html', form=form, login_error=error)


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('login'))


@app.route('/change_password', methods=['GET', 'POST'])
def change_password():
    form = forms.ChangePasswordForm()
    if request.method == 'POST' and form.validate_on_submit():
        # if bcrypt.check_password_hash(current_user.password, form.current_password.data):
        if check_password_hash(current_user.password, form.current_password.data):
            # current_user.password = bcrypt.generate_password_hash(form.new_password.data)
            current_user.password = generate_password_hash(form.new_password.data)
            db.session.commit()
            return redirect(url_for('login'))
        else:
            form.current_password.errors.append('Incorrect password.')
    return render_template('main/change_password.html', form=form)


@app.errorhandler(404)
def not_found(e):
    return render_template('error/404.html', page_error=True, gif_src=get_fail_gif_random()), 404


@app.errorhandler(403)
def forbidden(e):
    return render_template('error/403.html', page_error=True, gif_src=get_fail_gif_random()), 403


@app.errorhandler(500)
def internal_server_error(e):
    return render_template('error/500.html', page_error=True, gif_src=get_fail_gif_random()), 500