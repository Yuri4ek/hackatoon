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


app = Flask(__name__)
api = Api(app)
app.config["SECRET_KEY"] = "secret-key"

# Инициализация менеджера авторизации
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Маршруты
@app.route('/')
def index():
    return render_template('index.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Получаем данные из формы
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        agree_terms = request.form.get('agree_terms')

        # Дополнительные поля профиля
        age = request.form.get('age', '').strip()
        gender = request.form.get('gender', '').strip()
        weight = request.form.get('weight', '').strip()
        height = request.form.get('height', '').strip()
        activity_level = request.form.get('activity_level', '').strip()
        goal = request.form.get('goal', '').strip()
        dietary_restrictions = request.form.getlist('dietary_restrictions')

        # Валидация основных полей
        errors = []

        if not name or len(name) < 2:
            flash('Имя должно содержать минимум 2 символа', 'name_error')
            errors.append('name')

        if not email:
            flash('Email обязателен для заполнения', 'email_error')
            errors.append('email')
        elif '@' not in email or '.' not in email:
            flash('Введите корректный email адрес', 'email_error')
            errors.append('email')

        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'password_error')
            errors.append('password')

        if password != confirm_password:
            flash('Пароли не совпадают', 'confirm_password_error')
            errors.append('confirm_password')

        if not agree_terms:
            flash('Необходимо согласиться с условиями использования', 'terms_error')
            errors.append('terms')

        # Валидация дополнительных полей (если заполнены)
        if age and (not age.isdigit() or int(age) < 10 or int(age) > 100):
            flash('Возраст должен быть от 10 до 100 лет', 'age_error')
            errors.append('age')

        if weight and (not weight.replace('.', '').isdigit() or float(weight) < 30 or float(weight) > 300):
            flash('Вес должен быть от 30 до 300 кг', 'weight_error')
            errors.append('weight')

        if height and (not height.replace('.', '').isdigit() or float(height) < 100 or float(height) > 250):
            flash('Рост должен быть от 100 до 250 см', 'height_error')
            errors.append('height')

        # Проверка на существование пользователя
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == email).first():
            flash('Пользователь с таким email уже зарегистрирован', 'email_error')
            errors.append('email')

        if errors:
            return render_template('register.html')

        # Создание нового пользователя
        try:
            user = User(
                name=name,
                email=email,
                age=int(age) if age else None,
                gender=gender if gender else None,
                weight=float(weight) if weight else None,
                height=float(height) if height else None,
                activity_level=activity_level if activity_level else None,
                goal=goal if goal else None
            )
            user.set_password(password)

            # Устанавливаем диетические ограничения
            if dietary_restrictions:
                user.set_dietary_restrictions_list(dietary_restrictions)

            User.session.add(user)
            User.session.commit()

            # Автоматический вход после регистрации
            login_user(user)
            flash(f'Добро пожаловать в NutriPlan, {user.name}!', 'success')

            # Если профиль заполнен частично, перенаправляем на его завершение
            if not all([user.age, user.gender, user.weight, user.height]):
                flash('Завершите заполнение профиля для получения персональных рекомендаций', 'info')
                return redirect(url_for('profile'))
            else:
                return redirect(url_for('dashboard'))

        except Exception as e:
            flash('Произошла ошибка при регистрации. Попробуйте еще раз.', 'error')
            return render_template('register.html')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()

        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard'))
        else:
            flash('Неверное имя пользователя или пароль')

    return render_template('login.html')


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


@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        try:
            # Основная информация
            current_user.name = request.form.get('name', '').strip()
            current_user.age = int(request.form['age']) if request.form.get('age') else None
            current_user.gender = request.form.get('gender') if request.form.get('gender') else None
            current_user.weight = float(request.form['weight']) if request.form.get('weight') else None
            current_user.height = float(request.form['height']) if request.form.get('height') else None
            current_user.activity_level = request.form.get('activity_level') if request.form.get(
                'activity_level') else None
            current_user.goal = request.form.get('goal') if request.form.get('goal') else None

            # Диетические ограничения
            dietary_restrictions = request.form.getlist('dietary_restrictions')
            current_user.set_dietary_restrictions_list(dietary_restrictions)

            User.session.commit()
            flash('Профиль успешно обновлен!', 'success')
        except ValueError as e:
            flash('Пожалуйста, проверьте правильность введенных данных', 'error')
        except Exception as e:
            User.session.rollback()
            flash('Произошла ошибка при сохранении профиля', 'error')

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


def generate_chatbot_response(message, user):
    api_key = "NmU2ZTUyODAtNjRjYS00MzkwLWI0NjItNGZjNzBlNzQ1MzliOjNkNTBjNzk5LWEzMDgtNDZlZS04Mzg1LWY2N2M2NTc5NmRhNQ=="

    def get_ai_answer(text, age, gender, weight, height, activity, goal, dietary):
        text += f", {age} лет, {gender}, вес {weight} кг, рост {height} см, {activity}, цель - {goal}, противопоказания: {dietary}, пиши кратко, только то, что спросили"

        giga = GigaChat(
            credentials=api_key,
            scope="GIGACHAT_API_PERS",  # Для физлиц (альтернативы: GIGACHAT_API_B2B/CORP)
            verify_ssl_certs=False  # Отключение проверки сертификатов (не рекомендуется для прода)
        )

        response = giga.chat(text)
        print(response.choices[0].message.content)

        print(f"Потрачено токенов: {response.usage.total_tokens}")

    test_data = [message, user.age, user.gender, user.width, user.height, user.activity_level, user.goal, user.dietary_restrictions]

    get_ai_answer(*test_data)

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
    recent_messages = User_Query.query.filter_by(user_id=current_user.id) \
        .order_by(User_Query.created_at.desc()) \
        .limit(10).all()
    recent_messages.reverse()  # Показываем в хронологическом порядке

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
    data = request.get_json()
    message = data.get('message', '').strip()

    if not message:
        return jsonify({"error": "Сообщение не может быть пустым"}), 400

    try:
        # Генерируем ответ чат-бота
        response = generate_chatbot_response(message, current_user)

        # Сохраняем в базу данных
        chatbot_message = User_Query(
            user_id=current_user.id,
            message=message,
            response=response
        )
        User_Query.session.add(chatbot_message)
        User_Query.session.commit()

        return jsonify({
            "message": message,
            "response": response,
            "timestamp": datetime.now().strftime("%H:%M")
        })

    except Exception as e:
        User_Query.session.rollback()
        return jsonify({"error": "Произошла ошибка при обработке сообщения"}), 500

def main():
    # Инициализация бд (указывать абсолютный путь при хостинге)
    db_session.global_init("db/blogs.db")
    db_sess = db_session.create_session()
    # Проверяем, существует ли администратор
    app.run(port=8080, host="127.0.0.1", debug=True)


if __name__ == "__main__":
    main()