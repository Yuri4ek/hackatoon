from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

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


test_data = ["составь рацион на день", 10, "мужчина", 34, 150, "малоподвижен", "похудеть", "нет"]

get_ai_answer(*test_data)
