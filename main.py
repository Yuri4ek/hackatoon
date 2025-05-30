from flask import Flask, render_template, redirect, url_for, flash, abort, request, jsonify
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from flask_restful import abort, Api

from datetime import datetime, date

from data import db_session
from data.user import User
from data.user_query import User_Query


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
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        # Валидация
        if not name:
            flash('Имя обязательно для заполнения', 'error')
            return render_template('register.html')

        if not email:
            flash('Email обязателен для заполнения', 'error')
            return render_template('register.html')

        if len(password) < 6:
            flash('Пароль должен содержать минимум 6 символов', 'error')
            return render_template('register.html')

        if password != confirm_password:
            flash('Пароли не совпадают', 'error')
            return render_template('register.html')

        # Проверка на существование пользователя
        if User.query.filter_by(email=email).first():
            flash('Пользователь с таким email уже существует', 'error')
            return render_template('register.html')

        # Создание нового пользователя
        user = User(name=name, email=email)
        user.set_password(password)

        try:
            User.session.add(user)
            User.session.commit()
            flash('Регистрация успешна! Теперь вы можете войти в систему.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            User.session.rollback()
            flash('Произошла ошибка при регистрации. Попробуйте еще раз.', 'error')
            return render_template('register.html')

    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip()
        password = request.form['password']
        remember_me = bool(request.form.get('remember_me'))

        if not email or not password:
            flash('Пожалуйста, заполните все поля', 'error')
            return render_template('login.html')

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            login_user(user, remember=remember_me)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Неверный email или пароль', 'error')

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



def main():
    # Инициализация бд (указывать абсолютный путь при хостинге)
    db_session.global_init("db/blogs.db")
    db_sess = db_session.create_session()
    # Проверяем, существует ли администратор
    app.run(port=8080, host="127.0.0.1", debug=True)


if __name__ == "__main__":
    main()