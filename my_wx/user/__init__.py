# coding:utf-8

from flask import Blueprint

# 创建一个蓝图
app_user = Blueprint("app_user", __name__, template_folder="templates")

from .views import user, audit, telephone, email, fail