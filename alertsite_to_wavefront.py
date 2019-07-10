#!/usr/bin/python

# alertsite_to_wavefront
# Retrieves latest status of all alertsite checks and sends them to wavefront
# Developed by Wayne Haber @ www.secureworks.com

import requests
import json
import re
import xml.etree.ElementTree as ET
import socket
from requests.auth import HTTPBasicAuth
import time
from datetime import datetime


def collect_and_send_metrics():


	try:
		# get configuration
		with open('config.json','r') as f:
			config=json.load(f)
		f.close()
	except:
		print ("Could not load config.json file")
		return

	# configure proxy
	headers= {'User-Agent':'Python'};

	debug = config['debug']
	proxyDict = { "http"  : config['proxy'], "https" : config['proxy'], }

	try:
		response=requests.post(config['alertsiteurl'],proxies=proxyDict, headers=headers,
			auth=HTTPBasicAuth(config['alertsiteid'],config['alertsitepassword']) );
	except:
		print ("Could not make request to alertsite")
		return

	# if debugging is on, write out the xml file
	if (debug) :
		text_file = open("xml.out", "w")
		text_file.write(response.text)
		text_file.close()

	# parse xml
	root=ET.fromstring(response.text)

	# current_* variables are to store the most recent result for each check
	current_display_descrip=''
	current_last_status=''
	current_dt_last_status=''
	current_resptime_last=''
	current_dict = {}

	for child in root:
		for child2 in child:
			for child3 in child2:
				for child4 in child3:
					tag=child4.tag
					text=child4.text
					if tag=='display_descrip' :
						display_descrip=text
						# remove special characters in alertsite check names that wavefront doesn't like
						display_descrip=display_descrip.replace(' ','_')
						display_descrip=display_descrip.replace(':','')
						display_descrip=display_descrip.replace('(','')
						display_descrip=display_descrip.replace(')','')
						display_descrip=display_descrip.replace(',','_')
						if (current_display_descrip=='') :
							current_display_descrip=display_descrip
						if (display_descrip!=current_display_descrip)  :
							# We are at the next alertsite check
							current_dict[current_display_descrip]=current_last_status + "||" + current_dt_last_status + "||" + current_resptime_last + "||"
							# set current_display and clear other current variables
							current_display_descrip=display_descrip
							current_last_status=''
							current_dt_last_status=''
							current_resptime_last=''

					elif tag=='last_status' :
						last_status=text
					elif tag=='dt_last_status' :
						dt_last_status=text
					elif tag=='resptime_last' :
						resptime_last=text
						# last tag
						# check if status is not an alertsite error (9095, 4050) and that this is the most recent check found so far	
						if ((last_status!=9095) and (last_status!=4050) and (dt_last_status>current_dt_last_status)) :
							if (last_status=='0') :
								current_last_status='1'
							else :
								current_last_status='0'
							# Zero is good, anything else is an error.  Good = status of 1, Not good = 0

							current_dt_last_status=dt_last_status
							current_resptime_last=resptime_last


	# process last one
	current_dict[current_display_descrip]=current_last_status + "||" + current_dt_last_status + "||" + current_resptime_last + "||"


	# open last set of results
	try:
		old_dict=json.load(open("dict.out"))
	except:
		old_dict={} # This is ok.  We can start with no historical data
	

	# open socket connetion to wavefront proxy

	try:
		s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		s.connect((config['wavefrontproxy'],config['wavefrontproxyport']))
	except:
		print ("Could not connect to wavefront proxy")
		return 

	sendcount=0

	# go through all values in the current dictionary
	for x, y in current_dict.items() :
		lookup=old_dict.get(x,'') # if nothing found return empty string
		if (lookup!=y) : 
			# vals 0 = status, 1 = timestamp, 2 = seconds
			# if old != new then it has changed.  output it
			vals=y.split('||') # parse status and seconds

			# convert timestamp to epoch tim
			datetime_obj = datetime.strptime(vals[1],'%Y-%m-%d %H:%M:%S')
			epoch_sec = datetime_obj.strftime('%s')


			m1='{0} {1} {2} {3} {4} \n'.format('alertsite.'+x+'.status',vals[0],epoch_sec,'source=alertsite')
			m2='{0} {1} {2} {3} {4} \n'.format('alertsite.'+x+'.seconds',vals[2],epoch_sec,'source=alertsite')
            m1=m1.encode('ascii');
			m2=m2.encode('ascii');
			s.send(m1)
			s.send(m2)
			sendcount = sendcount+1

	# close socket
	s.close()

	# save current dict
	json.dump(current_dict,open("dict.out",'w'))


	print ('{0}: Sent {1} metric pairs'.format(time.ctime(),sendcount))


print ('{0}: Program starting'.format(time.ctime()))

while 1 :
	try:	
		collect_and_send_metrics()
	except:
		print ('Could not collect and send metrics')
		
	time.sleep(30)
