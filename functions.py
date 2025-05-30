def answer_bennedict(age, gender, weight, height, activity, goal):
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
