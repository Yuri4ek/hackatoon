from flask import Flask, render_template, redirect, url_for, flash, abort, request
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from flask_restful import abort, Api


from data import db_session
from data.user import User
from data.user_query import User_Query


app = Flask(__name__)
api = Api(app)
app.config["SECRET_KEY"] = "secret-key"

# Инициализация менеджера авторизации
login_manager = LoginManager(app)
login_manager.login_view = "login"

def main():
    # Инициализация бд (указывать абсолютный путь при хостинге)
    db_session.global_init("db/blogs.db")
    db_sess = db_session.create_session()
    # Проверяем, существует ли администратор
    app.run(port=8080, host="127.0.0.1", debug=True)


if __name__ == "__main__":
    main()