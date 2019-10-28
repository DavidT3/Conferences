import pymongo
import collections
import glob


def init_db(db_name):
    """
    Defines a database client and object, creates a new db if one does not already exist.
    :param db_name:
    :return:
    """

    db_client = pymongo.MongoClient("mongodb+srv://test:test123@xcs-cluster0-vokke.mongodb.net/test?retryWrites=true")
    conf_db = db_client[db_name]
    return conf_db


def read_legacy_conf(db):
    def parse_name(int_dict, first_line):
        nam = first_line.split("'''")[1].split(':')[0]
        if nam[0] == ' ':
            nam = nam[1:len(nam)]
        if nam[-1] == ' ':
            nam = nam[0:len(nam)-1]

        int_dict['Name'] = nam
        return int_dict

    def parse_loc(int_dict, f_name, data):
        unpacked = data.split('[[')
        if '[[' in data:
            place = unpacked[0]
            if place[0] == ' ':
                place = place[1:]
            if place == '(':
                place = ''
            if '(' in place:
                place = place.split('(')[0]

            gmaps = unpacked[1].split('|')[0]
            if gmaps[0] == ' ':
                gmaps = gmaps[1:]
        else:
            place = unpacked[0]
            gmaps = ''
        int_dict['Place Name'] = place
        int_dict['Gmaps URL'] = gmaps
        return int_dict

    def parse_url(int_dict, f_name, data):
        unpacked = data.split('|')
        url = unpacked[0].split('[[')[1]
        label = unpacked[1].split(']]')[0]
        if url[0] == ' ':
            url = url[1:]
        if url[-1] == ' ':
            url = url[:-1]
        if label[0] == ' ':
            label = label[1:]
        if label[-1] == ' ':
            label = label[:-1]
        int_dict['URL Label'] = label
        int_dict['URL'] = url
        return int_dict

    def parse_conf_date(int_dict, f_name, data):
        months = ['Jan', 'January', 'Feb', 'February', 'Mar', 'March', 'Apr', 'April', 'May', 'Jun', 'June', 'Jul',
                  'July', 'Aug', 'August', 'Sep', 'September', 'Oct', 'October', 'Nov', 'November', 'Dec', 'December']
        print(data)
        if f_name == 'Date':
            start = input('What is the start date (dd/mm/yy): ')
            end = input('What is the end date (dd/mm/yy): ')
            int_dict['Start Date'] = start
            int_dict['End Date'] = end
        elif f_name == 'Abstract Deadline' or f_name == 'Registration Deadline':
            print(f_name)
            date = input('What is the date: ')
            int_dict[f_name] = date
            print('')
        return int_dict

    def parse_general(a_line):
        line = a_line.split('-->')[1]
        field_name = line.split(':')[0]
        line_no_name = ':'.join(line.split(':')[1:])
        if len(line_no_name) != 0 and line_no_name[0] == ' ':
            line_no_name = line_no_name[1:]
        if len(field_name) != 0 and field_name[0] == ' ':
            field_name = line_no_name[1:]
        if len(field_name) != 0 and field_name[-1] == ' ':
            field_name = field_name[:-1]
        return field_name, line_no_name

    table = db['LegacyConferences']
    confs_present = []
    for doc in table.find():
        confs_present.append(doc['Name'])

    for file in glob.glob('legacy_conferences/added_*.txt'):
        with open(file, 'r') as added:
            lines = added.read()
        added.close()
        confs = [el.split('\n') for el in lines.split('\n\n')]
        for conf in confs:
            internal_dict = collections.OrderedDict()
            internal_dict = parse_name(internal_dict, conf[0])
            if internal_dict['Name'] not in confs_present:
                for i in range(1, len(conf)):
                    fld_name, raw_data = parse_general(conf[i])
                    if fld_name == "Location":
                        internal_dict = parse_loc(internal_dict, fld_name, raw_data)
                    if fld_name == "Date":
                        internal_dict = parse_conf_date(internal_dict, fld_name, raw_data)
                    if fld_name == "URL":
                        internal_dict = parse_url(internal_dict, fld_name, raw_data)
                    if fld_name == "Abstract Deadline":
                        internal_dict = parse_conf_date(internal_dict, fld_name, raw_data)
                    if fld_name == "Registration Deadline":
                        internal_dict = parse_conf_date(internal_dict, fld_name, raw_data)
                if "Abstract Deadline" not in internal_dict:
                    internal_dict["Abstract Deadline"] = ''
                if "Registration Deadline" not in internal_dict:
                    internal_dict["Registration Deadline"] = ''
                internal_dict['XCS Attending'] = ''
                internal_dict['Date Added'] = '01/01/18'
                for el in internal_dict:
                    print(el + ':', internal_dict[el])
                cont = input('Save this entry(y/n)?')
                if cont == 'y':
                    table.insert_one(internal_dict)
                elif cont == 'n':
                    print('fuck you')
                print('')