# coding:utf-8
from flask import request, render_template, jsonify, session, url_for, redirect
import urllib2
import json
import datetime

from main import db, User, Authority, Subscribe, ConferenceRoom

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField
from wtforms.validators import InputRequired

from . import app_conference_room

# 常量
WECHAT_TOKEN = "my_wx"
WECHAT_APPID = "wxaadcc3975c2e4428"
WECHAT_APPSECRET = "9dffbcb0ccb7cafddb65ee2e118cfb99"

# 定义预约表单
class ConditionForm(FlaskForm):

	conference_room_id = HiddenField()


@app_conference_room.route("/conference_room_condition", methods=["GET", "POST"])
def conference_room_condition():
	form = ConditionForm()

	# 查询会议室信息
	conference_rooms = ConferenceRoom.query.all()

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
					# 为新创建的用户设置权限并保存
					user = User(openid=user_dict_data.get("openid"), authority_id=authority.id)
					db.session.add(user)
					db.session.commit()
				except Exception as e:
					db.session.rollback()
					raise

			# 将用户的数据填充到页面中
			return render_template("conference_room_condition.html", conference_rooms=conference_rooms, form=form)


@app_conference_room.route("/select_conference_room_condition", methods=["GET", "POST"])
def select_conference_room_condition():
	
	form = ConditionForm()

	# 查询会议室信息
	conference_rooms = ConferenceRoom.query.all()
	# 判断表单中的数据是否合理
	if form.validate_on_submit():
		# 表示验证合格
		# 提取数据
		conference_room_id = form.conference_room_id.data

		conference_room = ConferenceRoom.query.filter_by(id=conference_room_id).first()

		db.session.expire_all()
		db.session.flush()
		db.session.commit()

		# 查询相应的订单
		subscribes = Subscribe.query.filter(Subscribe.conference_room_id==conference_room_id, Subscribe.begin_time>datetime.datetime.now(), Subscribe.condition==1).all()

		return render_template("conference_room_condition.html", conference_rooms=conference_rooms, form=form , conference_room=conference_room, subscribes=subscribes)

	return render_template("conference_room_condition.html", conference_rooms=conference_rooms, form=form)