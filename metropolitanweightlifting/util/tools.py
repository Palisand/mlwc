from metropolitanweightlifting import app

import os
import re
import time
import json
import random
import subprocess
from datetime import date, datetime
from time import mktime
from tempfile import NamedTemporaryFile
from collections import OrderedDict, namedtuple
from markdown import Markdown
from werkzeug.utils import secure_filename
from markupsafe import escape
import parsedatetime

POUND_KILO_RATIO = 2.2

ALLOWED_IMAGE_SUBTYPES = frozenset(('png', 'jpeg'))
ALLOWED_IMAGE_MIMETYPES = frozenset('/'.join(('image', st)) for st in ALLOWED_IMAGE_SUBTYPES)
RESULT_LENGTH = 19
PLACE_TO_DBVAL = {
    'EXTRA': 998,
    '': 999,
}
WEIGHT_CLASSES = {
    'm': ['56', '62', '69', '77', '85', '94', '105', '105+'],
    'f': ['48', '53', '58', '63', '69', '75', '75+'],
}
FAIL_GIFS = {
    0: '/static/image/fail_gifs/olympics_1.gif',
    1: '/static/image/fail_gifs/olympics_2.gif',
    2: '/static/image/fail_gifs/olympics_3.gif',
}
RESIZED_FILENAME_JPG_FORMAT = '{}_{}.jpg'
IMAGEMAGICK_PROCESS_TIMEOUT = 20
ImageSize = namedtuple('ImageSize', ['name', 'width', 'height'])
NORMAL = ImageSize('normal', 120, 120)
SMALL = ImageSize('small', 24, 24)
ATHLETE_IMAGE_SIZES = frozenset((NORMAL, SMALL))
ArticleImageInfo = namedtuple('ArticleImageInfo', ['src', 'caption', 'width', 'height'])
SANCTION_NUMBER_DIGITS = 6


class LastUpdatedOrderedDict(OrderedDict):

    def __setitem__(self, key, value):
        if key in self:
            del self[key]
        OrderedDict.__setitem__(self, key, value)


# ---------- #
# CONVERSION #
# ---------- #

def markdown_to_html(text):
    # leave '>' for blockquotes
    text = str(escape(text).encode('ascii', 'ignore')).replace('&gt;', '>')
    m = Markdown()
    return m.convert(text)


def pounds_to_kilos(lb):
    return lb / POUND_KILO_RATIO


# ---------- #
# VALIDATION #
# ---------- #

def allowed_image_type(image_file):
    return image_file.mimetype in ALLOWED_IMAGE_MIMETYPES


def can_wrap_text(image):
    """
    This may be subject to change...
    """
    return image.width <= image.height


# ---------- #
# PROCESSING #
# ---------- #

def normalize_place(raw_data):
    place = raw_data.upper().strip()
    if place.isdigit():
        return int(place)
    return PLACE_TO_DBVAL[place]


def resize_image(original_filename, new_filename, size):
    dimensions = "{}x{}^".format(size.width, size.height)
    options = [
        '-resize', dimensions,
        '-gravity', 'Center',
        '-crop', '{}+0+0'.format(dimensions), '+repage',
    ]
    cmd = ['convert', original_filename] + options + [new_filename]
    run_process_with_timeout(cmd, IMAGEMAGICK_PROCESS_TIMEOUT)


class TimeoutError(Exception):
    """
    Basic Exception to raise when a timeout has occurred
    """


def run_process_with_timeout(command, timeout):
    """
    Run a command with a timeout after which it will be killed.
    Args:
        command (list(str)): The command and arguments to be run
        timeout (int): Number of seconds we will allow the process to run
    Raises:
        CalledProcessError if there was an error during execution, or a
        TimeoutError if the process takes longer than the timeout arg.
    """
    p = subprocess.Popen(command)
    start = time.time()
    while True:
        if p.poll() is not None:
            break
        time_elapsed = time.time() - start
        if timeout and time_elapsed > timeout:
            p.terminate()
            raise TimeoutError()
        time.sleep(0.1)
    if p.returncode != 0:
        raise subprocess.CalledProcessError(p.returncode, command[0])


# ------------- #
# FILE HANDLING #
# ------------- #


def remove_uploaded_file(filename, upload_dir):
    os.remove(os.path.join(upload_dir, filename))


def remove_athlete_images(athlete):
    """
    This should only be used when an athlete record is to be deleted.
    When an athlete's bio image is changed, the file is overwritten because its filename never changes.
    """
    for size in ATHLETE_IMAGE_SIZES:
        remove_uploaded_file(
            RESIZED_FILENAME_JPG_FORMAT.format(athlete.id, size.name),
            app.config['ATHLETE_IMAGE_UPLOAD_FOLDER']
        )


def save_uploaded_image(image_file, upload_dir, new_filename=None, sizes=frozenset()):
    """
    Saves given image file locally

    :type image_file: werkzeug.datastructures.FileStorage
    :return: the filename of the saved image or the filename prefix of saved resized images
    """
    if not image_file:
        return

    filename = secure_filename(new_filename or image_file.filename)

    if sizes:
        filename_no_ext = os.path.splitext(filename)[0]
        with NamedTemporaryFile() as fp:
            image_file.seek(0)
            fp.write(image_file.read())
            fp.flush()  # write out any data that lingers in a program buffer
            for size in sizes:
                formatted = RESIZED_FILENAME_JPG_FORMAT.format(filename_no_ext, size.name)
                resize_image(fp.name, os.path.join(upload_dir, formatted), size)
        image_file.close()
        return filename_no_ext

    image_file.save(os.path.join(upload_dir, filename))
    image_file.close()
    return filename


def save_athlete_images(athlete_id, image_file):
    return save_uploaded_image(
        image_file,
        app.config['ATHLETE_IMAGE_UPLOAD_FOLDER'],
        str(athlete_id),
        ATHLETE_IMAGE_SIZES
    )


def save_article_image(image_file):
    return save_uploaded_image(
        image_file,
        app.config['ARTICLE_IMAGE_UPLOAD_FOLDER'],
    )


# --------- #
# RETRIEVAL #
# --------- #


def get_fail_gif_random():
    return FAIL_GIFS[random.randrange(len(FAIL_GIFS))]


def get_bylaws():
    with open(app.config['BASE_DIR'] + '/metropolitanweightlifting/static/json/bylaws.json', 'r') as fp:
        return json.load(fp, object_pairs_hook=LastUpdatedOrderedDict)


def get_weight_class(gender, body_weight):
    for wc in WEIGHT_CLASSES[gender][:-2]:
        if body_weight > int(wc):
            continue
        return wc
    return WEIGHT_CLASSES[gender][-1]


def get_image_dimensions(image_src, file_dir):
    filename = os.path.join(file_dir, image_src)
    cmd = ['identify', '-format', '%w %h', filename]
    w_h = subprocess.check_output(cmd).split()
    return w_h[0], w_h[1]


def get_video_source(data):
    if 'src="' not in data:
        return data
    return re.search(r'(?<=src=\")(.*?)(?=\")', data).group()


def get_meet_dict_from_csv(csv_file):
    """
    Converts a csv file of meet information into a usable dict

    File format:

    sanction number (containing 6 numbers; http://www.teamusa.org/usa-weightlifting/resources/all-meet-results)
    name
    date (human readable)
    city, state
    (0) lot number, (1) gender, (2) member id, (3) division, (4) weight class, (5) name, (6) year of birth, \
        (7) team, (8) body weight, (9) snatch 1, (10) 2, (11) 3, (12) best, \
        (13) clean and jerk 1, (14) 2, (15) 3, (16) best, (17) total, (18) place
    ...

    NOTE: after 'city, state', empty lines are allowed

    :param csv_file: comma-separated values file
    :return: a dictionary representing a single meet
    """
    csv_file.seek(0)
    meet_info = dict()
    # sanction number
    meet_info['sanction_number'] = re.sub('\D', '', csv_file.readline().strip())
    if len(meet_info['sanction_number']) != SANCTION_NUMBER_DIGITS:
        raise Exception("Invalid sanction number.")
    # name
    meet_info['name'] = csv_file.readline().rstrip()
    # date
    date_line = csv_file.readline().rstrip()
    cal = parsedatetime.Calendar()
    time_struct, parse_status = cal.parse(date_line)
    if parse_status != 1:
        raise Exception("Unable to parse date from: %s" % date_line)
    d = datetime.fromtimestamp(mktime(time_struct))
    meet_info['date'] = date(d.year, d.month, d.day)
    # d = [int(i) for i in csv_file.readline().rstrip().split('-')]
    # try:
    #     meet_info['date'] = date(d[0], d[1], d[2])
    # except IndexError:
    #     raise Exception("Invalid date format: %s" % meet_info['date'])
    # ===========
    # city, state
    location = csv_file.readline().split(',')
    meet_info['city'] = location[0].title()
    meet_info['state'] = location[1].upper().strip()
    # results
    meet_info['results'] = list()
    for line in csv_file:
        result = line.split(',')
        result_length = len(filter(lambda r: bool(r.strip()), result))
        if result_length:  # if not an empty line (,,,)
            try:
                if result[1].lower() not in ['m', 'f']:
                    raise Exception("Invalid gender '%s' (not 'm' or 'f') in line: '%s'" % (result[1], line))
                if result[4] not in WEIGHT_CLASSES['m'] and  \
                   result[4] not in WEIGHT_CLASSES['f']:
                    raise Exception("Invalid weight class '%s' in line: '%s'" % (result[4], line))
                meet_info['results'].append({
                    'gender': result[1].lower(),
                    'member_id': result[2],
                    'weight_class': result[4],
                    'name': result[5].title(),
                    'body_weight': float(result[8]),
                    'snatch_1': int(result[9]),
                    'snatch_2': int(result[10]),
                    'snatch_3': int(result[11]),
                    'snatch_best': int(result[12]),
                    'clean_jerk_1': int(result[13]),
                    'clean_jerk_2': int(result[14]),
                    'clean_jerk_3': int(result[15]),
                    'clean_jerk_best': int(result[16]),
                    'total': int(result[17]),
                    'place': normalize_place(result[18])
                })
            except IndexError:
                raise Exception("Missing item in line: '%s'" % line)
    return meet_info


def get_formatted_meet_results(meet_results):
    formatted_results = dict()
    for result in meet_results:
        if result.gender not in formatted_results:
            formatted_results[result.gender] = dict()
        if result.weight_class not in formatted_results[result.gender]:
            formatted_results[result.gender][result.weight_class] = list()
        formatted_results[result.gender][result.weight_class].append({
            'name': result.name,
            'body_weight': result.body_weight,
            'snatch_1': result.snatch_1,
            'snatch_2': result.snatch_2,
            'snatch_3': result.snatch_3,
            'snatch_best': result.snatch_best,
            'clean_jerk_1': result.clean_jerk_1,
            'clean_jerk_2': result.clean_jerk_2,
            'clean_jerk_3': result.clean_jerk_3,
            'clean_jerk_best': result.clean_jerk_best,
            'total': result.total,
            'place': result.place,
        })
    for gender, _ in formatted_results.iteritems():
        formatted_results[gender] = OrderedDict(
            sorted(
                formatted_results[gender].items(),
                key=lambda wc_r: int(wc_r[0].replace('+', '0'))  # int(re.sub(r'\D', '', wc_res[0]))
            )
        )
        for weight_class, rankings in formatted_results[gender].iteritems():
            formatted_results[gender][weight_class].sort(key=lambda i: i['place'])

    return formatted_results
