import pymongo
import collections
import sys


def init_db(db_name):
    """
    Defines a database client and object, creates a new db if one does not already exist.
    :param db_name:
    :return:
    """
    db_client = pymongo.MongoClient("mongodb://localhost:27017/")
    conf_db = db_client[db_name]
    return conf_db


def init_conf(db):
    return db['conferences']


def add_conferences(conf_col):
    required_fields = []

    create_entry = True
    while create_entry:
        print('')
        internal_dict = collections.OrderedDict()
        for i in range(len(required_fields)):
            internal_dict[required_fields[i]] = input(required_fields[i])

        more_fields = str(input('Add more fields(y/n): ')).lower()
        while more_fields == 'y':
            field_name = str(input('Field name: '))
            field_data = input('Field value: ')
            internal_dict[field_name] = field_data
            more_fields = str(input('Add more fields(y/n): ')).lower()

        conf_col.insert_one(internal_dict)

        more_entries = str(input('Add another conference entry(y/n): ')).lower()
        if more_entries == 'n':
            create_entry = False
        elif more_entries != 'y':
            print('YOU FUCKED UP')
            sys.exit(0)


def added_this_month():
    print('plchld')


def closing_soon():
    print('plchld')


def xcs_attending():
    print('plchld')


if __name__ == "__main__":
    the_db = init_db(db_name='conferences')
    the_col = init_conf(the_db)
    add_conferences(the_col)




