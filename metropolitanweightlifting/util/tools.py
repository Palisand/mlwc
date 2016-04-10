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

ALLOWED_EXCEL_SUBTYPES = frozenset(('vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'vnd.ms-excel'))
ALLOWED_EXCEL_MIMETYPES = frozenset('/'.join(('application', st)) for st in ALLOWED_EXCEL_SUBTYPES)

ALLOWED_IMAGE_SUBTYPES = frozenset(('png', 'jpeg'))
ALLOWED_IMAGE_MIMETYPES = frozenset('/'.join(('image', st)) for st in ALLOWED_IMAGE_SUBTYPES)

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

RESULT_LENGTH = 19
PLACE_TO_DBVAL = {
    'EXTRA': 998,
    '': 999,
}
WEIGHT_CLASSES = {
    'm': ['56', '62', '69', '77', '85', '94', '105', '105+'],
    'f': ['48', '53', '58', '63', '69', '75', '75+'],
}
MeetAttr = namedtuple('MeetAttr', ['name', 'row', 'column_range'])
MEET_ATTR_SANCTION_NUMBER = MeetAttr('Sanction Number', 11, range(13, 20))
MEET_ATTR_NAME = MeetAttr('Competition Name', 10, range(4, 10))
MEET_ATTR_DATE = MeetAttr('Date', 11, range(4, 6))
MEET_ATTR_LOCATION = MeetAttr('Location', 10, range(15, 20))
SANCTION_NUMBER_DIGITS = 9
DATE_STRING_FORMAT = "%Y-%m-%d"
MEET_RESULTS_ROW_RANGE = range(15, 36)


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


def allowed_excel_type(excel_file):
    return excel_file.mimetype in ALLOWED_EXCEL_MIMETYPES


def can_wrap_text(image):
    """
    This may be subject to change...
    """
    return image.width <= image.height


# ---------- #
# PROCESSING #
# ---------- #

def normalize_place(raw):
    """
    A valid place is "EXTRA", "", or a positive integer.
    """
    if isinstance(raw, float):
        if raw > 0:
            return int(raw)
    elif raw.upper() == "EXTRA" or raw == "":
        return PLACE_TO_DBVAL[raw.upper().strip()]
    raise Exception("Invalid place '%s'." % raw)


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


def save_uploaded_pdf(pdf_file):
    if not pdf_file:
        return

    filename = secure_filename(pdf_file.filename)
    pdf_file.save(os.path.join(app.config['PDF_UPLOAD_FOLDER'], filename))
    pdf_file.close()
    return filename


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


def get_meet_attribute_value(meet_attr, sheet):
    for col in meet_attr.column_range:
        value = sheet[meet_attr.row, col]
        if value:
            if isinstance(value, basestring) and not value.strip():  # in case of white space str
                continue
            else:
                return value
    raise Exception("%s not found." % meet_attr.name)


def get_meet_dict_from_excel_sheet(sheet):
    """
    Converts an excel file of meet information into a usable dict

    :type sheet: pyexcel.Sheet
    :return:
    """
    meet_info = dict()
    # sanction number
    sanction_number = get_meet_attribute_value(MEET_ATTR_SANCTION_NUMBER, sheet).replace('-', '')
    if len(sanction_number) == SANCTION_NUMBER_DIGITS:
        meet_info['sanction_number'] = sanction_number
    else:
        raise Exception("Invalid sanction number '%s'." % sanction_number)
    # name
    meet_info['name'] = get_meet_attribute_value(MEET_ATTR_NAME, sheet)
    # date
    meet_date = get_meet_attribute_value(MEET_ATTR_DATE, sheet)
    if isinstance(meet_date, date):
        meet_info['date'] = get_meet_attribute_value(MEET_ATTR_DATE, sheet)
    else:
        raise Exception("Date '%s' is not an Excel date type." % meet_date)
    # location
    try:
        location_raw = get_meet_attribute_value(MEET_ATTR_LOCATION, sheet)
        location = location_raw.split(",")
        assert(len(location) == 2)
    except (AttributeError, AssertionError) as e:
        raise Exception("Incorrect formatting for meet location '%s', "
                        "please use 'city, state' in a single Excel cell." % location_raw)
    else:
        meet_info['city'] = location[0].strip().title()
        meet_info['state'] = location[1].strip().upper()  # Assuming 'NY' format
    # results
    meet_info['results'] = list()
    for row_num in MEET_RESULTS_ROW_RANGE:
        row = sheet.row[row_num]
        if row[0]:  # if value for Lot No.
            try:
                # gender check
                if row[1].lower() not in ['m', 'f']:
                    raise Exception("Invalid gender value '%s' (not 'm' or 'f')" % row[1])
                # weight class check
                weight_class = str(int(row[4])) if isinstance(row[4], float) else str(row[4])
                if weight_class not in WEIGHT_CLASSES['m'] and \
                   weight_class not in WEIGHT_CLASSES['f']:
                    raise Exception("Invalid weight class '%s'" % weight_class)
                # add result data
                meet_info['results'].append({
                    'gender': row[1].lower(),
                    'member_id': int(row[2]),
                    'weight_class': weight_class,
                    'name': row[5].title(),
                    'body_weight': float(row[8]),
                    'snatch_1': int(row[9]),
                    'snatch_2': int(row[10]),
                    'snatch_3': int(row[11]),
                    'snatch_best': int(row[12]),
                    'clean_jerk_1': int(row[13]),
                    'clean_jerk_2': int(row[14]),
                    'clean_jerk_3': int(row[15]),
                    'clean_jerk_best': int(row[16]),
                    'total': int(row[17]),
                    'place': normalize_place(row[18])
                })
            except IndexError:
                raise Exception("Missing item in row %s" % (row_num + 1))
            except Exception as e:
                raise Exception("Error in row %s: %s" % (row_num + 1, e))
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
