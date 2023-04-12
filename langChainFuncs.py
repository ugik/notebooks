# langChainFuncs.py

from langchain import OpenAI
from langchain.agents import initialize_agent, Tool
from langchain.chains import PALChain
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain import PromptTemplate, LLMChain

import streamlit as st
import os 
from dateutil import parser
import datetime
import random
import json
from faker import Faker

fake = Faker()
today = datetime.datetime.now()
hours = (9, 18)   # open hours

######### utility functions for scheduling

# create random schedule
def createSchedule(daysAhead=5, perDay=5):
    schedule = {}
    for d in range(0, daysAhead):
        date = (today + datetime.timedelta(days=d)).strftime('%m/%d/%y')
        schedule[date] = {}

        for h in range(0, perDay -d):
            hour = random.randint(hours[0], hours[1])
            if hour not in schedule[date]:
                schedule[date][hour] = fake.name()
                
    return schedule

# get available times for a date
def getAvailTimes(date, num=10):
    schedule = loadSchedule()

    if '/' not in date or 'mm' in date:
        return 'date parameter must be in format: mm/dd/yy'

    if date not in schedule:
        return 'that day is entirely open, all times are available'

    hoursAvail = 'hours available on %s are ' % date

    for h in range(hours[0], hours[1]):
        if str(h) not in schedule[date]:
            hoursAvail += str(h) +':00, '
            num -= 1
            if num == 0:
                break
    
    if num > 0:
        hoursAvail = hoursAvail[:-2] +' - all other times are reserved'
    else:
        hoursAvail = hoursAvail[:-2]
        
    return hoursAvail

# schedule available time
def scheduleTime(dateTime):
    schedule = loadSchedule()

    date, time = dateTime.split(',')
    
    if not date or not time:
        return "sorry parameters must be date and time comma separated, for example: `12/31/23, 10:00` would be the input if for Dec 31'st 2023 at 10am"

    # get hours
    if ':' in time:
        timeHour = int(time[:time.index(':')])
        print(timeHour)
        
        if timeHour not in schedule[date]:
            if timeHour >= hours[0] and timeHour <= hours[1]:
                schedule[date][timeHour] = fake.name()
                saveSchedule(schedule)
                print('Updated schedule json...')
                return 'thank you, appointment scheduled for %s under name %s' % (time, schedule[date][timeHour])
            else:
                return '%s is after hours, please select a time during business hours' % time
        else:
            return 'sorry that time (%s) on %s is not available' % (time, date)
    else:
        return '%s is not a valid time, time must be in format hh:mm'
    
# save schedule json
def saveSchedule(schedule):
    with open('schedule.json', 'w') as f:
        json.dump(schedule, f)
    
# load schedule json
def loadSchedule():
    global schedule
    
    with open('schedule.json') as json_file:
        return json.load(json_file)

# get today's date
def todayDate():
	return today.strftime('%m/%d/%y')

#########

os.environ['OPENAI_API_KEY'] = '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'


llm = OpenAI(temperature=0, verbose=True)
pal_chain = PALChain.from_math_prompt(llm, verbose=True)


tools = [
	Tool(
		name = "today's date",
		func = lambda string: todayDate(),
		description="use to get today's date",
		),
	Tool(
		name = 'available appointments',
		func = lambda string: getAvailTimes(string),
		description="Use to check on available appointment times for a given date. The input to this tool should be a string in this format mm/dd/yy. This is the only way for you to answer questions about available appointments. This tool will reply with available times for the specified date in 24hour time, for example: 15:00 and 3pm are the same.",
		),
	Tool(
		name = 'schedule appointment',
		func = lambda string: scheduleTime(string),
		description="Use to schedule an appointment for a given date and time. The input to this tool should be a comma separated list of 2 strings: date and time in format: mm/dd/yy, hh:mm, convert date and time to these formats. For example, `12/31/23, 10:00` would be the input if for Dec 31'st 2023 at 10am",
		),
	Tool(
        name = "PAL",
        func = pal_chain.run,
        description = "useful for when you need to answer questions about math or word problems or date comparisons"
		)
	]

memory = ConversationBufferMemory(memory_key="chat_history")

if 'agent_memory' not in st.session_state:
	st.session_state['agent_memory'] = ConversationBufferMemory(memory_key='chat_history')

agent_chain = initialize_agent(tools, llm, agent='zero-shot-react-description', memory=st.session_state['agent_memory'], verbose=True)

st.header(":gray[Langchain chatbot with Python function tools for schedule]")
user_input = st.text_input("You: ")

if st.button('Submit'):
	print('user_input:', user_input)

	st.markdown(agent_chain.run(input=user_input))
	#print(st.session_state['agent_memory'])

	


