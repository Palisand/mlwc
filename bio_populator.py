from metropolitanweightlifting import app, db
from metropolitanweightlifting.models import Athlete, MeetResult

from nameparser import HumanName


class Populator3000(object):

    @classmethod
    def populate(cls):

        for a in cls._gather_athletes():
            print a
            # athlete = Athlete(
            #     None,
            #     a['gender'],
            #     a['firstname'],
            #     a['lastname'],
            #     None,
            #     a['weight_class'],
            #     a['snatch'],
            #     a['clean_jerk'],
            #     None,
            #     has_photo=False
            # )
            # app.logger.info("Adding {} to database.".format(athlete))
            # db.session.add(athlete)
            # db.session.commit()

    @classmethod
    def _gather_athletes(cls):

        athletes = []

        results = MeetResult.query.all()

        # TODO: by result.member_id! check 'Student'
        for name in set([result.name for result in results]):
            hn = HumanName(name)
            athletes.append({
                'raw_name': name,
                'firstname': ' '.join((hn.title, hn.first, hn.middle)).strip(),
                'lastname': ' '.join((hn.last, hn.suffix)).strip(),
            })

        return athletes
        # meet results for names
            # by greatest snatch
            # by greatest clean & jerk


if __name__ == "__main__":
    Populator3000().populate()
