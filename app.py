from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
import sqlite3
import os
from datetime import datetime, timedelta
import json

app = Flask(__name__)
app.secret_key = 'your-secret-key-here'

#

# Инициализируем БД при запуске
init_db()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        conn = sqlite3.connect('nutrition.db')
        c = conn.cursor()
        try:
            c.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", 
                     (username, email, password))
            conn.commit()
            flash('Регистрация успешна! Войдите в систему.', 'success')
            return redirect(url_for('login'))
        except sqlite3.IntegrityError:
            flash('Пользователь с таким именем или email уже существует.', 'error')
        finally:
            conn.close()
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = sqlite3.connect('nutrition.db')
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE username = ? AND password = ?", (username, password))
        user = c.fetchone()
        conn.close()
        
        if user:
            session['user_id'] = user[0]
            session['username'] = user[1]
            flash('Добро пожаловать!', 'success')
            return redirect(url_for('profile'))
        else:
            flash('Неверные данные для входа.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Вы вышли из системы.', 'info')
    return redirect(url_for('index'))

@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        gender = request.form['gender']
        age = int(request.form['age'])
        weight = float(request.form['weight'])
        height = float(request.form['height'])
        activity_level = request.form['activity_level']
        goal = request.form['goal']
        
        conn = sqlite3.connect('nutrition.db')
        c = conn.cursor()
        c.execute("""UPDATE users SET gender=?, age=?, weight=?, height=?, 
                     activity_level=?, goal=? WHERE id=?""", 
                 (gender, age, weight, height, activity_level, goal, session['user_id']))
        conn.commit()
        conn.close()
        
        flash('Профиль обновлен!', 'success')
    
    # Получаем данные пользователя
    conn = sqlite3.connect('nutrition.db')
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (session['user_id'],))
    user = c.fetchone()
    conn.close()
    
    return render_template('profile.html', user=user)

@app.route('/planner')
def planner():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Получаем план питания на сегодня
    today = datetime.now().strftime('%Y-%m-%d')
    conn = sqlite3.connect('nutrition.db')
    c = conn.cursor()
    c.execute("""SELECT * FROM meal_plans WHERE user_id=? AND date=? 
                 ORDER BY meal_type""", (session['user_id'], today))
    meals = c.fetchall()
    conn.close()
    
    return render_template('planner.html', meals=meals, today=today)

@app.route('/add_meal', methods=['POST'])
def add_meal():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    date = request.form['date']
    meal_type = request.form['meal_type']
    food_name = request.form['food_name']
    calories = int(request.form['calories'])
    protein = float(request.form['protein'])
    carbs = float(request.form['carbs'])
    fat = float(request.form['fat'])
    
    conn = sqlite3.connect('nutrition.db')
    c = conn.cursor()
    c.execute("""INSERT INTO meal_plans (user_id, date, meal_type, food_name, 
                 calories, protein, carbs, fat) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
             (session['user_id'], date, meal_type, food_name, calories, protein, carbs, fat))
    conn.commit()
    conn.close()
    
    flash('Блюдо добавлено в план питания!', 'success')
    return redirect(url_for('planner'))

@app.route('/analysis')
def analysis():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # Получаем данные за последние 7 дней
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    conn = sqlite3.connect('nutrition.db')
    c = conn.cursor()
    c.execute("""SELECT date, SUM(calories), SUM(protein), SUM(carbs), SUM(fat)
                 FROM meal_plans WHERE user_id=? AND date BETWEEN ? AND ?
                 GROUP BY date ORDER BY date""", 
             (session['user_id'], start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')))
    daily_stats = c.fetchall()
    
    # Получаем данные пользователя для расчета нормы
    c.execute("SELECT * FROM users WHERE id=?", (session['user_id'],))
    user = c.fetchone()
    conn.close()
    
    # Расчет базового метаболизма (формула Миффлина-Сан Жеора)
    bmr = 0
    if user and user[4] and user[5] and user[6] and user[7]:  # gender, age, weight, height
        if user[4] == 'male':
            bmr = 10 * user[6] + 6.25 * user[7] - 5 * user[5] + 5
        else:
            bmr = 10 * user[6] + 6.25 * user[7] - 5 * user[5] - 161
        
        # Учитываем уровень активности
        activity_multipliers = {
            'sedentary': 1.2,
            'light': 1.375,
            'moderate': 1.55,
            'active': 1.725,
            'very_active': 1.9
        }
        if user[8] in activity_multipliers:
            bmr *= activity_multipliers[user[8]]
    
    return render_template('analysis.html', daily_stats=daily_stats, bmr=int(bmr), user=user)

@app.route('/knowledge')
def knowledge():
    return render_template('knowledge.html')

@app.route('/recipes')
def recipes():
    diet_filter = request.args.get('diet_type', '')
    max_calories = request.args.get('max_calories', '')
    
    conn = sqlite3.connect('nutrition.db')
    c = conn.cursor()
    
    query = "SELECT * FROM recipes WHERE 1=1"
    params = []
    
    if diet_filter:
        query += " AND diet_type = ?"
        params.append(diet_filter)
    
    if max_calories:
        query += " AND calories_per_serving <= ?"
        params.append(int(max_calories))
    
    c.execute(query, params)
    recipes = c.fetchall()
    conn.close()
    
    return render_template('recipes.html', recipes=recipes)

@app.route('/recipe/<int:recipe_id>')
def recipe_detail(recipe_id):
    conn = sqlite3.connect('nutrition.db')
    c = conn.cursor()
    c.execute("SELECT * FROM recipes WHERE id=?", (recipe_id,))
    recipe = c.fetchone()
    conn.close()
    
    if not recipe:
        flash('Рецепт не найден.', 'error')
        return redirect(url_for('recipes'))
    
    return render_template('recipe_detail.html', recipe=recipe)

if __name__ == '__main__':
    app.run(debug=True)