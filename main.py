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
        if User.query.filter_by(email=email).first():
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
            User.session.rollback()
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
    """Генерирует ответ чат-бота на основе сообщения пользователя"""
    message_lower = message.lower()

    # Персонализированные ответы на основе профиля пользователя
    user_name = user.name if user.name else "друг"

    # Ответы на вопросы о калориях
    if any(word in message_lower for word in ['калории', 'ккал', 'энергия', 'сколько есть']):
        if user.calculate_bmr():
            bmr = user.calculate_bmr()
            return f"Привет, {user_name}! На основе вашего профиля, ваша суточная норма калорий составляет примерно {bmr:.0f} ккал. Это базовый расчет с учетом вашего возраста, веса, роста и уровня активности."
        else:
            return f"Привет, {user_name}! Чтобы рассчитать вашу суточную норму калорий, мне нужно знать ваш возраст, вес, рост и уровень активности. Заполните профиль для получения персональных рекомендаций!"

    # Ответы о БЖУ
    elif any(word in message_lower for word in ['бжу', 'белки', 'жиры', 'углеводы', 'протеин']):
        return f"Отличный вопрос, {user_name}! Оптимальное соотношение БЖУ зависит от ваших целей:\n\n🏃‍♂️ Для похудения: 30% белки, 30% жиры, 40% углеводы\n💪 Для набора массы: 25% белки, 25% жиры, 50% углеводы\n⚖️ Для поддержания: 20% белки, 30% жиры, 50% углеводы\n\nВ граммах на кг веса: белки 1.2-2г, жиры 0.8-1.2г, углеводы 3-5г."

    # Ответы о воде
    elif any(word in message_lower for word in ['вода', 'пить', 'жидкость', 'гидратация']):
        if user.weight:
            water_need = user.weight * 30
            return f"💧 {user_name}, рекомендуемая норма воды для вас: {water_need:.0f} мл в день (30 мл на кг веса). Это примерно {water_need / 250:.1f} стаканов. Увеличивайте количество при физических нагрузках!"
        else:
            return f"💧 {user_name}, общая рекомендация - 30-35 мл воды на кг веса. Для среднего человека это 2-2.5 литра в день. Заполните вес в профиле для точного расчета!"

    # Ответы о похудении
    elif any(word in message_lower for word in ['похудеть', 'сбросить', 'диета', 'вес', 'худеть']):
        return f"🎯 {user_name}, для здорового похудения:\n\n✅ Создайте дефицит 300-500 ккал в день\n✅ Ешьте больше белка (сохраняет мышцы)\n✅ Включите силовые тренировки\n✅ Пейте достаточно воды\n✅ Высыпайтесь (7-9 часов)\n\n❌ Избегайте экстремальных диет - они замедляют метаболизм!"

    # Ответы о наборе массы
    elif any(word in message_lower for word in ['набрать', 'масса', 'мышцы', 'поправиться']):
        return f"💪 {user_name}, для набора мышечной массы:\n\n✅ Профицит калорий 300-500 ккал\n✅ Белок 1.6-2.2г на кг веса\n✅ Силовые тренировки 3-4 раза в неделю\n✅ Сложные углеводы для энергии\n✅ Полноценный отдых\n\nНабирайте 0.5-1 кг в месяц для качественной массы!"

    # Ответы о продуктах
    elif any(word in message_lower for word in ['продукты', 'еда', 'что есть', 'питание']):
        restrictions = user.get_dietary_restrictions_list()
        if restrictions:
            return f"🥗 {user_name}, учитывая ваши ограничения ({', '.join(restrictions)}), рекомендую:\n\n🥬 Овощи и зелень\n🍎 Фрукты и ягоды\n🥜 Орехи и семена\n🐟 Нежирные источники белка\n🌾 Цельнозерновые продукты\n\nИзбегайте обработанных продуктов и следите за составом!"
        else:
            return f"🥗 {user_name}, основа здорового питания:\n\n🥬 Овощи (50% тарелки)\n🍗 Белки (25% тарелки)\n🌾 Сложные углеводы (25% тарелки)\n🥑 Полезные жиры\n🍎 Фрукты как перекус\n\nПринцип: чем меньше обработки, тем лучше!"

    # Ответы о тренировках
    elif any(word in message_lower for word in ['тренировки', 'спорт', 'упражнения', 'фитнес']):
        return f"🏋️‍♂️ {user_name}, питание и тренировки:\n\n⏰ За 1-2 часа до: углеводы + немного белка\n⚡ Сразу после: белки + быстрые углеводы\n💪 В дни тренировок: больше калорий и белка\n🛌 В дни отдыха: меньше углеводов, больше овощей\n\nПомните: питание = 70% результата!"

    # Ответы о витаминах
    elif any(word in message_lower for word in ['витамины', 'добавки', 'бады', 'нутриенты']):
        return f"💊 {user_name}, о витаминах и добавках:\n\n🌟 Обязательные: витамин D, B12 (особенно для веганов)\n🐟 Омега-3 (если мало рыбы)\n🦴 Кальций и магний\n🩸 Железо (при дефиците)\n\n⚠️ Лучше получать из еды! Сдайте анализы перед приемом добавок."

    # Ответы о перекусах
    elif any(word in message_lower for word in ['перекус', 'снек', 'голод', 'между едой']):
        return f"🍎 {user_name}, здоровые перекусы:\n\n✅ Орехи и семечки (горсть)\n✅ Фрукты с йогуртом\n✅ Овощи с хумусом\n✅ Творог с ягодами\n✅ Вареное яйцо\n\n❌ Избегайте: чипсы, печенье, сладости. Перекус = 10-15% от дневных калорий!"

    # Ответы о времени приема пищи
    elif any(word in message_lower for word in ['время', 'когда есть', 'режим', 'график']):
        return f"⏰ {user_name}, о режиме питания:\n\n🌅 Завтрак: в течение часа после пробуждения\n🌞 Обед: через 4-5 часов после завтрака\n🌆 Ужин: за 2-3 часа до сна\n🍎 Перекусы: при необходимости\n\nГлавное - регулярность и общий баланс калорий!"

    # Приветствие
    elif any(word in message_lower for word in ['привет', 'здравствуй', 'добро', 'начать']):
        return f"Привет, {user_name}! 👋 Я ваш персональный помощник по питанию в NutriPlan!\n\nЯ могу помочь с:\n🍎 Расчетом калорий и БЖУ\n📊 Планированием питания\n💡 Советами по здоровому образу жизни\n🥗 Рекомендациями продуктов\n\nЗадавайте любые вопросы о питании!"

    # Благодарность
    elif any(word in message_lower for word in ['спасибо', 'благодарю', 'thanks']):
        return f"Пожалуйста, {user_name}! 😊 Рад был помочь! Если у вас есть еще вопросы о питании или здоровом образе жизни, обращайтесь в любое время!"

    # Общие вопросы о здоровье
    elif any(word in message_lower for word in ['здоровье', 'самочувствие', 'энергия']):
        return f"🌟 {user_name}, для хорошего самочувствия важно:\n\n🥗 Сбалансированное питание\n💧 Достаточное количество воды\n😴 Качественный сон (7-9 часов)\n🏃‍♂️ Регулярная физическая активность\n😌 Управление стрессом\n\nВсе взаимосвязано - улучшив питание, вы почувствуете прилив энергии!"

    # Ответ по умолчанию
    else:
        responses = [
            f"Интересный вопрос, {user_name}! Я специализируюсь на вопросах питания и здорового образа жизни. Можете спросить о калориях, БЖУ, продуктах, режиме питания или планировании рациона.",
            f"{user_name}, я помогаю с вопросами питания! Спросите меня о расчете калорий, составлении рациона, выборе продуктов или здоровых привычках.",
            f"Хм, {user_name}, не совсем понял ваш вопрос. Попробуйте спросить о питании, калориях, БЖУ, продуктах или здоровом образе жизни - в этом я эксперт! 🤖"
        ]
        return random.choice(responses)

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
            "timestamp": msg.created_at.strftime("%H:%M")
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
        "timestamp": datetime.now().strftime("%H:%M")
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