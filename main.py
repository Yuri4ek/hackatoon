import random

from flask import Flask, render_template, redirect, url_for, flash, abort, request, jsonify
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from flask_restful import abort, Api

from datetime import datetime, date, timedelta
from data import db_session
from data.user import User
from data.user_query import User_Query
from data.food_entry import FoodEntry
from data.meal_plan import MealPlan

from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

from form import RegisterForm, LoginForm

app = Flask(__name__)
api = Api(app)
app.config["SECRET_KEY"] = "secret-key"

# Инициализация менеджера авторизации
login_manager = LoginManager()
login_manager.init_app(app)


@app.context_processor
def utility_processor():
    def calculate_bmr(user):
        if not all([user.age, user.gender, user.weight, user.height, user.activity_level]):
            return None

        # Приводим значения к нужному формату для функции answer_bennedict
        gender_map = {'male': 'мужчина', 'female': 'женщина'}
        activity_map = {
            'sedentary': 'сидячий образ жизни',
            'light': 'лёгкая активность',
            'moderate': 'умеренная активность',
            'active': 'высокая активность',
            'very_active': 'очень высокая активность'
        }
        goal_map = {
            'weight_loss': 'похудеть',
            'muscle_gain': 'набрать массу',
            'maintenance': 'поддержание'
        }

        try:
            return answer_bennedict(
                age=user.age,
                gender=gender_map.get(user.gender, 'мужчина'),
                weight=user.weight,
                height=user.height,
                activity=activity_map.get(user.activity_level, 'сидячий образ жизни'),
                goal=goal_map.get(user.goal, 'поддержание')
            )
        except:
            return None

    return dict(calculate_bmr=calculate_bmr)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    # Современный способ (SQLAlchemy 2.0 style)
    return db_sess.get(User, user_id)


# Маршруты
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            email=form.email.data,
            age=form.age.data,
            gender=form.gender.data,
            weight=form.weight.data,
            height=form.height.data,
            activity_level=form.activity_level.data,
            goal=form.goal.data,
            dietary_restrictions=form.dietary_restrictions.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


# app.py (обработчик)
@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()

        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect(url_for('index'))

        flash('Неправильный email или пароль', 'error')
        return redirect(url_for('login'))

    return render_template('login.html', title='Авторизация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Вы успешно вышли из системы', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    today = date.today()
    today_entries = FoodEntry.query.filter_by(user_id=current_user.id, date=today).all()

    total_calories = sum(entry.calories for entry in today_entries)
    total_protein = sum(entry.protein for entry in today_entries)
    total_carbs = sum(entry.carbs for entry in today_entries)
    total_fat = sum(entry.fat for entry in today_entries)

    target_calories = current_user.calculate_bmr() if current_user.calculate_bmr() else 2000

    return render_template('dashboard.html',
                           total_calories=total_calories,
                           total_protein=total_protein,
                           total_carbs=total_carbs,
                           total_fat=total_fat,
                           target_calories=target_calories,
                           today_entries=today_entries)


def answer_bennedict(age, gender, weight, height, activity, goal):  # Подсчет кол.
    bmr = 88.36 + (13.4 * weight) + (4.8 * height) - (5.7 * age) if gender == 'мужчина' else 447.6 + (9.2 * weight) + (
            3.1 * height) - (4.3 * age)
    activityes = {
        'сидячий образ жизни': 1.2,
        'лёгкая активность': 1.375,
        'умеренная активность': 1.55,
        'высокая активность': 1.725,
        'очень высокая активность': 1.9
    }
    bmr *= activityes[activity]
    if goal == 'похудеть':
        bmr -= bmr / 10
    else:
        bmr += bmr / 10 if goal == 'набрать массу' else bmr
    return bmr


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        db_sess = db_session.create_session()
        try:
            user = db_sess.query(User).get(current_user.id)

            # Основная информация
            user.name = request.form.get('name', '').strip()
            user.age = int(request.form['age']) if request.form.get('age') else None
            user.gender = request.form.get('gender') if request.form.get('gender') else None
            user.weight = float(request.form['weight']) if request.form.get('weight') else None
            user.height = float(request.form['height']) if request.form.get('height') else None
            user.activity_level = request.form.get('activity_level') if request.form.get('activity_level') else None
            user.goal = request.form.get('goal') if request.form.get('goal') else None

            # Диетические ограничения (сохраняем как строку с разделителями)
            dietary_restrictions = request.form.getlist('dietary_restrictions')
            user.dietary_restrictions = ','.join(dietary_restrictions) if dietary_restrictions else None

            db_sess.commit()
            flash('Профиль успешно обновлен!', 'success')
        except ValueError as e:
            flash('Пожалуйста, проверьте правильность введенных данных', 'error')
        except Exception as e:
            db_sess.rollback()
            flash(f'Произошла ошибка при сохранении профиля: {str(e)}', 'error')
        finally:
            db_sess.close()

        return redirect(url_for('profile'))

    return render_template('profile.html')


@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form['current_password']
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']

        if not current_user.check_password(current_password):
            flash('Неверный текущий пароль', 'error')
            return render_template('change_password.html')

        if len(new_password) < 6:
            flash('Новый пароль должен содержать минимум 6 символов', 'error')
            return render_template('change_password.html')

        if new_password != confirm_password:
            flash('Новые пароли не совпадают', 'error')
            return render_template('change_password.html')

        current_user.set_password(new_password)
        User.session.commit()
        flash('Пароль успешно изменен!', 'success')
        return redirect(url_for('profile'))

    return render_template('change_password.html')


# Остальные маршруты остаются без изменений...
@app.route('/meal_planner')
@login_required
def meal_planner():
    selected_date = request.args.get('date', date.today().isoformat())
    selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()

    meal_plans = MealPlan.query.filter_by(user_id=current_user.id, date=selected_date).all()

    meals_by_type = {
        'breakfast': [m for m in meal_plans if m.meal_type == 'breakfast'],
        'lunch': [m for m in meal_plans if m.meal_type == 'lunch'],
        'dinner': [m for m in meal_plans if m.meal_type == 'dinner'],
        'snack': [m for m in meal_plans if m.meal_type == 'snack']
    }

    return render_template('meal_planner.html',
                           selected_date=selected_date,
                           meals_by_type=meals_by_type)


@app.route('/nutrition_analysis')
@login_required
def nutrition_analysis():
    selected_date = request.args.get('date', date.today().isoformat())
    selected_date = datetime.strptime(selected_date, '%Y-%m-%d').date()

    entries = FoodEntry.query.filter_by(user_id=current_user.id, date=selected_date).all()

    total_calories = sum(entry.calories for entry in entries)
    total_protein = sum(entry.protein for entry in entries)
    total_carbs = sum(entry.carbs for entry in entries)
    total_fat = sum(entry.fat for entry in entries)

    target_calories = current_user.calculate_bmr() if current_user.calculate_bmr() else 2000

    return render_template('nutrition_analysis.html',
                           selected_date=selected_date,
                           entries=entries,
                           total_calories=total_calories,
                           total_protein=total_protein,
                           total_carbs=total_carbs,
                           total_fat=total_fat,
                           target_calories=target_calories)


@app.route('/knowledge_base')
def knowledge_base():
    return render_template('knowledge_base.html')


@app.route('/lifestyle_tips')
def lifestyle_tips():
    return render_template('lifestyle_tips.html')


# API маршруты
@app.route('/api/nutrition_data')
@login_required
def nutrition_data():
    days = int(request.args.get('days', 7))
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    entries = FoodEntry.query.filter(
        FoodEntry.user_id == current_user.id,
        FoodEntry.date >= start_date,
        FoodEntry.date <= end_date
    ).all()

    daily_data = {}
    for entry in entries:
        date_str = entry.date.isoformat()
        if date_str not in daily_data:
            daily_data[date_str] = {'calories': 0, 'protein': 0, 'carbs': 0, 'fat': 0}

        daily_data[date_str]['calories'] += entry.calories
        daily_data[date_str]['protein'] += entry.protein
        daily_data[date_str]['carbs'] += entry.carbs
        daily_data[date_str]['fat'] += entry.fat

    return jsonify(daily_data)


def get_ai_answer(text, age, gender, weight, height, activity, goal, dietary):
    api_key = "NmU2ZTUyODAtNjRjYS00MzkwLWI0NjItNGZjNzBlNzQ1MzliOjNkNTBjNzk5LWEzMDgtNDZlZS04Mzg1LWY2N2M2NTc5NmRhNQ=="

    text += f", {age} лет, {gender}, вес {weight} кг, рост {height} см, {activity}, цель - {goal}, противопоказания: {dietary}, пиши кратко, только то, что спросили"

    giga = GigaChat(
        credentials=api_key,
        scope="GIGACHAT_API_PERS",  # Для физлиц (альтернативы: GIGACHAT_API_B2B/CORP)
        verify_ssl_certs=False  # Отключение проверки сертификатов (не рекомендуется для прода)
    )

    response = giga.chat(text)
    return response.choices[0].message.content


def generate_chatbot_response(message, user):
    test_data = [message, user.age, user.gender, user.weight, user.height, user.activity_level, user.goal,
                 user.dietary_restrictions]

    return get_ai_answer(*test_data)


@app.route('/api/chatbot/history')
@login_required
def chatbot_history():
    """API для получения истории чат-бота"""
    messages = User_Query.query.filter_by(user_id=current_user.id) \
        .order_by(User_Query.created_at.desc()) \
        .limit(50).all()

    history = []
    for msg in reversed(messages):
        history.append({
            "id": msg.id,
            "message": msg.message,
            "response": msg.response,
        })

    return jsonify(history)


# Чат-бот
@app.route('/chatbot')
@login_required
def chatbot():
    """Страница чат-бота"""
    # Получаем последние сообщения пользователя с чат-ботом
    db_sess = db_session.create_session()
    recent_messages = db_sess.query(User_Query).filter(User_Query.user_id == current_user.id).all()

    return render_template('chatbot.html', recent_messages=recent_messages)


@app.route('/api/messages', methods=['POST'])
@login_required
def send_message():
    """API для отправки сообщения"""
    content = request.json.get('content')
    if not content or content.strip() == '':
        return jsonify({"error": "Сообщение не может быть пустым"}), 400

    # Здесь в реальном приложении вы бы сохраняли сообщение в базу данных
    # Для демонстрации просто возвращаем сообщение с ID
    message = {
        "id": 999,  # В реальном приложении это был бы ID из базы данных
        "sender_id": current_user.id,
        "sender_name": current_user.name,
        "content": content,
    }

    # Имитация ответа от консультанта через 1-2 секунды
    # В реальном приложении здесь был бы WebSocket или периодический опрос

    return jsonify(message)


@app.route('/api/chatbot', methods=['POST'])
@login_required
def chatbot_api():
    """API для обработки сообщений чат-бота"""
    db_sess = db_session.create_session()

    data = request.get_json()
    message = data.get('message', '').strip()

    if not message:
        return jsonify({"error": "Сообщение не может быть пустым"}), 400

    try:
        # Генерируем ответ чат-бота
        response = generate_chatbot_response(message, current_user)
        print(response)

        # Сохраняем в базу данных
        chatbot_message = User_Query(
            user_id=current_user.id,
            message=message,
            response=response
        )
        db_sess.add(chatbot_message)
        db_sess.commit()

        return jsonify({
            "message": message,
            "response": response,
            "timestamp": datetime.now().strftime("%H:%M")
        })

    except Exception as e:
        return jsonify({"error": "Произошла ошибка при обработке сообщения"}), 500


def main():
    # Инициализация бд (указывать абсолютный путь при хостинге)
    db_session.global_init("db/blogs.db")
    db_sess = db_session.create_session()
    # Проверяем, существует ли администратор
    app.run(port=8080, host="127.0.0.1", debug=True)


if __name__ == "__main__":
    main()
