# coding:utf-8
from flask import request, render_template, session, redirect, url_for
from flask_mail import Message
import urllib2
import json
import time

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Regexp, InputRequired

from . import app_user

from main import db, mail, User, Authority, Subscribe

# 常量
WECHAT_TOKEN = "my_wx"
WECHAT_APPID = "wxaadcc3975c2e4428"
WECHAT_APPSECRET = "9dffbcb0ccb7cafddb65ee2e118cfb99"

class EmailForm(FlaskForm):
	email = StringField(label=u"电子邮箱:", validators=[InputRequired(u"您未填写该字段！"), Regexp(r"[1-9][0-9]{4,}@qq.com", message=u"请输入正确的QQ邮箱！")])
	
	submit = SubmitField(label=u"确认")


class TelephoneForm(FlaskForm):
	telephone = StringField(label=u"手机号:", validators=[InputRequired(u"您未填写该字段！"), Regexp(r"^1[3|4|5|6|7|8][0-9]{9}$", message=u"请输入正确的手机号！")])
	
	submit = SubmitField(label=u"确认")


@app_user.route("/user", methods = ["GET", "POST"])
def user():
	# 表示是微信发送的请求
	if request.method == "GET":
		""""让用户通过微信访问网页页面的视图"""
		# 从微信服务器中拿用户的数据
		# 1. 拿code参数
		code = request.args.get("code")

		if not code:
			return u"缺失code参数"

		# 2. 向微信服务其发送http请求，获取access_token
		url = " https://api.weixin.qq.com/sns/oauth2/access_token?appid=%s&secret=%s&code=%s&grant_type=authorization_code" % (WECHAT_APPID, WECHAT_APPSECRET, code)
		response = urllib2.urlopen(url)

		# 获取相应体数据，微信返回的json数据
		json_str = response.read()
		resp_dict = json.loads(json_str)

		# 提取access_token
		if"errcode" in resp_dict:
			return u"获取access_token失败"

		access_token = resp_dict.get("access_token")
		open_id = resp_dict.get("openid")  # 用户的编号

		# 3. 向微信服务器发送http请求获取用户的数据
		url = "https://api.weixin.qq.com/sns/userinfo?access_token=%s&openid=%s&lang=zh_CN" % (access_token,open_id)

		response = urllib2.urlopen(url)

		# 读取微信传回的json的响应体数据
		user_json_str = response.read()
		user_dict_data = json.loads(user_json_str)

		if"errcode" in resp_dict:
			return u"获取用户信息失败"
		else:
			# 将用户的数据保存在session中
			session["user"] = user_dict_data

			# 查询openid对应的用户
			user = User.query.filter_by(openid=user_dict_data.get("openid")).first()

			#判断数据库中是否已有此用户
			if user is None:
				# 查询权限为管理员的记录
				authority = Authority.query.filter_by(authority="user").first()

				try:
					#为新创建的用户设置权限并保存
					user = User(openid=user_dict_data.get("openid"), authority_id=authority.id)
					db.session.add(user)
					db.session.commit()
				except Exception as e:
					db.session.rollback()
					raise

			# 根据openid查询用户的手机号和电子邮箱
			telephone = user.telephone
			email = user.email

			# 将用户的数据填充到页面中
			return render_template("user.html", user=user_dict_data, telephone=telephone, email=email)
	else:
		return render_template("user.html")


@app_user.route("/audit", methods = ["GET", "POST"])
def audit():
	# 表示是微信发送的请求
	if request.method == "GET":
		""""让用户通过微信访问网页页面的视图"""
		# 从微信服务器中拿用户的数据
		# 1. 拿code参数
		code = request.args.get("code")

		if not code:
			return u"缺失code参数"

		# 2. 向微信服务其发送http请求，获取access_token
		url = " https://api.weixin.qq.com/sns/oauth2/access_token?appid=%s&secret=%s&code=%s&grant_type=authorization_code" % (WECHAT_APPID, WECHAT_APPSECRET, code)
		response = urllib2.urlopen(url)

		# 获取相应体数据，微信返回的json数据
		json_str = response.read()
		resp_dict = json.loads(json_str)

		# 提取access_token
		if"errcode" in resp_dict:
			return u"获取access_token失败"

		access_token = resp_dict.get("access_token")
		open_id = resp_dict.get("openid")  # 用户的编号

		# 3. 向微信服务器发送http请求获取用户的数据
		url = "https://api.weixin.qq.com/sns/userinfo?access_token=%s&openid=%s&lang=zh_CN" % (access_token,open_id)

		response = urllib2.urlopen(url)

		# 读取微信传回的json的响应体数据
		user_json_str = response.read()
		user_dict_data = json.loads(user_json_str)

		if"errcode" in resp_dict:
			return u"获取用户信息失败"
		else:
			# 将用户的数据保存在session中
			session["user"] = user_dict_data

			# 查询openid对应的用户
			user = User.query.filter_by(openid=user_dict_data.get("openid")).first()

			#判断数据库中是否已有此用户
			if user is None:
				# 查询权限为管理员的记录
				authority = Authority.query.filter_by(authority="user").first()

				try:
					#为新创建的用户设置权限并保存
					user = User(openid=user_dict_data.get("openid"), authority_id=authority.id)
					db.session.add(user)
					db.session.commit()
				except Exception as e:
					db.session.rollback()
					raise

			if user.authority.authority=="administrator":

				# 清除缓存
				db.session.expire_all()
				db.session.flush()
				db.session.commit()

				# 查询未审核的订单，并按开始时间进行排序
				subscribes = Subscribe.query.filter_by(condition=2).order_by("begin_time").all()
			else:
				return redirect(url_for("app_user.fail"))

			openid_list = []
			conference_room_list = []
			index = 0
			index_list = []

			for subscribe in subscribes:
				openid_list.append(subscribe.user.openid)
				conference_room_list.append(subscribe.conference_room.conference_room)
				index_list.append(index)
				index = index + 1
				
			# 将用户的数据填充到页面中
			return render_template("audit.html", subscribes=subscribes, openid_list=openid_list, conference_room_list=conference_room_list, index_list=index_list)
	else:
		time.sleep(1)
		# 获取用户选择的预约订单
		req_dict = request.get_json()
		subscribe_id = req_dict.get("subscribe_id")
		option = req_dict.get("option")


		if int(option) == 1:

			Subscribe.query.filter_by(id=int(subscribe_id)).update({"condition":1})
			db.session.commit()

			subscribe = Subscribe.query.filter_by(id=int(subscribe_id)).first()
			email = subscribe.user.email
			msg = Message(u"会议室预约成功",sender="1210446790@qq.com",recipients=[email])
			msg.body = u"您的会议室："+subscribe.conference_room.conference_room+u"，已预约成功！"

			mail.send(msg)

		else:

			Subscribe.query.filter_by(id=int(subscribe_id)).update({"condition":0})
			db.session.commit()

			subscribe = Subscribe.query.filter_by(id=int(subscribe_id)).first()
			email = subscribe.user.email
			msg = Message(u"会议室预约失败",sender=u"1210446790@qq.com",recipients=[email])
			msg.body = u"很抱歉，您的会议室:"+subscribe.conference_room.conference_room+u"，预约失败!"

			mail.send(msg)

		return json.dumps({"code":1})



@app_user.route("/telephone", methods = ["GET", "POST"])
def telephone():
	# 创建表单
	form = TelephoneForm()

	if request.method == "GET":
		return render_template("telephone.html", form=form)
	else:
		# 判断表单中的数据是否合理
		if form.validate_on_submit():
			# 表示验证合格
			# 提取数据
			telephone = form.telephone.data

			# 取出用户数据
			user_dict_data = session.get("user")

			# 查询用户，并修改用户的电子邮箱
			user = User.query.filter_by(openid=user_dict_data.get("openid")).first()
			user.telephone = telephone
			db.session.add(user)
			db.session.commit()

			email = user.email

			return render_template("user.html", user=user_dict_data, telephone=telephone, email=email)

		return render_template("telephone.html", form=form)


@app_user.route("/email", methods = ["GET", "POST"])
def email():
	# 创建表单
	form = EmailForm()

	if request.method == "GET":
		return render_template("email.html", form=form)
	else:
		# 判断表单中的数据是否合理
		if form.validate_on_submit():
			# 表示验证合格
			# 提取数据
			email = form.email.data

			# 取出用户数据
			user_dict_data = session.get("user")

			# 查询用户，并修改用户的电子邮箱
			user = User.query.filter_by(openid=user_dict_data.get("openid")).first()
			user.email = email
			db.session.add(user)
			db.session.commit()

			telephone = user.telephone

			return render_template("user.html", user=user_dict_data, telephone=telephone, email=email)

		return render_template("email.html", form=form)


@app_user.route("/fail", methods = ["GET", "POST"])
def fail():
	return render_template("fail.html")
	