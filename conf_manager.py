import pymongo
import collections
import sys
import glob
from datetime import datetime
from string import ascii_lowercase as alphabet

des_working_groups = ["Clusters", "Galaxy Evolution (and AGN)", "Large-Scale Structure", "Milky Way", "Photo-z",
                      "Simulation", "Lensing", "Supernovae", "Theory", "Transients", "Gravitational Waves"]
allowed_keywords = ["Astronomy", "Astrophysics", "Cosmology", "School", "Workshop"]
section_order = {"General Astronomy/Astrophysics": ["Astrophysics", "Astronomy"], "General Cosmology": ["Cosmology"],
                 "Working Group Specific": des_working_groups, "Schools and Workshops": ["School", "Workshop"]}


def init_db(db_name):
    """
    Defines a database client and object, creates a new db if one does not already exist.
    :param db_name:
    :return:
    """

    db_client = pymongo.MongoClient("mongodb+srv://test:test123@xcs-cluster0-vokke.mongodb.net/test?retryWrites=true")
    conf_db = db_client[db_name]
    return conf_db


def add_conferences(db, table_name):
    def derive_gmap_url(place_name):
        unpacked = place_name.split(' ')
        loc_str = '+'.join(unpacked)
        return "https://www.google.co.uk/maps/search/{name}".format(name=loc_str)

    def new_entry(create_entry):
        print('New Conference Entry')
        internal_dict = collections.OrderedDict()
        internal_dict["Name"] = input("Name" + ': ')
        if internal_dict["Name"] not in conference_names:
            for field in required_fields:
                if field not in auto_fields and field not in fields_with_options.keys():
                    internal_dict[field] = input(field + ': ')
                elif field in auto_fields:
                    internal_dict['Gmaps URL'] = derive_gmap_url(internal_dict['Place Name'])
                    internal_dict['Date Added'] = cur_date.strftime("%d/%m/%y")
                elif field in fields_with_options.keys():
                    print('')
                    for ind, option in enumerate(fields_with_options[field]):
                        print('\x1b[0;30;41m {ind}) {choice} \x1b[0m'.format(ind=ind, choice=option))
                    selections = input("Select {} option(s) (using numbers separated by commas): ".format(field))

                    try:
                        selections = [int(elem.strip(" ")) for elem in selections.split(",")]
                    except ValueError:
                        print("You must select at least one option!\n")
                        return

                    try:
                        internal_dict[field] = list(map(lambda x: fields_with_options[field][x], selections))
                    except IndexError:
                        print("Invalid selection, try again!\n")
                        return
            try:
                start = datetime.strptime(internal_dict["Start Date"], "%d/%m/%y")
                end = datetime.strptime(internal_dict["End Date"], "%d/%m/%y")
                if internal_dict["Abstract Deadline"] != "":
                    datetime.strptime(internal_dict["Abstract Deadline"], "%d/%m/%y")
                if internal_dict["Registration Deadline"] != "":
                    datetime.strptime(internal_dict["Registration Deadline"], "%d/%m/%y")
            except ValueError:
                print("One of the dates you entered is in the wrong format! Use dd/mm/yy (e.g. 25/12/19)!\n")
                return

            if start > end:
                print("Conferences cannot end before they begin!\n")
                return
            elif start.date() < cur_date:
                print("Conferences cannot start before the current date!\n")
                return


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
        else:
            print('\nTHIS CONFERENCE NAME ALREADY EXISTS, PLEASE TRY AGAIN!\n')
        return create_entry

    cur_date = datetime.now().date()
    conf_table = db[table_name]
    conference_names = [record['Name'] for record in conf_table.find()]
    required_fields = ['Place Name', "Working Group(s)", "Keyword(s)", 'Gmaps URL', 'Start Date', 'End Date',
                       'URL Label', 'URL', 'Abstract Deadline', 'Registration Deadline', 'XCS Attending', 'Date Added']
    auto_fields = ['Gmaps URL', 'Date Added']
    fields_with_options = {"Working Group(s)": des_working_groups, "Keyword(s)": allowed_keywords}

    create_entry_flag = True
    while create_entry_flag:
        create_entry_flag = new_entry(create_entry_flag)
        if create_entry_flag is None:
            create_entry_flag = True


def move_past_conferences(db, from_table, to_table):
    cur_date = datetime.now().date()
    happened = [entry for entry in db[from_table].find()
                if (datetime.strptime(entry['Start Date'], "%d/%m/%y").date() - cur_date).days < 0]
    if len(happened) > 0:
        db[to_table].bulk_write([pymongo.InsertOne(entry) for entry in happened])
        in_to_table = list(filter(None, [db[to_table].find_one(entry) for entry in happened]))
        db[from_table].bulk_write([pymongo.DeleteOne(entry) for entry in in_to_table])

        if in_to_table != happened:
            print("For some reason some documents have not been moved to the past conferences table!")


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
            template = "* *{Name}:*\n" \
                       "** Location: \"{PlaceName}\":{GmapsURL}\n" \
                       "** Date: {FormattedDate}\n" \
                       "** URL: \"{URLLabel}\":{URL}\n" \
                       "** Abstract Deadline: {ABDEAD}\n" \
                       "** Registration Deadline: {REGDEAD}\n"

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

        expec = ['_id', 'Name', 'Gmaps URL', 'Place Name', 'URL', 'URL Label', 'Abstract Deadline',
                 'Registration Deadline', 'Start Date', 'End Date', 'XCS Attending', 'Date Added']
        no_print = ["Working Group(s)"]
        if group == 'xcs':
            entry = template.format(Name=record['Name'], GmapsURL=record['Gmaps URL'], PlaceName=record['Place Name'],
                                    FormattedDate=formatted_date, URL=record['URL'], URLLabel=record['URL Label'],
                                    ABDEAD=form_abs, REGDEAD=form_reg, members=record['XCS Attending'])
            for rec in record:
                if rec not in expec and rec not in no_print:
                    entry += "-->{fieldname}: {content}\n".format(fieldname=rec, content=record[rec])
            return entry

        if group == 'des':
            entry = template.format(Name=record['Name'], GmapsURL=record['Gmaps URL'], PlaceName=record['Place Name'],
                                    FormattedDate=formatted_date, URL=record['URL'], URLLabel=record['URL Label'],
                                    ABDEAD=form_abs, REGDEAD=form_reg)
            for rec in record:
                if rec not in expec and rec not in no_print:
                    entry += "** {fieldname}: {content}\n".format(fieldname=rec, content=record[rec])
            return entry

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

    def new_des_layout(confs):
        des_string = "h1. Conference List - Generated on {d}\n\n" \
                     "Please email me at david.turner@sussex.ac.uk " \
                     "if you spot any problems with this page. \n\n".format(d=cur_date.strftime("%d %B %Y"))
        des_string += "{{toc}}\n\n"
        header_string = "h{j}. {i}. {n}\n\n"
        for ind, section in enumerate(section_order):
            substring = header_string.format(j=2, i=ind+1, n=section)
            if section != "Working Group Specific":
                for entry in section_order[section]:
                    for conf in confs:
                        if entry in conf["Keyword(s)"]:
                            substring += format_entry(conf) + "\n"
            else:
                for sub_ind, wg in enumerate(section_order[section]):
                    sub_substring = header_string.format(j=3, i=str(ind+1)+alphabet[sub_ind], n=wg)
                    for conf in confs:
                        if wg in conf["Working Group(s)"]:
                            sub_substring += format_entry(conf) + "\n"
                    substring += sub_substring + "\n"
            des_string += substring

        return des_string

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
                        ab_reg_clsd_future_(confs)]
            dat_string = init_string + '\n'.join(dat_list)

        elif group == 'des':
            dat_string = new_des_layout(confs)
        return dat_string

    cur_date = datetime.now().date()
    xcs_conf_list = []
    des_conf_list = []
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

            record["Keyword(s)"] = ", ".join(record["Keyword(s)"])
            des_conf_list.append(record)
            if "Clusters" in record["Working Group(s)"]:
                xcs_conf_list.append(record)

    with open('generated_lists/xcs_conference_list_{date}.txt'.format(date=cur_date.strftime('%d%m%y')), 'w') as xcs_conf:
        group = 'xcs'
        xcs_conf.writelines(gather_sections(xcs_conf_list))
    xcs_conf.close()

    with open('generated_lists/des_conference_list_{date}.txt'.format(date=cur_date.strftime('%d%m%y')), 'w') as des_conf:
        group = 'des'
        des_conf.writelines(gather_sections(des_conf_list))
    des_conf.close()


def update_existing(db, table_name, conf_name=None):
    if conf_name is None:
        docs = db[table_name].find()
    else:
        docs = [db[table_name].find_one({"Name": conf_name})]

    for doc in docs:
        new_doc = doc.copy()
        for el in new_doc:
            if el != "_id":
                print(el, new_doc[el])
        print('')

        update_or_nah = input("Update or nah: ")
        if update_or_nah != "nah":
            field_to_update = input("Field Name: ")
            new_value = input("New value: ")
            print('')
            new_doc[field_to_update] = new_value
            db[table_name].update_one(doc, {"$set": new_doc}, upsert=False)


if __name__ == "__main__":
    the_db = init_db(db_name='ConferenceManager')
    # update_existing(the_db, "Conferences")
    add_conferences(db=the_db, table_name='tester')  # Conferences table contains entries from conf_manager.py
    move_past_conferences(the_db, "Conferences", "PastConferences")
    generate_out_file(db=the_db, table_names=['Conferences'])




