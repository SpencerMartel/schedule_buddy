import asyncio
import discord
from discord import Message
from discord.ext import tasks
import requests
from requests.models import HTTPBasicAuth
import json
import re
from Config.config import *

class_file = 'Data/Classes.json'
current_semesters_file = 'Data/CurrentSemesters.json'
prereqs_file = 'Data/Prereqs.json'
line = '---------------------------------------------'

# Current_semester_numbers and function will need to change every semester, get semester numbers from https://github.com/opendataConcordiaU/documentation/blob/master/v1/courses/schedule.md.
# TODO create mapping function to CurrentSemesters.json
current_semester_numbers = ['2221','2222','2223','2224']
def populate_current_semester_file(semesters_file, current_semester_numbers):
    file = open(semesters_file, 'w')
    semester_json = {}
    semester_json[current_semester_numbers[0]] = 'summer 2022'
    semester_json[current_semester_numbers[1]] = 'fall 2022'
    semester_json[current_semester_numbers[2]] = 'fall/winter 2022/23'
    semester_json[current_semester_numbers[3]] = 'winter 2023'
    semester_json_object = semester_json
    semester_json_string = json.dumps(semester_json_object,indent = 4, sort_keys=False)
    file.write(semester_json_string)
    file.close()
    return semester_json

# TODO Make this rely on CurrentSemesters file.
def queried_semester_number_str(user_message):
    if user_message[2].lower() == 'fall': # TODO  add or 'autumn', for some reason this breaks it?!?
        queried_semester_number = '2222'
    elif user_message[2].lower() == 'fall/winter':
        queried_semester_number = '2223'
    elif user_message[2].lower() == 'winter':
        queried_semester_number = '2224'
    elif user_message[2].lower() == 'summer':
        queried_semester_number = '2221'
    else:
        queried_semester_number = None
    return queried_semester_number

#Noice lil function to remove duplicate data sent from the API, also used to check which semesters a class is offered in.
def clean_duplicate_data(data_to_clean):
    print('Entering clean_duplicate_data function')
    clean_data = []
    for obj in data_to_clean:
        if clean_data.__contains__(obj):
            del obj
        else:
            obj_copy = obj.copy()
            clean_data.append(obj_copy)
    print('Data is cleaned (removed of duplicates)')
    return clean_data

# Get request and saving relevant semesters to Data/Classes.json
# Gets called upon the bot entering the server, and once a day in a task loop.
def fetch_and_save_classes(current_semester_numbers):
    print('Beginning fetch and save classes function')
    fetch_and_save_prereqs()
    auth = API_config['auth']
    r = requests.get('https://opendata.concordia.ca/API/v1/course/schedule/filter/*/*/*', auth = auth)
    input_json = list(json.loads(r.text))
    relevant_semesters = list(filter(lambda x: x['termCode'] in current_semester_numbers, input_json))
    clean_relevant_semesters = clean_duplicate_data(relevant_semesters)
    prereqs = load_prereqs()
    # Add prereqs to classes
    for classes in clean_relevant_semesters:
        for courses in prereqs:
            if classes['courseID'] == courses['ID']:
                classes['prerequisites'] = courses['prerequisites'].strip()
    output_json = json.dumps(clean_relevant_semesters, indent = 4)
    class_list = open(class_file, 'w' )
    class_list.write(output_json)
    class_list.close
    clear_prereqs()
    print('Daily class fetch has been completed')

# Data/Prereqs.json is a temporary storage to get the prereq info into Classes.json
def fetch_and_save_prereqs():
    print('Beginning fetch prereqs function')
    auth = API_config['auth']
    r = requests.get('https://opendata.concordia.ca/API/v1/course/catalog/filter/*/*/*', auth = auth)
    input_json = list(json.loads(r.text))
    clean_input_json = clean_duplicate_data(input_json)
    output_json = json.dumps(clean_input_json, indent = 4)
    prereq_list = open(prereqs_file, 'w' )
    prereq_list.write(output_json)
    prereq_list.close
    print("Finished fetch and save prereqs function")
    return

def load_classes():
    file = open(class_file, 'r')
    class_list = file.read()
    file.close()
    return json.loads(class_list)

def load_prereqs():
    file = open(prereqs_file, 'r')
    prereqs_list = file.read()
    file.close()
    return json.loads(prereqs_list)

def clear_prereqs():
    with open(prereqs_file, 'r+') as f:
        f.truncate(0)

def read_current_semester_file():
    file = open(current_semesters_file, 'r')
    current_semesters_json = file.read()
    file.close()
    return json.loads(current_semesters_json)

def grab_semester_list(queried_semester_number):
    semester_list_json = read_current_semester_file()
    for key, value in semester_list_json.items():
        if queried_semester_number == key:
            semester_list = [key,value]
            return semester_list

# Big ol function that lets the user know which semesters their queried course is offered in out of the ones the bot is looking at.
# Called if len(user_message) == 2 as in Geog 363
def check_semester_availability(class_list_json, queried_course, queried_number):
    print(line)
    course_title = get_course_name(class_list_json, queried_course, queried_number)
    if course_title == '':
        reply_string = f'**{queried_course.capitalize()} {queried_number}**  does not seem to exist, is there a typo or has concordia changed the course code?'
        return reply_string
    reply_string = f'**{queried_course.capitalize()} {queried_number}** -- **{course_title}** is offered in the following semesters:\n'
    semester_list = semester_availability_list(class_list_json, queried_course, queried_number)
    semester_string= ''
    for semesters in semester_list:
        semester_string += f'{semesters}'
    if semester_string == '':
        reply_string = f'**{queried_course.lower().capitalize()} {queried_number}** -- **{course_title}** is **not offered** in any semesters I am currently looking at :sob:'
    reply_string += semester_string
    reply_string += f'To view the sections offered each semester send another message with the following format:\n{queried_course.capitalize()} {queried_number} semester year'
    print(line,'\nThe bot is sending the following:\n', reply_string, '\n', line)
    return reply_string

# returns a list containing formatted string of semesters.
def semester_availability_list(class_list_json, queried_course, queried_number):
    working_data = []
    reply_string = ''
    reply_string_list = []
    for key in class_list_json:
        if (queried_course == key['subject'] and queried_number == key['catalog']) == True:
            dirty_list = grab_semester_list(key['termCode'])
            working_data.append(dirty_list)
    final_data = clean_duplicate_data(working_data)
    for key in final_data:
        clean_list = grab_semester_list(key[0])
        reply_string = f'\t• {clean_list[1].capitalize()}\n'
        reply_string_list.append(reply_string)
    return reply_string_list


def get_course_name(class_list_json, queried_course, queried_number):
    course_name = ''
    for key in class_list_json:
        if (queried_course == key['subject'] and queried_number == key['catalog']) == True:
            course_name += key['courseTitle'].title()
            break
    return course_name

def centering_func(subject, title, number, prereqs):
    object = grab_semester_list(number)
    backn = '\n'
    sending1 = '----------------------------------------------------------'
    sending2 = f'**{subject} --- {title}**'
    centered_sending2 = sending2.center(48)
    sending3 = f'{object[1].upper()} SEMESTER'
    centered_sending3 = sending3.center(len(sending1))
    sending_data = sending1 +backn +centered_sending2 + backn + centered_sending3 + backn + sending1 + backn
    return sending_data

def class_days(obj):
    class_occurance = []
    if obj['modays'] == 'Y':
        class_occurance.append('Mondays')
    if obj['tuesdays'] == 'Y':
        class_occurance.append('Tuesdays')
    if obj['wednesdays'] == 'Y':
        class_occurance.append('Wednesdays')
    if obj['thursdays'] == 'Y':
        class_occurance.append('Thursdays')
    if obj['fridays'] == 'Y':
        class_occurance.append('Fridays')
    if obj['saturdays'] == 'Y':
        class_occurance.append('Saturdays')
    if obj['sundays'] == 'Y':
        class_occurance.append('Sundays')
    class_occurance_string = listtostring(class_occurance)
    return class_occurance_string

# Used to format class days.
def listtostring(x):
    str = ' & '
    return (str.join(x))