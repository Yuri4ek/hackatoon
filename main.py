from random import random

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


def answer_bennedict(user):  # Подсчет калорий
    try:
        bmr = 88.36 + (13.4 * user.weight) + (4.8 * user.height) - (
                5.7 * user.age) if user.gender == 'мужчина' else 447.6 + (9.2 * user.weight) + (
                3.1 * user.height) - (4.3 * user.age)
        activityes = {
            'сидячий образ жизни': 1.2,
            'лёгкая активность': 1.375,
            'умеренная активность': 1.55,
            'высокая активность': 1.725,
            'очень высокая активность': 1.9
        }
        bmr *= activityes[user.activity_level]
        if user.goal == 'похудеть':
            bmr -= bmr / 10
        else:
            bmr += bmr / 10 if user.goal == 'набрать массу' else bmr
        return bmr
    except Exception as e:
        app.logger.error(f"Error in answer_bennedict: {str(e)}")


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


@app.route('/add_food_entry', methods=['POST'])
@login_required
def add_food_entry():
    db_sess = db_session.create_session()

    try:
        food_entry = FoodEntry(
            user_id=current_user.id,
            date=datetime.now().date(),
            food_name=request.form['food_name'],
            meal_type=request.form['meal_type'],
            calories=float(request.form['calories']),
            protein=float(request.form.get('protein', 0)),
            carbs=float(request.form.get('carbs', 0)),
            fat=float(request.form.get('fat', 0))
        )

        db_sess.add(food_entry)
        db_sess.commit()
        flash('Запись о питании успешно добавлена!', 'success')
    except Exception as e:
        app.logger.error(f"Error in dashboard: {str(e)}")
        flash('Ошибка при добавлении записи', 'error')

    finally:
        db_sess.close()


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


def generate_meal_plan_for_user(user_id, target_date):
    """Генерация плана питания для пользователя"""
    db_sess = db_session.create_session()

    try:
        user = db_sess.get(User, user_id)
        target_calories = answer_bennedict(user)

        # Примерные блюда для генерации
        meal_database = {
            'breakfast': [
                {'name': 'Овсяная каша с ягодами', 'calories': 320, 'protein': 12, 'carbs': 58, 'fat': 6},
                {'name': 'Омлет с овощами', 'calories': 280, 'protein': 20, 'carbs': 8, 'fat': 18},
                {'name': 'Творог с фруктами', 'calories': 250, 'protein': 18, 'carbs': 25, 'fat': 8},
                {'name': 'Гранола с йогуртом', 'calories': 350, 'protein': 15, 'carbs': 45, 'fat': 12},
            ],
            'lunch': [
                {'name': 'Куриная грудка с рисом', 'calories': 450, 'protein': 35, 'carbs': 45, 'fat': 8},
                {'name': 'Рыба с овощами', 'calories': 380, 'protein': 30, 'carbs': 20, 'fat': 15},
                {'name': 'Говядина с гречкой', 'calories': 420, 'protein': 32, 'carbs': 35, 'fat': 12},
                {'name': 'Салат с курицей', 'calories': 320, 'protein': 28, 'carbs': 15, 'fat': 18},
            ],
            'dinner': [
                {'name': 'Лосось запеченный', 'calories': 350, 'protein': 40, 'carbs': 2, 'fat': 18},
                {'name': 'Куриное филе с салатом', 'calories': 300, 'protein': 35, 'carbs': 10, 'fat': 12},
                {'name': 'Творожная запеканка', 'calories': 280, 'protein': 22, 'carbs': 20, 'fat': 10},
                {'name': 'Рыбные котлеты с овощами', 'calories': 320, 'protein': 25, 'carbs': 15, 'fat': 16},
            ],
            'snack': [
                {'name': 'Греческий йогурт с орехами', 'calories': 180, 'protein': 15, 'carbs': 8, 'fat': 10},
                {'name': 'Яблоко с арахисовой пастой', 'calories': 200, 'protein': 8, 'carbs': 25, 'fat': 8},
                {'name': 'Протеиновый коктейль', 'calories': 150, 'protein': 25, 'carbs': 5, 'fat': 3},
                {'name': 'Орехи и сухофрукты', 'calories': 220, 'protein': 6, 'carbs': 20, 'fat': 14},
            ]
        }

        # Удаляем существующий план на эту дату
        db_sess.query(MealPlan).filter(
            MealPlan.user_id == user_id,
            MealPlan.date == target_date
        ).delete()

        # Генерируем новый план
        for meal_type, meals in meal_database.items():
            selected_meal = random.choice(meals)

            meal_plan = MealPlan(
                user_id=user_id,
                date=target_date,
                meal_type=meal_type,
                food_name=selected_meal['name'],
                calories=selected_meal['calories'],
                protein=selected_meal['protein'],
                carbs=selected_meal['carbs'],
                fat=selected_meal['fat']
            )
            db_sess.add(meal_plan)

        db_sess.commit()
        return True

    except Exception as e:
        db_sess.rollback()
        app.logger.error(f"Error generating meal plan: {str(e)}")
        return False
    finally:
        db_sess.close()


@app.route('/meal_planner')
@login_required
def meal_planner():
    try:
        # Получаем дату
        selected_date_str = request.args.get('date', date.today().isoformat())
        try:
            selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
        except ValueError:
            selected_date = date.today()

        db_sess = db_session.create_session()

        # Проверяем, есть ли план на эту дату
        existing_plans = db_sess.query(MealPlan).filter(
            MealPlan.user_id == current_user.id,
            MealPlan.date == selected_date
        ).all()

        has_plan = len(existing_plans) > 0

        if not has_plan:
            # Показываем страницу генерации плана
            target_calories = answer_bennedict(current_user)
            return render_template('generate_plan.html',
                                   selected_date=selected_date,
                                   target_calories=target_calories,
                                   user=current_user)

        # Группируем планы по типам приема пищи
        meals_by_type = {
            'breakfast': [],
            'lunch': [],
            'dinner': [],
            'snack': []
        }

        for meal in existing_plans:
            if meal.meal_type in meals_by_type:
                meals_by_type[meal.meal_type].append(meal)

        # Рассчитываем итоги
        totals = {
            'calories': sum(meal.calories or 0 for meal in existing_plans),
            'protein': sum(meal.protein or 0 for meal in existing_plans),
            'carbs': sum(meal.carbs or 0 for meal in existing_plans),
            'fat': sum(meal.fat or 0 for meal in existing_plans)
        }

        # Целевые значения
        target_calories = answer_bennedict(current_user)
        targets = {
            'calories': target_calories,
            'protein': int(target_calories * 0.3 / 4),  # 30% от калорий
            'carbs': int(target_calories * 0.4 / 4),  # 40% от калорий
            'fat': int(target_calories * 0.3 / 9)  # 30% от калорий
        }

        return render_template('meal_planner.html',
                               selected_date=selected_date,
                               meals_by_type=meals_by_type,
                               totals=totals,
                               targets=targets,
                               prev_date=(selected_date - timedelta(days=1)).isoformat(),
                               next_date=(selected_date + timedelta(days=1)).isoformat())

    except Exception as e:
        app.logger.error(f"Error in meal_planner: {str(e)}")
        flash('Произошла ошибка при загрузке планировщика питания', 'error')
        return redirect(url_for('index'))
    finally:
        db_sess.close()


@app.route('/generate_plan', methods=['POST'])
@login_required
def generate_plan():
    selected_date_str = request.form.get('date', date.today().isoformat())
    try:
        selected_date = datetime.strptime(selected_date_str, '%Y-%m-%d').date()
    except ValueError:
        selected_date = date.today()

    if generate_meal_plan_for_user(current_user.id, selected_date):
        flash('План питания успешно сгенерирован!', 'success')
    else:
        flash('Ошибка при генерации плана питания', 'error')

    return redirect(url_for('meal_planner', date=selected_date.isoformat()))


@app.route('/add_meal', methods=['POST'])
@login_required
def add_meal():
    db_sess = db_session.create_session()

    try:
        meal_plan = MealPlan(
            user_id=current_user.id,
            date=datetime.strptime(request.form['date'], '%Y-%m-%d').date(),
            meal_type=request.form['meal_type'],
            food_name=request.form['food_name'],
            calories=float(request.form['calories']),
            protein=float(request.form.get('protein', 0)),
            carbs=float(request.form.get('carbs', 0)),
            fat=float(request.form.get('fat', 0))
        )

        db_sess.add(meal_plan)
        db_sess.commit()
        flash('Блюдо успешно добавлено!', 'success')

    except Exception as e:
        db_sess.rollback()
        flash('Ошибка при добавлении блюда', 'error')
        app.logger.error(f"Error adding meal: {str(e)}")
    finally:
        db_sess.close()

    return redirect(url_for('meal_planner', date=request.form['date']))


@app.route('/delete_meal/<int:meal_id>', methods=['POST'])
@login_required
def delete_meal(meal_id):
    db_sess = db_session.create_session()

    try:
        meal = db_sess.query(MealPlan).filter(
            MealPlan.id == meal_id,
            MealPlan.user_id == current_user.id
        ).first()

        if meal:
            meal_date = meal.date
            db_sess.delete(meal)
            db_sess.commit()
            flash('Блюдо удалено', 'success')
            return redirect(url_for('meal_planner', date=meal_date.isoformat()))
        else:
            flash('Блюдо не найдено', 'error')

    except Exception as e:
        db_sess.rollback()
        flash('Ошибка при удалении блюда', 'error')
        app.logger.error(f"Error deleting meal: {str(e)}")
    finally:
        db_sess.close()

    return redirect(url_for('meal_planner'))


@app.route('/nutrition_analysis')
@login_required
def nutrition_analysis():
    try:
        # Получаем дату из параметров запроса или используем сегодняшнюю
        selected_date = request.args.get('date', date.today().isoformat())

        # Создаем сессию БД
        db_sess = db_session.create_session()

        # Получаем записи о питании для текущего пользователя и выбранной даты
        entries = db_sess.query(FoodEntry).filter(
            FoodEntry.user_id == current_user.id,
            FoodEntry.date == selected_date
        ).all()

        # Расчет сумм с защитой от None
        total_calories = sum(entry.calories or 0 for entry in entries)
        total_protein = sum(entry.protein or 0 for entry in entries)
        total_carbs = sum(entry.carbs or 0 for entry in entries)
        total_fat = sum(entry.fat or 0 for entry in entries)

        # Рассчитываем целевую норму калорий
        target_calories = answer_bennedict(current_user) if answer_bennedict(current_user) else 2000

        return render_template('nutrition_analysis.html',
                               selected_date=selected_date,
                               entries=entries,
                               total_calories=total_calories,
                               total_protein=total_protein,
                               total_carbs=total_carbs,
                               total_fat=total_fat,
                               target_calories=target_calories)

    except Exception as e:
        app.logger.error(f"Error in nutrition_analysis: {str(e)}")
        flash('Произошла ошибка при загрузке данных анализа питания', 'error')
        return render_template('nutrition_analysis.html',
                               selected_date=date.today().isoformat(),
                               entries=[],
                               total_calories=0,
                               total_protein=0,
                               total_carbs=0,
                               total_fat=0,
                               target_calories=2000)

    finally:
        db_sess.close()


@app.route('/knowledge_base')
def knowledge_base():
    return render_template('knowledge_base.html')


@app.route('/lifestyle_tips')
def lifestyle_tips():
    return render_template('lifestyle_tips.html')


@app.route('/api/nutrition_data')
@login_required
def nutrition_data():
    days = int(request.args.get('days', 7))
    end_date = date.today()
    start_date = end_date - timedelta(days=days - 1)

    db_sess = db_session.create_session()

    entries = db_sess.query(
        FoodEntry).filter(
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


api_key = "NmU2ZTUyODAtNjRjYS00MzkwLWI0NjItNGZjNzBlNzQ1MzliOjNkNTBjNzk5LWEzMDgtNDZlZS04Mzg1LWY2N2M2NTc5NmRhNQ=="
giga = GigaChat(
    credentials=api_key,
    scope="GIGACHAT_API_PERS",  # Для физлиц (альтернативы: GIGACHAT_API_B2B/CORP)
    verify_ssl_certs=False  # Отключение проверки сертификатов (не рекомендуется для прода)
)


def get_days_diet(age, gender, weight, height, activity, goal, dietary):
    text = f'''Составь рацион в виде 3 списка языка программирования python,
            где внутри каждого списка есть несколько списков, 1 элемент этого списка - название блюда или еды
            2 элемент - калорийность, 3 элемент - белки, 4 элемент - жиры, 5 элемент - углеводы
            , рацион на день для человека с такими данными:
            {age} лет, {gender}, вес {weight} кг, рост {height} см, {activity},
            цель - {goal}, особенности: {dietary}
            ВАЖНО СНИЗУ БУДЕТ ПРИМЕР, НАДО ВЫВОДИТЬ ТАКЖЕ
            daily_menu = [
            # Завтрак
            [
                "Овсяная каша",
                160,
                5.7,
                4.8,
                25.9
            ],
            [
                "Яйцо вареное",
                78,
                6.3,
                5.7,
                0.6
            ],
            [
                "Хлеб цельнозерновой",
                121,
                7.7,
                1.2,
                23.0
            ],
            
            # Перекус
            [
                "Йогурт греческий",
                66,
                5.2,
                2.0,
                7.5
            ],
            
            # Обед
            [
                "Куриная грудка",
                165,
                30.6,
                3.6,
                0.0
            ],
            [
                "Рис",
                130,
                2.7,
                0.5,
                28.2
            ],
            [
                "Салат из свежих овощей",
                46,
                1.7,
                0.2,
                9.6
            ],
            
            # Полдник
            [
                "Творог нежирный",
                88,
                17.2,
                1.8,
                1.0
            ],
            
            # Ужин
            [
                "Кальмар тушеный",
                122,
                22.1,
                1.6,
                1.1
            ],
            [
                "Капуста брокколи",
                34,
                2.8,
                0.4,
                6.6
            ]
            ]
            ВОТ ПОДОБНОЕ ТАКОМУ НЕЛЬЗЯ ПИСАТЬ
        Пример рациона на день для мальчика 10 лет с весом 40 кг и ростом 140 см, ведущего сидячий образ жизни, при снижении веса. Рацион включает завтрак, перекус, обед, полдник и ужин.
        '''
    messages = [
        Messages(role=MessagesRole.SYSTEM,
                 content="Ты программа, которая выводит только список языка python, ничего другого,"
                         " и знаешь БЖУ и калорийность всех продуктов питания"),
        Messages(role=MessagesRole.USER, content=text)
    ]

    # Формируем запрос
    chat = Chat(messages=messages)

    response = giga.chat(chat)
    return response.choices[0].message.content


def get_ai_answer(text, age, gender, weight, height, activity, goal, dietary):
    db_sess = db_session.create_session()
    last_messages = db_sess.query(User_Query).filter(User_Query.user_id == current_user.id).all()

    text += (f"\nДанные пользователя, которые надо учитывать и не противоречить им:\n"
             f"{age} лет, {gender}, вес {weight} кг, рост {height} см, {activity}, "
             f"цель - {goal}, особенности: {dietary}\n"
             f"Важно напиши ответ до 100 слов.")

    # Создаем историю сообщений
    messages = [
        Messages(role=MessagesRole.SYSTEM, content="Ты ассистент по ЗОЖ")
    ]
    for last_message in last_messages:
        messages.append(Messages(role=MessagesRole.USER, content=last_message.message))
        messages.append(Messages(role=MessagesRole.ASSISTANT, content=last_message.response))
    messages.append(Messages(role=MessagesRole.USER, content=text))

    # Формируем запрос
    chat = Chat(messages=messages)

    response = giga.chat(chat)
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
    # main()
    print(get_days_diet(10, "мужчина", 40, 140, "сидячий образ жизни", "похудение",
                        "нет"))
