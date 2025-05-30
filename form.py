from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import (
    StringField,
    TextAreaField,
    PasswordField,
    BooleanField,
    SelectField,
    IntegerField,
    EmailField,
    SubmitField,
)
from wtforms.validators import DataRequired, Length, Optional

class LoginForm(FlaskForm):
    email = EmailField("Почта", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    remember = BooleanField("Запомнить меня")

class RegisterForm(FlaskForm):
    email = EmailField("Почта", validators=[DataRequired()])
    password = PasswordField("Пароль", validators=[DataRequired()])
    password_again = PasswordField("Повторите пароль", validators=[DataRequired()])
    name = StringField("Имя пользователя", validators=[DataRequired()])
    age = IntegerField("Возраст", validators=[DataRequired()])
    gender = SelectField(
        "Пол",
        choices=[
            "Мужской",
            "Женский",
        ],
    )
    weight = IntegerField("Вес", validators=[DataRequired()])
    height = IntegerField("Рост", validators=[DataRequired()])
    activity_level = SelectField(
        "Активность",
        choices=[
            "сидячий образ жизни",
            "лёгкая активность (упражнения 1–3 раза в неделю)",
            "умеренная активность (упражнения 3–5 раз в неделю)",
            "высокая активность (упражнения 6–7 раз в неделю)",
            "очень высокая активность (упражнения каждый день или физическая работа)"
        ],
    )
    goal = SelectField(
        "Цель",
        choices=[
            "ЗОЖ",
            "похудение",
            "набор массы"
        ],
    )
    dietary_restrictions = TextAreaField("Ограничения", validators=[DataRequired()])
    submit = SubmitField("Зарегистрироваться")