# -*- coding: utf-8 -*-
import web
import urllib,re
import datetime
try:
    import json
except ImportError:
    import simplejson as json
from google.appengine.ext import db
from google.appengine.api import urlfetch
from google.appengine.api import users
from google.appengine.api import mail
from google.appengine.api import app_identity
#时区修正参数 如果你不在中国请修改相应时区(etc:china GMT+8)
TIMEZONE_DELTA = 8
#指定邮箱进行接收邮件提示,
#如果不希望邮件提醒请留空，切勿随意填写！！！
EMAIL=''
# G+ API key 访问https://code.google.com/apis/console/获取
key = ''
#www.ingress.com 提取 cookie ACSID 注意；填写在单引号内
acsid=''
#www.ingress.com 提取 cookie csrftoken
csrftoken = ''

urls = (
	'/','index',
	'/auto','Auto',
)
app=web.application(urls,globals())
#用于存储已提交的passcode
class passcodes(db.Model):
	passcode=db.StringProperty()
#用于存储提交结果
class results(db.Model):
	passcode=db.StringProperty()
	posttime = db.DateTimeProperty()
	result=db.TextProperty()
#BackGroundServices
class BGS:
	def checknew(self):
		gplusaddr = 'https://www.googleapis.com/plus/v1/activities?query=passcode&maxResults=20&fields=items(annotation%2Cobject(attachments%2Fcontent%2Ccontent%2CoriginalContent)%2Ctitle)%2Ctitle&key='+ key
		lastest = []
		try:
			page=urllib.urlopen(gplusaddr)
			data=page.read()
			new1 = re.findall('\d[A-Za-z]{2}\d[A-Za-z]{3,40}\d[A-Za-z]\d[A-Za-z]', data)
			new2 = re.findall('[A-Za-z]{4,40}\d{2}[A-Za-z]', data)
			new3 = re.findall('82666\d{5,6}', data)
			old = passcodes.all()
			oldpasscodes = []
			for each in old:
				oldpasscodes.append(each.passcode)
			for each in new1+new2+new3:
				if each not in lastest +oldpasscodes:
					lastest.append(each)
			return lastest
		except :
			return lastest
	def  getResult(self,response):
		if response.status_code == 200:  
			try:
				ap = json.loads(response.content)['gameBasket']['playerEntity'][2]['playerPersonal']['ap']
				ap_inc = json.loads(response.content)['result']['apAward']
				xm_inc = json.loads(response.content)['result']['xmAward']
				inventoryAward = json.loads(response.content)['result']['inventoryAward']
				newItems = {}
				for i in range(len(inventoryAward)):
					if len(inventoryAward[i][2]) == 2:
						item = '%s Portal Shield' %inventoryAward[i][2]['modResource']['rarity']
					elif len(inventoryAward[i][2]) == 3:
						item = 'L%i Resonator' %inventoryAward[i][2]['resourceWithLevels']['level']
					else:
						item = 'L%i XMP' %inventoryAward[i][2]['resourceWithLevels']['level']
					if item not in newItems:
						newItems[item] = 0
					newItems[item] += 1
				doc = 'Total: '+ap+'AP; Gained: '+ap_inc+'AP, '+xm_inc+'XM; '
				for item in newItems:
					doc += item+' x '+str(newItems[item])+'; '
			except:
				doc = json.loads(response.content)['error']
			
		else:
			doc = str(response.status_code)
		return doc
	def LocalTime(self):
		return datetime.datetime.now() + datetime.timedelta(hours=TIMEZONE_DELTA)
	def mailRemind(self,passcode,posttime,result):
		if mail.is_email_valid(EMAIL):
			appid = app_identity.get_application_id()
			sender_address = "passcode@"+appid+".appspotmail.com"
			user_address = EMAIL
			subject = "Ingress Passcode :"+passcode
			body = u"""
				Passcode :%s 
				在%s提交。
				结果为:
				%s。
				感谢使用PasscodeAuto
				这是一封自动发送邮件 请勿回复 后果自负。
				如有任何问题G+: +Houfukude Clarke
				程序更新地址:
				https://code.google.com/p/kissshell/downloads/list?can=1
					
					""" % (passcode,posttime,result)
			mail.send_mail(sender_address, user_address, subject, body)
#通过cookies模拟用户提交行为
class Ingress:
	def __init__(self,csrftoken,acsid):
		self.csrftoken = csrftoken
		self.cookie = 'ACSID='+acsid+';csrftoken='+csrftoken
	def submit(self,passcode):
		url = 'http://www.ingress.com/rpc/dashboard.redeemReward'
		data_json = json.dumps({"passcode":passcode,"method":"dashboard.redeemReward"}) 
		headers = {
			'X-Requested-With':'XMLHttpRequest',
			'X-CSRFToken':self.csrftoken,
			'Cookie':self.cookie,
			}
		response = urlfetch.fetch(url=url, payload=data_json,method=urlfetch.POST,headers=headers,allow_truncated=True,deadline=30)
		t =BGS().LocalTime()
		doc = BGS().getResult(response)
		res = results(passcode=passcode, posttime =t ,result=doc)
		res.put()
		BGS().mailRemind(passcode=passcode, posttime =t ,result=doc)
#抓取G+上的passcode并提交	
class Auto:
	def GET(self):
		res = BGS().checknew()
		if len(res)>0:
			ingress = Ingress(csrftoken,acsid)
			for each in res:
				ingress.submit(each)
				passcode = passcodes(passcode = each)
				passcode.put()
			return 'post success<br/>'
		else:
			return 'oops.no new passcodes<br/>'

#首页
class index:
	def GET(self):
		MyResult = results.all()
		style=u"<style type='text/css'>p{margin: 0;padding: 0;border: 0;font-size: 14px;font-family: '微软雅黑', '宋体', 'Arial Narrow', HELVETICA;}.code{font-size:20px;color:#2384d5;height:30px;display:block;line-height:30px;font-weight:bold;margin:20px 0;padding-left: 30px;}.pass_code{padding-left:70px;margin:10px 0;}.source{margin-top: 20px;padding-left: 50px;font-weight: bold;color: #9c0;}</style>"

		current ="<p class='code'>Passcode from Google+:</p>"

		currenttime = BGS().LocalTime()
		for each in MyResult:
			if (currenttime - each.posttime).seconds<300:
				current = current+"<p class='pass_code'>"+each.passcode+"</p>"
		return  style+current+"<p class='source'>Checked every 5 mins<br/>Hosted on GAE <a style='color: #f04381;' href='http://www.houfukude.tk/2013/01/17/PasscodeAuto'>source</a></p>"
#系统跑起来 = =！
app.cgirun()
