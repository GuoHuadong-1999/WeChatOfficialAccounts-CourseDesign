# coding:utf-8

from flask import Blueprint

# 创建一个蓝图
app_conference_room = Blueprint("app_conference_room", __name__, template_folder="templates")

from .views import conference_room_condition, select_conference_room_condition