from metropolitanweightlifting import app

import datetime
import strict_rfc3339
from tools import (
    PLACE_TO_DBVAL,
    markdown_to_html,
)

MAX_WRAPPED_IMAGE_WIDTH = 300


@app.template_filter('human_uDate')
def human_readable_date(unicode_date, str_format):
    normalized = str(unicode_date)
    dtime = datetime.datetime.strptime(normalized, "%Y-%m-%d").date()
    return dtime.strftime(str_format)


@app.template_filter('human_rfc3339')
def human_readable_rfc3339(rfc3339, str_format):
    normalized = str(rfc3339)
    timestamp = strict_rfc3339.rfc3339_to_timestamp(normalized)
    dtime = datetime.datetime.fromtimestamp(timestamp)
    return dtime.strftime(str_format)


@app.template_filter('human_place')
def human_readable_meet_place(value):
    dbval_to_place = {v: k for k, v in PLACE_TO_DBVAL.iteritems()}
    return dbval_to_place.get(value, value)


@app.template_filter('wrapped_image_width')
def wrapped_image_width(image):
    if image.article.wrap_text:
        return min(MAX_WRAPPED_IMAGE_WIDTH, image.width)
    return image.width


@app.template_filter('markup')
def markup(text):
    return markdown_to_html(text)
