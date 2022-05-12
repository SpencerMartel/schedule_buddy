import asyncio
import discord
from discord import Message
from discord.ext import tasks
import requests
from requests.models import HTTPBasicAuth
import json
import re
import datetime
from datetime import datetime, timedelta
from Config.config import *

class_file = 'Data/Classes.json'
current_semesters_file = 'Data/CurrentSemesters.json'
prereqs_file = 'Data/Prereqs.json'
line = '---------------------------------------------'
client = discord.Client()
Token = str(discord_config["token"])
# this is the password for the bot to enter the discord server, you have to give it access to the server on the discord developer portal

# current_semester_numbers and function will need to change every semester, get semester numbers from https://github.com/opendataConcordiaU/documentation/blob/master/v1/courses/schedule.md.
# Check to see if link is still alive / proper.

# TODO create mapping function to CurrentSemesters.json
current_semester_numbers = ['2221','2222','2223','2224']
current_info_link = 'https://www.concordia.ca/academics/undergraduate/calendar.html'

def populate_current_semester_file(semesters_file, current_semester_numbers):
    file = open(semesters_file, 'w')
    semester_json = {}
    semester_json[current_semester_numbers[0]] = 'summer 2022'
    semester_json[current_semester_numbers[1]] = 'fall 2022'
    semester_json[current_semester_numbers[2]] = 'fall/winter 2022/23'
    semester_json[current_semester_numbers[3]] = 'winter 2023'
    semester_json_object = {'currentsemesters':semester_json}
    semester_json_string = json.dumps(semester_json_object,indent = 4, sort_keys=False)
    file.write(semester_json_string)
    file.close()
    return semester_json

# this client event lets us know we successfully connected to the server and have initialized Data/Classes.json with a fetch and CurrentSemesters.json with our function
@client.event
async def on_ready():
    print(line)
    print('We have logged in as {0.user}'.format(client))
    print(f'Ready to go!\n{line}')
    return

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------#
#---------------------------------------------------------------------------END OF DISCORD STUFF--------------------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------#

#this event is the meat and potatoes
@client.event
async def on_message(message):
    channel_check = message.channel.id in discord_config["channel_id"]
    if channel_check != True:
        return
    if message.author == client.user:
        return
    
    am = discord.AllowedMentions(users = False, everyone = False, roles = False, replied_user = True)
    author = str(message.author.id)
    class_list_json = load_classes()
    semester_list_json = read_current_semester_file()
    prereqs_list_json = load_prereqs()
    
    # help message prompt
    if message.content.lower() == 'help':
        await message.reply(f'Hi! I\'m a bot here to help you pick your classes more easily\n----------------------------------------------------------\nTo work me, simply enter the class you want to see!\nYou can either enter just the class and I will let you know which of the upcoming semesters it is offered in (ex. geog 363)\nOr you may enter the class and semester you are interested in seeing and I will tell you specifics about sections of the class offered that semester (ex. geog 363 winter 2022)\n----------------------------------------------------------\nIf I don\'t respond I am either offline or your message doesn\'t follow the correct format.\nIf you have errors or questions please ask The Help Desk or message <@650136117227683877>\n----------------------------------------------------------\n You may also type info for information regarding me, the Schedule Buddy bot :smile:', allowed_mentions = am)
        print('help was typed, help message was sent.')
        print('---------------------------------------------')
        return
    # info message prompt
    if message.content.lower() == 'info':
        # This line allows the bot to mention people, but it doesnt ping them. It's broken on mobile (looks like it's discord's fault not mine). Found it here: https://tutorial.vcokltfre.dev/tips/mentions/
        await message.reply(f"This bot was built by <@650136117227683877> out of love :heart:.\nI want to thank <@375852152544952322> for helping me build the bot.\n\nConcordia collects all kinds of data and its Open Data project thinks it should be accessible (I do too).\nPlease note the data is updated daily so enrollment numbers are not live, for that check your MyConcordia My Student Center.\n\nThis bot grabs data from Concordia's Open Data project here: https://github.com/opendataConcordiaU/documentation/blob/master/v1/queried_courses/schedule.md.\nThis bot operates under the Creative Commons Attribution 4.0 International Public License. https://creativecommons.org/licenses/by/4.0/legalcode\nThis bot is in no way affiliated to Concordia University.\n\nThat\'s about it, I hope the bot is helpful :smile:\n-Spencer", allowed_mentions = am)
        print('info was typed, info message was sent.')
        print('---------------------------------------------')
        return
    # hello message prompt
    if message.content.lower() == 'hello':
        username = str(message.author).split('#')[0]
        await message.reply(f'Hi {username}!\nLove you pass it on:heart:')
        return

    # These next variables store our parameters to know what the user is asking for
    user_message = re.split(' ', message.content)
    queried_course = user_message[0].upper()
    queried_number = user_message[1]
    print('User message as a list is:', user_message)
    print('length of user message is', len(user_message))

    if len(user_message) == 2:
        reply = check_semester_availability(class_list_json, queried_course, queried_number)
        await message.reply(reply)
    elif len(user_message) == 3 or 4:
        queried_semester_number = queried_semester_number_str(user_message)
        print(f'The queried department is: {queried_course}\nThe queried queried_course number is: {queried_number}\nThe queried semester is: {queried_semester_number}')
        print(line)

        # Check to see if the queried_course is offered in the semester the user wants to know about
        # Then grab object containing semester info
        semester_object = grab_semester_tupple(queried_semester_number)

        # Now we filter through locally saved file to get to only the classes we want
        working_semester_json = list(filter(lambda x: x['termCode'] in queried_semester_number, class_list_json))
        working_course_json = list(filter(lambda x: x['subject'] in [queried_course], working_semester_json))
        final_data = list(filter(lambda x: x['catalog'] in [queried_number], working_course_json))
        print('This is the final_data that will be used\n', json.dumps(final_data, indent = 4),'\n',line)

        # This is our check to see if the class is offered in the queried semester. If variable is empty, it's not offered and we throw a message.
        if final_data == []:
            await message.reply (f'{queried_course.capitalize()} {queried_number} is **not offered** in the {user_message[2]} semester.')
            return

        # Now we start collecting the data we want from final_data to format it
        course_title = return_obj_copy(final_data)
        relevant_subject = f'{user_message[0].upper()} {user_message[1]}'
        relevant_title = course_title['courseTitle']
        relevant_prereqs = prereqs_mapping(final_data)
        sending_data = centering_func(relevant_subject, relevant_title, queried_semester_number, relevant_prereqs)
        sending_data += relevant_prereqs + '\n' + '----------------------------------------------------------' + '\n'
        lecture_data = ''
        else_data = ''
        for obj in final_data:
            constructing_data = []
            relevant_type = obj['componentDescription']
            relevant_location = obj['locationCode']
            relevant_room = obj['roomCode']
            relevant_capacity = obj['enrollmentCapacity']
            relevant_enrollment = obj['currentEnrollment']
            relevant_section = obj['section']
            relevant_instruction_mode = obj['instructionModeDescription']
            relevant_waitlist = obj['currentWaitlistTotal']
                # TODO Throw in if to check section if they only want one specific section here
                # This can only happen once we figure out regex.

            #Sometimes Concordia overbooks and it makes it looks like the bot is broken, this adds a little message to let people know it's not but only when it looks like it might be.
            #the variable enrollment_string is used in the constructing_data that wil be used.
            enrollement_string = (f'Seats Filled:  {relevant_enrollment}/{relevant_capacity}')
        
            #The times needed some formatting to make em pretty. Seperating them for legibility
            start_time = str(obj['classStartTime'])
            working_start_time = start_time.split('.',2)
            relevant_start_time = (working_start_time[0] + ':' + working_start_time[1])
            end_time = str(obj['classEndTime'])
            working_end_time = end_time.split('.',2)
            relevant_end_time = (working_end_time[0] + ':' + working_end_time[1])
            class_occurance_string = class_days(obj)
            if relevant_type == 'Lecture':
                constructing_lecture_data = (f"Type:  {relevant_type}\nSection:  {relevant_section}\nLocation:  {relevant_location} --- {relevant_room}\nClass Days:  {class_occurance_string}\nClass Time:  {relevant_start_time} - {relevant_end_time}\n{enrollement_string}\nStudents Waitlisted:  {relevant_waitlist}\n--------------------------------\n")
                lecture_data += lecture_data + constructing_lecture_data
            else:
                constructing_else_data = (f"Type:  {relevant_type}\nSection:  {relevant_section}\nLocation:  {relevant_location} --- {relevant_room}\nClass Days:  {class_occurance_string}\nClass Time:  {relevant_start_time} - {relevant_end_time}\n{enrollement_string}\nStudents Waitlisted:  {relevant_waitlist}\n--------------------------------\n")
                else_data += constructing_else_data
        sending_data += lecture_data + else_data
        print(f'The bot is sending the following\n', sending_data)
        #This await command is when the bot will send the relevant info to discord.
        print('Length of the final message is:', len(sending_data))
        if len(sending_data) >= 4000:
            await message.reply (f'{queried_course.capitalize()} {queried_number} --- {relevant_title} has too many sections for me to send :sob:.\nYou may want to visit this link for more info on your classes:\n{current_info_link}')
        await message.reply(f'{sending_data}', allowed_mentions = am)
        final_data = []
    else:
        await message.reply (f'{queried_course.capitalize()} {queried_number} is not offered in the {semester_object[1]} semester.\nIf you think it is, check your spelling and make sure there is a space between the class name, number, semester, and year ex. geog 363 winter 2022')
        print('This queried course is not offered in the', user_message[2].lower(), 'semester\n This message comes up when it truly isnt offered, or if the user input doesnt match the expected input')
        return


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
def clean_duplicate_data(working_data):
    print('Entering clean_duplicate_data function')
    clean_data = []
    for obj in working_data:
        if clean_data.__contains__(obj):
            del obj
        else:
            obj_copy = obj.copy()
            clean_data.append(obj_copy)
    print('Data is cleaned (removed of duplicates)')
    return clean_data

def prereqs_mapping(final_data):
    course_id = final_data[0]['courseID']
    prereqs = load_prereqs()
    for obj in prereqs:
        if obj['ID'] == course_id:
            prereqs = obj['prerequisites']
    if prereqs == '' or "":
        prereqs = 'This course has no prerequisites.'
    else:
        prereqs = prereqs
    return prereqs

# This is a stupid function because I couldnt get to the layer to grab the course title, hopefully it doesnt break shit
def return_obj_copy(working_data):
    for obj in working_data:
        return obj

# Get request and saving relevant semesters to Data/Classes.json
# Gets called upon the bot entering the server, and once a day in a task loop.
def fetch_and_save_classes(current_semester_numbers):
    print('Beginning fetch and save classes function')
    auth = API_config['auth']
    r = requests.get('https://opendata.concordia.ca/API/v1/course/schedule/filter/*/*/*', auth = auth)
    input_json = list(json.loads(r.text))
    relevant_semesters = list(filter(lambda x: x['termCode'] in current_semester_numbers, input_json))
    clean_relevant_semesters = clean_duplicate_data(relevant_semesters)
    output_json = json.dumps(clean_relevant_semesters, indent = 4)
    class_list = open(class_file, 'w' )
    class_list.write(output_json)
    class_list.close
    print('Daily class fetch has been completed\n')

def fetch_and_save_prereqs():
    print('Beginning fetch and save prereqs function')
    auth = API_config['auth']
    r = requests.get('https://opendata.concordia.ca/API/v1/course/catalog/filter/*/*/*', auth = auth)
    input_json = list(json.loads(r.text))
    clean_input_json = clean_duplicate_data(input_json)
    output_json = json.dumps(clean_input_json, indent = 4)
    prereqs_list = open(prereqs_file, 'w' )
    prereqs_list.write(output_json)
    prereqs_list.close
    print('Daily prereqs fetch has been completed\n')

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

def read_current_semester_file():
    file = open(current_semesters_file, 'r')
    current_semesters_json = file.read()
    file.close()
    return json.loads(current_semesters_json)

def grab_semester_tupple(queried_semester_number):
    semester_list_json = read_current_semester_file()
    for key, value in semester_list_json['currentsemesters'].items():
        if queried_semester_number == key:
            semester_list = [key,value]
            return semester_list

# Big ol function that lets the user know which semesters their queried course is offered in out of the ones the bot is looking at.
# Called if len(user_message) == 2 as in Geog 363
def check_semester_availability(class_list_json, queried_course, queried_number):
    print(line)
    reply_string = f'**{queried_course.lower().capitalize()} {queried_number}** is offered in the following semesters:\n'
    working_data = []
    final_data = {}
    for key in class_list_json:
        if (queried_course == key['subject'] and queried_number == key['catalog']) == True:
            dirty_tupple = grab_semester_tupple(key['termCode'])
            working_data.append(dirty_tupple)
    final_data = clean_duplicate_data(working_data)
    print('Semester final data is:', final_data)
    for key in final_data:
        clean_tupple = grab_semester_tupple(key[0])
        reply_string += f'• {clean_tupple[1].capitalize()}\n'
    reply_string += f'\nTo view the sections offered each semester send another message with the following format:\n{queried_course.capitalize()} {queried_number} semester year'
    if final_data == []:
        reply_string = f'{queried_course.lower().capitalize()} {queried_number} is **not offered** in any semesters I am currently looking at :cry:'
    print(line,'\nThe bot is sending the following:\n', reply_string, '\n', line)
    return reply_string

def centering_func(subject, title, number, prereqs):
    object = grab_semester_tupple(number)
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

@tasks.loop(hours = 24)
async def daily_classesjson_update():
    fetch_and_save_classes(current_semester_numbers)
    fetch_and_save_prereqs()

@daily_classesjson_update.before_loop
async def configure_daily_classesjson_update():
    print(line, '\nTask.loop info:')
    hour = 4
    minute = 00
    await client.wait_until_ready()
    now = datetime.now()
    future = datetime(now.year, now.month, now.day, hour, minute)
    if now.hour > hour or (now.hour == hour and now.minute > minute): 
        future += timedelta(days=1)
    print('The loop is set to run at:', future)
    print('The loop will run in:', future - now)
    await asyncio.sleep((future-now).seconds)

# Initialize our files on start of program, comment out while working on it, it takes a while, unless you need to initialize anything in the Data folder.
# fetch_and_save_classes(current_semester_numbers)
# fetch_and_save_prereqs()
populate_current_semester_file(current_semesters_file, current_semester_numbers)

daily_classesjson_update.start()
client.run(Token)