#Tornado Libraries
from tornado.ioloop import IOLoop
from tornado.escape import json_encode
from tornado.web import RequestHandler, Application, asynchronous
from tornado.httpserver import HTTPServer
from tornado.httpclient import AsyncHTTPClient
from tornado.gen import engine, Task

#Other Libraries
import sqlite3
import json
import requests
import os
import urllib2

#custom modules
from Database.database import _execute



#Handlers :-
class MainHandler(RequestHandler):
	def get(self):
		self.write("Welcome to travelnet")

class ImageRateHandler(RequestHandler):
	@asynchronous
	@engine
	def get(self):
		img_url = self.get_argument('img','0')
		client = AsyncHTTPClient()
		response = yield Task(client.fetch,"http://apius.faceplusplus.com/v2/detection/detect?api_key=e2707513a30c55f950583457e8845ec1&api_secret=9cWd6oDOtFMmqhGT7mwPKphefakx52tI&url="+str(img_url))
		js = []
		data = json.loads(response.body)
		latitude = self.get_argument('latitude','0')
		longitude = self.get_argument('longitude','0')
		for i in data['face']:
			gender = i['attribute']['gender']['value']
			def getAgeCategory():
				age = i['attribute']['age']['value']
				if(age>55):
					ageCategory = "Old Age"
				elif(age>20 and age<56):
					ageCategory = "Youth"
				elif(age>12 and age<21):
					ageCategory = "Teenageer"
				else:
					ageCategory = "Kids"
				return ageCategory
			def rating():
				smiling = i['attribute']['smiling']['value']
				if(smiling>75):
					rate = 5
				elif(smiling>61 and smiling<76):
					rate = 4
				elif(smiling>50 and smiling<62):
					rate = 3
				elif(smiling>15 and smiling<51):
					rate = 2
				else:
					rate = 1
				return rate
			response =yield Task(client.fetch,'http://maps.googleapis.com/maps/api/geocode/json?latlng='+str(latitude)+','+str(longitude)+'&sensor=true')
			data = json.loads(response.body)
			address = data['results'][0]['formatted_address']
			rate = rating()
			ageCategory = getAgeCategory()
			_execute("""insert into upload (img_url, ageCategory, latitude, longitude, rating, gender, location) values ("{0}","{1}","{2}","{3}","{4}","{5}","{6}");""".format(img_url,ageCategory,latitude,longitude,rate,gender,address))
			r = json.loads(json.dumps({'gender':gender, 'rating':rate, 'ageCategory': ageCategory}, sort_keys = True,indent=4, separators=(',', ': ')))
			js.append(r)

		self.write(dict(results=js))
		self.finish()

class DbViewHandler(RequestHandler):
	def get(self):
		dbResult = _execute('select * from upload')
		dbList = []
		for i in dbResult:
			dbList.append(dict(location=i[0],url=i[2],rating=i[5],gender=i[6],ageCategory=i[7]))
		self.write(json.dumps(dict(dbResult=dbList),indent = 4))

places_img = {'Chennai': 'https://upload.wikimedia.org/wikipedia/commons/7/73/Chennai_Kathipara_bridge.jpg', 'Mumbai': 'https://upload.wikimedia.org/wikipedia/commons/6/66/Mumbai_skyline88907.jpg','Bangalore':'http://www.discoverbangalore.com/images/Slide1.jpg'}

class travelApiHandler(RequestHandler):
	@asynchronous
	@engine
	def get(self):
		location = self.get_argument('location',0)
		location = location.title()
		recommend = _execute("""select * from location where city = "{0}";""".format(location))
		js = []
		locates = []
		imgList = []
		descriptionList = []
		for row in recommend:
			locates.append(row[2].replace(' ',''))
			imgList.append(row[4])
			descriptionList.append(row[3])
		imgList.append(places_img[location])
		descriptionList.append('Hometown')
		ways = '|'.join(locates)
		client = AsyncHTTPClient()
		response = yield Task(client.fetch,'https://maps.googleapis.com/maps/api/directions/json?origin='+location+'&destination='+location+'&waypoints=optimize:true|'+ways+'&key=AIzaSyDVYEzlC_MuzKNDIwWzipvny3dkf4nSBVo')
		data = json.loads(response.body)
		count = 0
		for i in data['routes'][0]['legs']:
			start = i['start_address']
			duration = i['duration']['text']
			distance = i['distance']['text']
			end = i['end_address']
			r = dict(start=start, duration=duration,distance=distance,end= end,img= imgList[count],descrition=descriptionList[count])
			count = count+1
			js.append(r)
		self.write(dict(nearby=js))
		self.finish()

class budgetApiHandler(RequestHandler):
	def get(self):
		city = self.get_argument('city',0)
		living = self.get_argument('living', 0)
		hotelsFetch = _execute("""select * from hotels where hotel_type="{0}" and hotel_city="{1}";""".format(living,city.title()))
		hotel = []
		for i in hotelsFetch:
			hotel.append(dict(name=i[1],rating=i[2],facilities=i[3],review=i[4]))
		self.write(dict(hotels=hotel))

class ratingApiHandler(RequestHandler):
	@asynchronous
	@engine
	def get(self):
		sum = 0
		counter = 0
		latitude = self.get_argument('latitude',12.9692)
		longitude = self.get_argument('longitude',79.1559)
		client = AsyncHTTPClient()
		response = yield Task(client.fetch,'http://maps.googleapis.com/maps/api/geocode/json?latlng='+str(latitude)+','+str(longitude)+'&sensor=true')
		data = json.loads(response)
		age = {'old_age':0,'youth':0,'teen':0,'kids':0}
		address = data['results'][0]['formatted_address']
		query = _execute(""" select * from upload where location = "{0}"; """.format(address))
		for i in query:
			sum=sum+int(i[5])
			if(str(i[7])=='Old Age'):
				age['old_age']=age['old_age']+1
			elif(str(i[7])=='Youth'):
				age['youth']=age['youth']+1
			elif(str(i[7])=='Teenageer'):
				age['teen']=age['teen']+1
			else:
				age['kids']=age['kids']+1
			counter = counter+1
		age_group = ''
		if(age['old_age']>age['youth'] and age['old_age']>age['teen'] and age['old_age']>age['kids']):
			age_group = "Old Age"
		elif(age['youth']>age['old_age'] and age['youth']>age['teen'] and age['youth']>age['kids']):
			age_group = "Kids"
		elif(age['teen']>age['youth'] and age['teen'] > age['kids'] and age['teen'] > age['old_age']):
			age_group = "Teenageer"
		elif(age['kids']>age['youth'] and age['kids']>age['teen'] and age['kids']>age['old_age']):
			age_group = "Kids"
		averageRating = float(sum)/float(counter)
		self.write(dict(age_group=age_group,rating=averageRating))
		self.finish()

#Application initialization
application = Application([
	(r"/", MainHandler),
	(r"/imagerate", ImageRateHandler),
	(r"/db", DbViewHandler),
	(r"/travelApi", travelApiHandler),
	(r"/budgetApi", budgetApiHandler),
	(r"/ratingApi", ratingApiHandler)
], debug = True)

#main init
if __name__ == "__main__":
	port = int(os.environ.get('PORT',80))
	http_server = HTTPServer(application)
	http_server.listen(port)
	#print 'Listening to port http://127.0.0.1:%d' % port
	IOLoop.current().start()