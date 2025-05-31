import datetime
from data import db_session
from data.products import Product  # Предполагается, что у вас есть модель Product


def main():
    # Инициализация базы данных
    db_session.global_init("db/blogs.db")
    db_sess = db_session.create_session()

    # Чтение файла products.txt
    with open('products.txt', 'r', encoding='utf-8') as file:
        for line in file:
            line = line.strip()
            if not line or line.startswith(('Напиток', 'Белки')):
                continue  # Пропускаем заголовки и пустые строки

            # Обработка строки с данными
            if line.startswith("[('") or line.startswith("('"):
                # Удаляем лишние символы и разбиваем на элементы
                line = line.replace("[('", "").replace("')]", "").replace("('", "").replace("')", "")
                items = [item.strip().strip("'") for item in line.split("', '")]

                if len(items) >= 5:
                    # Создаем новый продукт и заполняем данные
                    print(items[0], items[1], items[2], items[3], items[4])
                    product = Product(
                        name=items[0],
                        proteins=float(items[1].replace(',', '.')),
                        fats=float(items[2].replace(',', '.')),
                        carbohydrates=float(items[3].replace(',', '.')),
                        calories=float(items[4].replace(',', '.'))
                    )

                    # Добавляем в сессию
                    db_sess.add(product)

    # Сохраняем изменения
    db_sess.commit()
    print("Данные о продуктах успешно загружены в базу данных.")


if __name__ == "__main__":
    main()