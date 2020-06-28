# coding:utf-8
from flask import Flask, request, abort, render_template, url_for, session
from flask_mail import Mail, Message
import hashlib
import xmltodict
import time
import urllib2
import json
from flask_sqlalchemy import SQLAlchemy
import datetime

from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, DateTimeField, IntegerField, TextAreaField, HiddenField
from wtforms.validators import DataRequired, Regexp, NumberRange, Length, InputRequired
	

# 常量
WECHAT_TOKEN = "my_wx"
WECHAT_APPID = "wxaadcc3975c2e4428"
WECHAT_APPSECRET = "9dffbcb0ccb7cafddb65ee2e118cfb99"

app = Flask(__name__)

class Config(object):
	"""配置参数"""
	# sqlalchemy的配置参数
	SQLALCHEMY_DATABASE_URI = "mysql://root:0124ghdwin@127.0.0.1:3306/db_subscribe"

	# 设置sqlalchemy自动跟踪数据库
	SQLALCHEMY_TRACK_MODIFICATIONS = True 

	SECRET_KEY = "0124ghdwin"
	CSRF_ENABLED = True

	MAIL_SERVER = "smtp.qq.com"
	MAIL_PORT = 25
	MAIL_USE_TLS = True
	MAIL_USERNAME = "1210446790@qq.com"
	MAIL_PASSWORD = "qkhwclqnhrlnbagc"


app.config.from_object(Config)

# 创建数据库sqlalchemy工具对象
db = SQLAlchemy(app)

mail = Mail(app)

class User(db.Model):
	"""用户表"""
	__tablename__ = "subs_users"

	id = db.Column(db.Integer, primary_key=True)
	openid = db.Column(db.String(32), unique=True, nullable=False)
	# telephone = db.Column(db.String(32), unique=True, default=u"未填写")
	# email = db.Column(db.String(32), unique=True, default=u"未填写")
	telephone = db.Column(db.String(32), default=u"未填写")
	email = db.Column(db.String(32), default=u"未填写")
	position_id = db.Column(db.Integer, db.ForeignKey("subs_positions.id"))
	authority_id = db.Column(db.Integer, db.ForeignKey("subs_authoritys.id"), nullable=False)

	# 创建时间
	create_time = db.Column(db.DateTime, default=datetime.datetime.now(), nullable=False)
	# 更新时间
	update_time = db.Column(db.DateTime, default=datetime.datetime.now(), onupdate=datetime.datetime.now(), nullable=False)


	subscribes = db.relationship("Subscribe", backref="user")


class Authority(db.Model):
	"""权限表"""
	__tablename__ = "subs_authoritys"

	id = db.Column(db.Integer, primary_key=True)
	authority = db.Column(db.String(32), unique=True, nullable=False)

	# 创建时间
	create_time = db.Column(db.DateTime, default=datetime.datetime.now(), nullable=False)
	# 更新时间
	update_time = db.Column(db.DateTime, default=datetime.datetime.now(), onupdate=datetime.datetime.now(), nullable=False)

	users = db.relationship("User", backref="authority")


class Position(db.Model):
	"""职位表"""
	__tablename__ = "subs_positions"

	id = db.Column(db.Integer, primary_key=True)
	position = db.Column(db.String(32), unique=True, nullable=False)

	# 创建时间
	create_time = db.Column(db.DateTime, default=datetime.datetime.now(), nullable=False)
	# 更新时间
	update_time = db.Column(db.DateTime, default=datetime.datetime.now(), onupdate=datetime.datetime.now(), nullable=False)

	users = db.relationship("User", backref="position")


class ConferenceRoom(db.Model):
	"""会议室表"""
	__tablename__ = "subs_conference_rooms"

	id = db.Column(db.Integer, primary_key=True)
	conference_room = db.Column(db.String(32), unique=True, nullable=False)

	# 创建时间
	create_time = db.Column(db.DateTime, default=datetime.datetime.now(), nullable=False)
	# 更新时间
	update_time = db.Column(db.DateTime, default=datetime.datetime.now(), onupdate=datetime.datetime.now(), nullable=False)

	subscribes = db.relationship("Subscribe", backref="conference_room")


class Subscribe(db.Model):
	"""预约表"""
	__tablename__ = "subs_subscribes"

	id = db.Column(db.Integer, primary_key=True)
	subscribe_id = db.Column(db.String(32), unique=True, nullable=False)
	begin_time = db.Column(db.DateTime, nullable=False)
	end_time = db.Column(db.DateTime, nullable=False)
	title = db.Column(db.String(32), nullable=False)
	use = db.Column(db.String(128))
	people_number = db.Column(db.Integer, nullable=False)
	condition = db.Column(db.Integer, nullable=False)
	conference_room_id = db.Column(db.Integer, db.ForeignKey("subs_conference_rooms.id"), nullable=False)
	user_id = db.Column(db.Integer, db.ForeignKey("subs_users.id"), nullable=False)

	# 创建时间
	create_time = db.Column(db.DateTime, default=datetime.datetime.now(), nullable=False)
	# 更新时间
	update_time = db.Column(db.DateTime, default=datetime.datetime.now(), onupdate=datetime.datetime.now(), nullable=False)
	

# 引入蓝图
from conference_room import app_conference_room
from user import app_user

# 注册蓝图
app.register_blueprint(app_conference_room, url_prefix="/conference_room")
app.register_blueprint(app_user, url_prefix="/user")


# 定义预约表单
class SubscribeForm(FlaskForm):

	title = StringField(label=u"会议主题:", validators=[InputRequired(u"您未填写该字段！"), Length(1,32,message=u"字数不得超过32！")])
	begin_time = DateTimeField(label=u"开始时间:", validators=[DataRequired(u"请输入指定格式的开始时间！")])
	end_time = DateTimeField(label=u"结束时间:", validators=[DataRequired(u"请输入指定格式的结束时间！")])
	people_number = IntegerField(label=u"会议人数:", validators=[InputRequired(u"您未填写该字段！"), NumberRange(1,200,message=u"人数须在1到200范围内！")])
	use = TextAreaField(label=u"会议用途:")
	conference_room_id = HiddenField()
	
	submit = SubmitField(label=u"确认")


@app.route('/', methods = ["GET", "POST"])
def wechat():
	"""对接微信公众号服务器"""
	# 接收微信服务器发送的参数
	signature = request.args.get("signature")
	timestamp = request.args.get("timestamp")
	nonce = request.args.get("nonce")

	# 校验参数
	if not all([signature, timestamp, nonce]):
		abort(400)

	# 按照微信的流程进行计算签名
	li = [WECHAT_TOKEN, timestamp, nonce]
	# 排序
	li.sort()
	# 拼接字符串
	tmp_str = "".join(li)
	# 进行sha1加密，得到正确的签名值
	sign = hashlib.sha1(tmp_str).hexdigest()

	# 将自己计算的签名值与请求的签名参数进行对比，如果相同，则说明请求来自微信
	if signature != sign:
		# 表示不是微信发送的请求
		abort(403)
	else:
		# 表示是微信发送的请求
		if request.method == "GET":
			# 表示是第一次接入微信服务器的验证
			echostr = request.args.get("echostr")
			if not echostr:
				abort(400)
			return echostr
		elif request.method == "POST":
			# 表示微信服务器转发过来的用户的消息
			xml_str = request.data
			if not xml_str:
				abort(400)

			# 对xml字符串进行解析
			xml_dict = xmltodict.parse(xml_str)
			xml_dict = xml_dict.get("xml")

			# 提取消息类型
			msg_type = xml_dict.get("MsgType")

			if msg_type == "text":
				# 表示发送的是文本消息
				# 构造返回值，经由微信服务器回复给用户的消息内容
				resp_dict = {
					"xml": {
						"ToUserName": xml_dict.get("FromUserName"),
						"FromUserName": xml_dict.get("ToUserName"),
						"CreateTime": int(time.time()),
						"MsgType": "text",
						"Content": xml_dict.get("Content")
					}
				}
			else:
				resp_dict = {
					"xml": {
						"ToUserName": xml_dict.get("FromUserName"),
						"FromUserName": xml_dict.get("ToUserName"),
						"CreateTime": int(time.time()),
						"MsgType": "text",
						"Content": "I love you."
					}
				}

			# 将字典转换为xml字符串
			resp_xml_str = xmltodict.unparse(resp_dict)
			# 返回消息数据给微信服务器
			return resp_xml_str

@app.route("/index", methods = ["GET", "POST"])
def index():
	# 创建表单
	form = SubscribeForm()

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
					#为新创建的用户设置权限并保存
					user = User(openid=user_dict_data.get("openid"), authority_id=authority.id)
					db.session.add(user)
					db.session.commit()
				except Exception as e:
					db.session.rollback()
					raise

			# 将用户的数据填充到页面中
			return render_template("index.html", form=form, conference_rooms=conference_rooms)
	

@app.route("/subscribe", methods = ["GET", "POST"])
def subscribe():
	# 创建表单
	form = SubscribeForm()

	# 查询会议室信息
	conference_rooms = ConferenceRoom.query.all()

	# 判断表单中的数据是否合理
	if form.validate_on_submit():
		# 表示验证合格
		# 提取数据
		title = form.title.data
		begin_time = form.begin_time.data
		end_time = form.end_time.data
		people_number = form.people_number.data
		use = form.use.data
		conference_room_id = int(form.conference_room_id.data)

		# 取出用户数据
		user_dict_data = session.get("user")

		# 查询用户，并创建预约订单
		user = User.query.filter_by(openid=user_dict_data.get("openid")).first()

		subscribe = Subscribe(subscribe_id=datetime.datetime.now().strftime("%Y%m%d%H%M%S")+str(user.id),
			begin_time=begin_time,
			end_time=end_time,
			title=title,
			use=use,
			people_number=people_number,
			condition=2,
			conference_room_id=conference_room_id,
			user_id=user.id)

		db.session.add(subscribe)
		db.session.commit()

		return render_template("success.html")
	return render_template("index.html", form=form, conference_rooms=conference_rooms)


if __name__ == '__main__':
    # 清除数据库中的所有数据
    db.drop_all()

    # 创建所有的表
    db.create_all()

    # 初始化数据库
    position1 = Position(position="Student")
    position2 = Position(position="Teacher")

    authority1 = Authority(authority="administrator")
    authority2 = Authority(authority="user")

    db.session.add_all([position1, position2, authority1, authority2])
    db.session.commit()

    user = User(openid="oszXrsn-2PimON4K2cTxzxZ-dMlQ",position_id=position1.id,authority_id=authority2.id)

    conference_room1 = ConferenceRoom(conference_room="逸夫楼108")
    conference_room2 = ConferenceRoom(conference_room="逸夫楼217-1")
    conference_room3 = ConferenceRoom(conference_room="逸夫楼217-2")
    conference_room4 = ConferenceRoom(conference_room="逸夫楼217-3")
    conference_room5 = ConferenceRoom(conference_room="逸夫楼220-1")
    conference_room6 = ConferenceRoom(conference_room="逸夫楼220-2")
    conference_room7 = ConferenceRoom(conference_room="逸夫楼326")
    conference_room8 = ConferenceRoom(conference_room="逸夫楼333")
    conference_room9 = ConferenceRoom(conference_room="逸夫楼401")
    conference_room10 = ConferenceRoom(conference_room="逸夫楼414")
    conference_room11 = ConferenceRoom(conference_room="逸夫楼416")
    conference_room12 = ConferenceRoom(conference_room="逸夫楼418")
    conference_room13 = ConferenceRoom(conference_room="逸夫楼429")
    conference_room14 = ConferenceRoom(conference_room="逸夫楼431")
    conference_room15 = ConferenceRoom(conference_room="逸夫楼518")
    conference_room16 = ConferenceRoom(conference_room="逸夫楼537")

    db.session.add_all([user, conference_room1, conference_room2, conference_room3, conference_room4, conference_room5, conference_room6, conference_room7, conference_room8, conference_room9, conference_room10, conference_room11, conference_room12, conference_room13, conference_room14, conference_room15, conference_room16])
    db.session.commit()

    app.run(host="127.0.0.1", port=8000, debug=True)
