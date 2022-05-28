import asyncio
import discord
from discord import Message
from discord.ext import tasks
import re
import datetime
from datetime import datetime, timedelta
from Config.config import *
from functions import *

class_file = 'Data/Classes.json'
current_semesters_file = 'Data/CurrentSemesters.json'
prereqs_file = 'Data/Prereqs.json'
line = '---------------------------------------------'
client = discord.Client()
# This is the password for the bot to enter the discord server, you have to give it access to the server on the discord developer portal
Token = str(discord_config["token"])

# TODO Check to see if link is still alive / proper.
current_info_link = 'https://www.concordia.ca/academics/undergraduate/calendar.html'

# this client event lets us know we successfully connected to the server and have initialized Data/Classes.json with a fetch and CurrentSemesters.json with our function
@client.event
async def on_ready():
    print(line)
    print('We have logged in as {0.user}'.format(client))
    print(f'Ready to go!\n{line}')
    return

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
        semester_object = grab_semester_list(queried_semester_number)

        # Now we filter through locally saved file to get to only the classes we want
        working_semester_json = list(filter(lambda x: x['termCode'] in queried_semester_number, class_list_json))
        working_course_json = list(filter(lambda x: x['subject'] in [queried_course], working_semester_json))
        final_data = list(filter(lambda x: x['catalog'] in [queried_number], working_course_json))
        print(f'The length of final data is: {len(final_data)}\nThis number should corespond to how many sections the bot sends.')

        # This is our check to see if the class is offered in the queried semester. If variable is empty, it's not offered and we throw a message.
        if final_data == []:
            semester_string = 'It is however offered in the following semesters:\n'
            semester_list = (semester_availability_list(class_list_json, queried_course, queried_number))
            class_title = get_course_name(class_list_json, queried_course, queried_number)
            for semesters in semester_list:
                semester_string += f'{semesters}'
            await message.reply (f'**{queried_course.capitalize()} {queried_number}** --- **{class_title}** is not offered in the {user_message[2]} semester.\n{semester_string}To view the sections offered each semester send another message with the following format:\n{queried_course.capitalize()} {queried_number} semester year')
            return

        # Now we start collecting the data we want from final_data to format it
        relevant_title = final_data[0]['courseTitle']
        subject = final_data[0]['subject']
        course = final_data[0]['catalog']
        relevant_subject = f'{subject} {course}'
        relevant_prereqs = final_data[0]['prerequisites']
        if relevant_prereqs == "":
            relevant_prereqs = 'This course has no prerequisites.'
        sending_data = centering_func(relevant_subject, relevant_title, queried_semester_number, relevant_prereqs)
        sending_data += relevant_prereqs + '\n' + '----------------------------------------------------------' + '\n'
        lecture_data = ''
        else_data = ''

        for obj in final_data:
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
            enrollement_string = (f'Seats Filled:  {relevant_enrollment}/{relevant_capacity}')
        
            #The times needed some formatting to make em pretty. Seperating them for legibility
            start_time = str(obj['classStartTime'])
            working_start_time = start_time.split('.',2)
            relevant_start_time = (working_start_time[0] + ':' + working_start_time[1])
            end_time = str(obj['classEndTime'])
            working_end_time = end_time.split('.',2)
            relevant_end_time = (working_end_time[0] + ':' + working_end_time[1])
            class_occurance_string = class_days(obj)

            # Here we seperate lecture sections from lab or others to keep all available lecture sections at the top of the message.
            if relevant_type == 'Lecture':
                constructing_lecture_data = (f"Type:  {relevant_type}\nSection:  {relevant_section}\nLocation:  {relevant_location} --- {relevant_room}\nClass Days:  {class_occurance_string}\nClass Time:  {relevant_start_time} - {relevant_end_time}\n{enrollement_string}\nStudents Waitlisted:  {relevant_waitlist}\n--------------------------------\n")
                lecture_data += constructing_lecture_data
            else:
                constructing_else_data = (f"Type:  {relevant_type}\nSection:  {relevant_section}\nLocation:  {relevant_location} --- {relevant_room}\nClass Days:  {class_occurance_string}\nClass Time:  {relevant_start_time} - {relevant_end_time}\n{enrollement_string}\nStudents Waitlisted:  {relevant_waitlist}\n--------------------------------\n")
                else_data += constructing_else_data
        # This line brings all the strings together and is what the bot will send.
        sending_data = sending_data + lecture_data + else_data
        print(f'The bot is sending the following\n', sending_data)
        print(f'Length of the final message is: {len(sending_data)}.\n2000 characters is the maximum, if it is exceded the code throws an error and so do we to the user.\n{line}')
        if len(sending_data) >= 2000:
            await message.reply (f'**{queried_course.capitalize()} {queried_number} --- {relevant_title}** has too many sections for me to send :sob:.\nYou may want to visit this link for more info on your classes:\n{current_info_link}')
        await message.reply(f'{sending_data}', allowed_mentions = am)
        final_data = []
    else:
        await message.reply (f'{queried_course.capitalize()} {queried_number} is not offered in the {semester_object[1]} semester.\nIf you think it is, check your spelling and make sure there is a space between the class name, number, semester, and year ex. geog 363 winter 2022')
        print('This queried course is not offered in the', user_message[2].lower(), 'semester\n This message comes up when it truly isnt offered, or if the user input doesnt match the expected input')
        return


@tasks.loop(hours = 24)
async def daily_classesjson_update():
    fetch_and_save_classes(current_semester_numbers)

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
populate_current_semester_file(current_semesters_file, current_semester_numbers)
daily_classesjson_update.start()
client.run(Token)