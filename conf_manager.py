import pymongo
import collections
import sys
import glob
from datetime import datetime


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


def add_conferences(db, table_name):
    def derive_gmap_url(place_name):
        unpacked = place_name.split(' ')
        loc_str = '+'.join(unpacked)
        return "https://www.google.co.uk/maps/search/{name}".format(name=loc_str)

    cur_date = datetime.now().date()
    conf_table = db[table_name]
    required_fields = ['Name', 'Place Name', 'Gmaps URL', 'Start Date', 'End Date', 'URL Label', 'URL',
                       'Abstract Deadline', 'Registration Deadline', 'XCS Attending', 'Date Added']
    auto_fields = ['Gmaps URL', 'Date Added']
    create_entry = True
    while create_entry:
        print('New Conference Entry')
        internal_dict = collections.OrderedDict()
        for i in range(len(required_fields)):
            if required_fields[i] not in auto_fields:
                internal_dict[required_fields[i]] = input(required_fields[i] + ': ')
            elif required_fields[i] in auto_fields:
                internal_dict['Gmaps URL'] = derive_gmap_url(internal_dict['Place Name'])
                internal_dict['Date Added'] = cur_date.strftime("%d/%m/%y")

        more_fields = str(input('Add more fields(y/n): ')).lower()
        while more_fields == 'y':
            field_name = str(input('Field name: '))
            field_data = input('Field value: ')
            internal_dict[field_name] = field_data
            more_fields = str(input('Add more fields(y/n): ')).lower()

        submit = str(input('Save this entry(y/n): '))
        if submit.lower() == 'y':
            conf_table.insert_one(internal_dict)
        elif submit.lower() == 'n':
            print('Entry Discarded')
        print('')
        more_entries = str(input('Add another record(y/n): ')).lower()
        print('')
        if more_entries == 'n':
            create_entry = False
        elif more_entries != 'y':
            print('YOU FUCKED UP')
            sys.exit(0)


def generate_out_file(db, table_names):
    def format_entry(record):
        if group == 'xcs':
            template = "*'''{Name}:'''\n" \
                       "-->Location: ([[{GmapsURL}| {PlaceName}]])\n" \
                       "-->Date: {FormattedDate}\n" \
                       "-->URL: [[{URL}| {URLLabel}]]\n" \
                       "-->Abstract Deadline: {ABDEAD}\n" \
                       "-->Registration Deadline: {REGDEAD}\n"\
                       "-->XCS Members Attending: {members}\n"
        elif group == 'des':
            template = "*'''{Name}:'''\n" \
                       "-->Location: ([[{GmapsURL}| {PlaceName}]])\n" \
                       "-->Date: {FormattedDate}\n" \
                       "-->URL: [[{URL}| {URLLabel}]]\n" \
                       "-->Abstract Deadline: {ABDEAD}\n" \
                       "-->Registration Deadline: {REGDEAD}\n"

        if record['Start Date'].month != record['End Date'].month:
            formatted_date = record['Start Date'].strftime("%B") + ' ' + record['Start Date'].strftime('%d') + '-' \
                             + record['End Date'].strftime("%B") + ' ' + record['End Date'].strftime('%d') + ' ' \
                             + record['Start Date'].strftime('%Y')
        else:
            formatted_date = record['Start Date'].strftime("%B") + ' ' + record['Start Date'].strftime('%d') + '-' \
                             + record['End Date'].strftime('%d') + ' ' + record['Start Date'].strftime('%Y')

        try:
            form_abs = record['Abstract Deadline'].strftime('%d/%m/%y')
        except AttributeError:
            form_abs = ''

        try:
            form_reg = record['Registration Deadline'].strftime('%d/%m/%y')
        except AttributeError:
            form_reg = ''

        if group == 'xcs':
            return template.format(Name=record['Name'], GmapsURL=record['Gmaps URL'], PlaceName=record['Place Name'],
                               FormattedDate=formatted_date, URL=record['URL'], URLLabel=record['URL Label'],
                               ABDEAD=form_abs, REGDEAD=form_reg, members=record['XCS Attending'])
        if group == 'des':
            return template.format(Name=record['Name'], GmapsURL=record['Gmaps URL'], PlaceName=record['Place Name'],
                                   FormattedDate=formatted_date, URL=record['URL'], URLLabel=record['URL Label'],
                                   ABDEAD=form_abs, REGDEAD=form_reg)

    def this_month(confs):
        month_string = "'''Added in " + cur_date.strftime('%B') + ' ' + cur_date.strftime('%Y') + ":'''\n\n"
        for conf in confs:
            if conf['Date Added'].month == cur_date.month and conf['Date Added'].year == cur_date.year:
                month_string = month_string + format_entry(conf) + '\n'

        return month_string

    def closing_soon(confs):
        closing_string = "'''Abstracts/Registration Closing Soon:'''\n\n"
        for conf in confs:
            soon = False
            try:
                abs_diff = (conf['Abstract Deadline'] - cur_date).days
                if 0 < abs_diff <= 30:
                    soon = True
            except TypeError:
                pass

            try:
                reg_diff = (conf['Registration Deadline'] - cur_date).days
                if 0 < reg_diff <= 30:
                    soon = True
            except TypeError:
                pass
            if soon:
                closing_string = closing_string + format_entry(conf) + '\n'

        return closing_string

    def ab_reg_open(confs):
        open_string = "'''Still open for Abstract and Registration:'''\n\n"
        for conf in confs:
            abs_open = False
            reg_open = False

            try:
                if (conf['Start Date'] - cur_date).days < 0:
                    happened = True
                else:
                    happened = False
            except TypeError:
                happened = False
            try:
                abs_diff = (conf['Abstract Deadline'] - cur_date).days
                if abs_diff > 30:
                    abs_open = True
            except TypeError:
                if conf['Abstract Deadline'] == '':
                    abs_open = False
            try:
                reg_diff = (conf['Registration Deadline'] - cur_date).days
                if reg_diff > 30:
                    reg_open = True
            except TypeError:
                if conf['Registration Deadline'] == '':
                    reg_open = False

            if abs_open and reg_open and not happened:
                open_string = open_string + format_entry(conf) + '\n'

        return open_string

    def no_ab_reg(confs):
        dateless_string = "'''No abstract or registration deadlines:'''\n\n"
        for conf in confs:
            no_reg = False
            no_abs = False

            try:
                if (conf['Start Date'] - cur_date).days < 0:
                    happened = True
                else:
                    happened = False
            except TypeError:
                happened = False

            if conf['Abstract Deadline'] == '' or conf['Abstract Deadline'] == 'TBA':
                no_abs = True

            if conf['Registration Deadline'] == '' or conf['Registration Deadline'] == 'TBA':
                no_reg = True

            if no_reg and no_abs and not happened:
                dateless_string = dateless_string + format_entry(conf) + '\n'

        return dateless_string

    def reg_open(confs):
        open_string = "'''Still open for Registration but Abstract Deadline has passed:'''\n\n"
        for conf in confs:
            abs_open = False
            abs_empty = False
            reg_open = False
            reg_empty = False

            try:
                if (conf['Start Date'] - cur_date).days < 0:
                    happened = True
                else:
                    happened = False
            except TypeError:
                happened = False
            try:
                abs_diff = (conf['Abstract Deadline'] - cur_date).days
                if 0 < abs_diff:
                    abs_open = True
            except TypeError:
                if conf['Abstract Deadline'] == '':
                    abs_open = True
                    abs_empty = True
            try:
                reg_diff = (conf['Registration Deadline'] - cur_date).days
                if 0 < reg_diff:
                    reg_open = True
            except TypeError:
                if conf['Registration Deadline'] == '':
                    reg_open = True
                    reg_empty = True

            allowed = True
            if reg_empty and abs_empty:
                allowed = False

            if not abs_open and reg_open and not happened and allowed:
                open_string = open_string + format_entry(conf) + '\n'

        return open_string

    def ab_reg_clsd_future_(confs):
        open_string = "'''Conferences not yet occurred but both Registration and Abstract Deadline has passed:'''\n\n"
        for conf in confs:
            abs_open = False
            reg_open = False
            try:
                if (conf['Start Date'] - cur_date).days < 0:
                    happened = True
                else:
                    happened = False
            except TypeError:
                happened = False
            try:
                abs_diff = (conf['Abstract Deadline'] - cur_date).days
                if 0 < abs_diff:
                    abs_open = True
            except TypeError:
                abs_open = True
            try:
                reg_diff = (conf['Registration Deadline'] - cur_date).days
                if 0 < reg_diff:
                    reg_open = True
            except TypeError:
                reg_open = True

            if not abs_open and not reg_open and not happened:
                open_string = open_string + format_entry(conf) + '\n'

        return open_string

    def past(confs):
        past_string = "'''The archive of past conferences:'''\n\n"
        for conf in confs:
            try:
                if (conf['Start Date'] - cur_date).days < 0:
                    happened = True
                else:
                    happened = False
            except TypeError:
                happened = False

            if happened:
                past_string = past_string + format_entry(conf) + '\n'

        return past_string

    def gather_sections(confs):
        if group == 'xcs':
            init_string = "'''Conference announcements'''\n" \
                          "For contributions, please go to [[TalksArchive | this page]]\n\n" \
                          "To see what other conferences are coming up, [[http://www1.cadc-ccda.hia-iha.nrc-cnrc.gc.ca/en/meetings/| this page ]] is a good resource.\n\n" \
                          "-----\n\n" \
                          "'''DES version of the conference list'''\n" \
                          "(Remember to refresh page on the DES_FILE as your browser will use a cached copy otherwise!)\n\n" \
                          "[[ https://www.acru.ukzn.ac.za/~xcs/wiki/uploads/Restricted/ConferencePlussList/DES_FILE | DES_FILE ]]\n\n" \
                          "[[ https://www.acru.ukzn.ac.za/~xcs/wiki/index.php/Restricted/ConferencePlussList?action=upload | To Change DES_FILE ]]\n\n" \
                          "-----\n\n"\
                          "'''If you are attending any of these conferences, or spot an issue with this page, EMAIL ME at david.turner@sussex.ac.uk'''\n\n" \
                          "-----\n\n"
            dat_list = [this_month(confs), closing_soon(confs), ab_reg_open(confs), reg_open(confs), no_ab_reg(confs),
                        ab_reg_clsd_future_(confs), past(confs)]
            dat_string = init_string + '\n'.join(dat_list)

        elif group == 'des':
            init_string = "*Please email me at david.turner@sussex.ac.uk if you spot any problems with this page.* \n\n"
            dat_list = [this_month(confs), closing_soon(confs), ab_reg_open(confs), reg_open(confs), no_ab_reg(confs),
                        ab_reg_clsd_future_(confs)]
            dat_string = init_string + '\n'.join(dat_list)

        return dat_string

    cur_date = datetime.now().date()
    all_conf = []
    for tab in table_names:
        conf_table = db[tab]
        result = conf_table.find()

        for record in result:
            record['Start Date'] = datetime.strptime(record['Start Date'], "%d/%m/%y").date()
            record['End Date'] = datetime.strptime(record['End Date'], "%d/%m/%y").date()
            record['Date Added'] = datetime.strptime(record['Date Added'], "%d/%m/%y").date()
            if record['Abstract Deadline'] != '' and record['Abstract Deadline'] != 'TBA':
                record['Abstract Deadline'] = datetime.strptime(record['Abstract Deadline'], "%d/%m/%y").date()

            if record['Registration Deadline'] and record['Registration Deadline'] != 'TBA':
                record['Registration Deadline'] = datetime.strptime(record['Registration Deadline'], "%d/%m/%y").date()
            all_conf.append(record)

    with open('generated_lists/xcs_conference_list_{date}.txt'.format(date=cur_date.strftime('%d%m%y')), 'w') as xcs_conf:
        group = 'xcs'
        xcs_conf.writelines(gather_sections(all_conf))
    xcs_conf.close()

    with open('generated_lists/des_conference_list_{date}.txt'.format(date=cur_date.strftime('%d%m%y')), 'w') as des_conf:
        group = 'des'
        des_conf.writelines(gather_sections(all_conf))
    des_conf.close()

    write_des_out(cur_date)


def write_des_out(cur_date):
    with open('generated_lists/des_conference_list_{date}.txt'.format(date=cur_date.strftime('%d%m%y'))) as afile:
        contents = afile.readlines()
    afile.close()

    def xcs_to_des(oneline):
        # print("0", line)
        if oneline.find("[[") != -1:
            start = oneline.find("[[")
            end = oneline.find("]]")
            middle = oneline.find('|')
            new_line = oneline[0:start].replace("(", "") + " \"" + oneline[middle + 1:end] + "\":" + oneline[
                                                                                               start + 2:middle].replace(
                " ", "") + "\n"
            # print("1",new_line)
            oneline = new_line
        oneline = oneline.replace("*", '* ')
        oneline = oneline.replace("-->", "** ")
        oneline = oneline.replace("''' ", '*')
        oneline = oneline.replace("'''", "*")
        return oneline

    with open('generated_lists/des_conference_list_{date}.txt'.format(date=cur_date.strftime('%d%m%y')), "w+") as outfile:
        for line in contents:
            outfile.write(xcs_to_des(line))


if __name__ == "__main__":
    the_db = init_db(db_name='ConferenceManager')
    #read_legacy_conf(the_db)
    add_conferences(db=the_db, table_name='Conferences')  # Conferences table contains entries from conf_manager.py
    generate_out_file(db=the_db, table_names=['LegacyConferences', 'Conferences'])




