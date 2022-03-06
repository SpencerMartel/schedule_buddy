import discord
from discord import Message
from discord.mentions import AllowedMentions
import requests
from requests import status_codes
from requests import auth
from requests import sessions
from requests.models import HTTPBasicAuth
import json
import re


#We will begin by connecting the bot to the server, then create an event when a class is typed
#The bot will then search for, organize, and spit out the relevant information.

client = discord.Client()
Token = 'OTI3NjQ2OTYyNDc0NDMwNDY0.YdNQjg.A8dd9EJ8KuZXUwzU3fRfJONC32E'
#this is the password for the bot to enter the discord server, you then have to give it access to the server on the discord developer portal


@client.event
async def on_ready():
    print('---------------------------------------------')
    print('We have logged in as {0.user}'.format(client))
    print('---------------------------------------------')
    return
#this client event just lets us know the bot has successfully been added to the server.

s = requests.Session()
s.auth = HTTPBasicAuth('449','1d82e249a3b972561791eeefd1dca83a')
base_url = ('https://opendata.concordia.ca/API/v1/course/schedule/filter/*/')

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------#
#---------------------------------------------------------------------------END OF DISCORD STUFF--------------------------------------------------------------------------#
#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------#

#this event is the meat and potatoes

@client.event
async def on_message(message):

    # These variables will need to be changed every semester.
    # Check to make sure the link is still alive, if not, find the new concordia undergraduate calendar link
    current_semester = 'Winter 2022'
    # TODO use regex to allow for multiple semester searches.
    current_semester_number = '2214'
    current_info_link = 'https://www.concordia.ca/academics/undergraduate/calendar/current/courses-quick-links.html'

    #condition to break so the bot doesn't respond to itself.
    if message.author == client.user:
        return
    
    am = discord.AllowedMentions(users = False, everyone = False, roles = False, replied_user = True)
    author = str(message.author.id)
    
    
    if message.channel.name == 'class-info':
        print('Correct channel detected')
        user_input = message.content.upper()

        # help message prompt
        if message.content.lower() == 'help':
            await message.reply(f'Hi! I\'m a bot here to help you pick your classes more easily\n----------------------------------------------------------\nTo work me, simply enter the class you want to see!\nThe format must be "course" followed by a space then "####" ex. geog 363\nI will then tell you pertinent info about that class\nI take a little time to respond, the Concordia database I get info from is a little slow\n----------------------------------------------------------\nIf I don\'t respond I am either offline or your message doesn\'t follow the correct format.\nIf you have errors or questions please ask The Help Desk or message <@650136117227683877>\n----------------------------------------------------------\n You may also type info for information regarding me, the Schedule Buddy bot :smile:', allowed_mentions = am)
            print('help was typed, help message was sent.')
            print('---------------------------------------------')
            return
        
        # info message prompt
        if message.content.lower() == 'info':
            # This line allows the bot to mention people, but it doesnt ping them. It's broken on mobile (looks like it's discord's fault not mine). Found it here: https://tutorial.vcokltfre.dev/tips/mentions/
            await message.reply(f"This bot was built by <@650136117227683877> out of love :heart:.\nI want to thank <@375852152544952322> for helping me build the bot.\n\nConcordia collects all kinds of data and its Open Data project thinks it should be accessible (I do too).\nPlease note the data is updated daily so enrollment numbers are not live, for that check your MyConcordia My Student Center.\n\nThis bot grabs data from Concordia's Open Data project here: https://github.com/opendataConcordiaU/documentation/blob/master/v1/courses/schedule.md.\nThis bot operates under the Creative Commons Attribution 4.0 International Public License. https://creativecommons.org/licenses/by/4.0/legalcode\nThis bot is in no way affiliated to Concordia University.\n\nThat\'s about it, I hope the bot is helpful :smile:\n-Spencer", allowed_mentions = am)
            print('info was typed, info message was sent.')
            print('---------------------------------------------')
            return

        # hello message prompt
        if message.content.lower() == 'hello':
            username = str(message.author).split('#')[0]
            await message.reply(f'Hi {username}!\nLove you pass it on:heart:')
            return
        
        # Here starts all the shit if they want class info
        # turns input into a list to be able to seperate the department, class number, and section.
        user_message = re.split(' ', message.content)
        print('The user message as a list is', user_message)
        print("The length of the list is", len(user_message))
        print('---------------------------------------------')

        # These next variables store our parameters for our get request to know what the user is asking for
        if len(user_message) == 2:
            course = user_message[0].upper()
            number = user_message[1]
            print('The queried department is:', course)
            print('The queried course number is:', number)
        elif len(user_message) > 2:
            await message.reply (f'Looks like your message doesn\'t follow the required format\nMake sure you enter the class name followed by a space followed by the class number (ex. geog 220)\nFor more help')
        print('---------------------------------------------')

        # This part builds the url for the get request, I don't think it's the most efficient but it works
        #nobody uses the course ID so we will leave it as *

        slash = "/"
        url = (base_url + course + slash + number)
        print('The url for the get request is: ', url)
        print('Sending get request')
        print('---------------------------------------------')

        # This is the actual get request for the data, tried using session but it didn't seem to speed anything up
        response_API = s.get(url)
        print('API get request status code is:', response_API.status_code)
        print('The time the get request took was:', response_API.elapsed.total_seconds(), 'seconds')
        print('---------------------------------------------')


        if response_API.status_code == 200:
            dict_data = json.loads(response_API.text)

            #check to see if the course is offered in the semester the bot is currently looking at
            if any(d['termCode'] == current_semester_number for d in dict_data):
                offered_this_semester = (f'\nThis course is offered in the {current_semester} semester.')

                #this next line filters out all the semesters that aren't the one the bot is currently looking at.
                #It stores the data we want as json data in the variable called working_data.
                #We then initialize a list called final_data which will hold the actual data (in a list of dicts) we want after sorting for current semester and deleting duplicate data the API sends.
                working_data = list(filter(lambda x: x['termCode'] in [current_semester_number], dict_data))
                
                final_data = []

                #This next section cleans up our data recieved from the API
                #For some reason it sends duplicates of classes, no idea why
                #There's a tiny forum for it on the github here: https://github.com/opendataConcordiaU/documentation/issues/8

                print('We are now beginning the looping through the data after it has been scanned to only contain the semester we want.')
                for obj in working_data:
                    if final_data.__contains__(obj):
                        del obj
                    else:
                        obj_copy = obj.copy()
                        final_data.append(obj_copy)
                print('---------------------------------------------')
                print('This is the final_data that will be used\n')
                print(json.dumps(final_data, indent = 4))
                

                # This next sorting goes through the componentCode column of the data and extracts it, this creates our counter for lecture and lab activities
                # Concordia may add different class types, this would be a bitch, I think I got them all for now.
                # We will use these values later to find out how many unique instances of the class we must print
                # this is so cool to me, so to the computer, a boolean True is assigned a value 1 and boolean False is assigned a value 0
                # So to find out how many lectures, labs, etc. all we do is create a list and take the sum of the list, so cool
                # TODO make this a function
                print('---------------------------------------------')
                print('This is the breakdown of componentCode (class type):\n')

                lec_check = list(obj['componentCode'] == 'LEC' for obj in final_data)
                lec_counter = sum(lec_check)
                print('The lec check list is:', lec_check)
                print('The course has', lec_counter, 'lecture sections\n')
                
                lab_check = list(obj['componentCode'] == 'LAB' for obj in final_data)
                lab_counter = sum(lab_check)
                print('The lab check list is:', lab_check)
                print('The course has', lab_counter, 'laboratory sections\n')

                sem_check = list(obj['componentCode'] == 'SEM' for obj in final_data)
                sem_counter = sum(sem_check)
                print('The sem check list is:', sem_check)
                print('The course has', sem_counter, 'seminar sections\n')

                con_check = list(obj['componentCode'] == 'CON' for obj in final_data)
                con_counter = sum(con_check)
                print('The con check list is:', con_check)
                print('The course has', con_counter, 'conference sections\n')

                stu_check = list(obj['componentCode'] == 'STU' for obj in final_data)
                stu_counter = sum(stu_check)
                print('The stu check list is:', stu_check)
                print('The course has', stu_counter, 'studio sections\n')

                onl_check = list(obj['componentCode'] == 'ONL' for obj in final_data)
                onl_counter = sum(onl_check)
                print('The onl check list is:', onl_check)
                print('The course has', onl_counter, 'online sections\n')

                pra_check = list(obj['componentCode'] == 'PRA' for obj in final_data)
                pra_counter = sum(pra_check)
                print('The pra check list is:', pra_check)
                print('The course has', pra_counter, 'practicum/internship/work term sections\n')

                tut_check = list(obj['componentCode'] == 'TUT' for obj in final_data)
                tut_counter = sum(tut_check)
                print('The tut check list is:', tut_check)
                print('The course has', tut_counter, 'tutorial sections\n')

                wks_check = list(obj['componentCode'] == 'WKS' for obj in final_data)
                wks_counter = sum(wks_check)
                print('The wks check list is:', wks_check)
                print('The course has', wks_counter, 'workshop sections\n')

                
                lec_sections = lec_counter + sem_counter + con_counter + onl_counter
                lab_sections = lab_counter + stu_counter + pra_counter + tut_counter + wks_counter
                total_occurances = lec_sections + lab_sections

                if (total_occurances) > 10:
                    await message.reply (f'{offered_this_semester}\n----------------------------------------------------------\nUnfortunately this class has too many sections for me to send :disappointed:\nThis is sometimes due to labs being split up by week and being called new sections (MECH 351)\nFind more info on your class here: {current_info_link}\nor in your My Student Center.')
                    return
                print('The course occurs a total of', total_occurances, 'times in the data')
                print('---------------------------------------------')

                #Proper singular & plural outputs to be pretty.
                if lec_sections == 1:
                    lec_output = (f'This course has {lec_sections} lecture type section and')
                else:
                    lec_output = (f'This course has {lec_sections} lecture type sections and')

                if lab_sections == 1:
                    lab_output = (f' {lab_sections} lab type section.')
                else:
                    lab_output = (f' {lab_sections} lab type sections.')
                

                #Now we build what the bot will say in seperate variables that all come together in the string variable relevant_data
                #The bot then sends relevant_data as it's output
                #some of the data is dependant on which lec or lab section, need to seperate it

                relevant_subject = obj_copy['subject'] + ' ' + obj_copy['catalog']
                relevant_title = obj_copy['courseTitle']

            
                sending_data = (f'----------------------------------------------------------{offered_this_semester}\n{lec_output}{lab_output}\n----------------------------------------------------------\n{relevant_subject} --- {relevant_title}\n----------------------------------------------------------\n')
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
                        # Throw in if to check section if they only want one specific section here
                        # This can only happen once we figure out regex.

                    #Sometimes Concordia overbooks and it makes it looks like the bot is broken, this adds a little message to let people know it's not but only when it looks like it might be.
                    #the variable enrollment_string is used in the constructing_data that wil be used.
                    if relevant_enrollment > relevant_capacity:
                        enrollement_string = (f'Seats Filled:  {relevant_enrollment}/{relevant_capacity}  (Concordia overbooks some classes, it\'s not unusual for enrollment to exceed stated capacity)')
                    else:
                        enrollement_string = (f'Seats Filled:  {relevant_enrollment}/{relevant_capacity}')
                
                    #The times needed some formatting to make em pretty. Seperating them for legibility
                    start_time = str(obj['classStartTime'])
                    working_start_time = start_time.split('.',2)
                    relevant_start_time = (working_start_time[0] + ':' + working_start_time[1])

                    end_time = str(obj['classEndTime'])
                    working_end_time = end_time.split('.',2)
                    relevant_end_time = (working_end_time[0] + ':' + working_end_time[1])

                    #finding which days it's on was super fucking annoying, it is also seperated for legibility.
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
                    #cool lil function to turn my list into a pretty string for the bot.
                    def listtostring(x):
                        str = ' & '
                        return (str.join(x))
                    class_occurance_string = listtostring(class_occurance)

                    constructing_data = (f"Type:  {relevant_type}\nSection:  {relevant_section}\nLocation:  {relevant_location} --- {relevant_room}\nClass Days:  {class_occurance_string}\nClass Time:  {relevant_start_time} - {relevant_end_time}\n{enrollement_string}\nStudents Waitlisted:  {relevant_waitlist}\n--------------------------------\n")

                    sending_data += constructing_data


                print(f'The bot is sending the following',sending_data)
                #This await command is when the bot will send the relevant info to discord.
                await message.reply(f'\n{sending_data}', allowed_mentions = am)

            else:
                await message.reply (f'This course is not offered in the {current_semester} semester.\nIf you think it is, check your spelling and make sure there is a space between the class name and number ex. geog 361.')
                print('This course is not offered in the', current_semester, 'semester\nThis message comes up when the course truly isnt offered, or if the user input doesnt match the expected input')
                return
            return
        elif response_API.status_code != 200:
            await message.reply(f'Oops looks like there\'s a problem\nCheck your spelling for any errors and make sure there is a space between the class and its number. If the problem persists, please contact the help desk.')
            return
        return
    return

# This line actually runs the fuckin thing.
client.run(Token)