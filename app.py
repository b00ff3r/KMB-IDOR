"""
Flask CTF приложение: заметки с уязвимостью IDOR.

Функционал:
- Регистрация и вход пользователей (данные хранятся в памяти — для CTF достаточно).
- После входа открывается «Дэшборд заметок».
- На дашборде всегда висят 4 случайные заметки (кроме скрытой с id=1).
- Каждая заметка открывается на своей отдельной странице по адресу /notes/<id>.
- Уязвимость: нет проверки владельца заметки. Поэтому можно открыть /notes/1 и увидеть флаг.

Интерфейс полностью на русском, с современным минималистичным дизайном.
"""

from flask import Flask, request, render_template_string, session, redirect, url_for
from functools import wraps
import random

app = Flask(__name__)
app.secret_key = 'secret-for-ctf'

# Демо заметки
NOTES = [
    {"id": 1, "owner_id": 1, "title": "Секретная заметка", "content": "PSUTICTF{IDOR_1s_s0_34sy}"},
    {"id": 2, "owner_id": 2, "title": "Список покупок", "content": "Яйца, молоко, хлеб"},
    {"id": 3, "owner_id": 3, "title": "Идеи", "content": "Сделать крутой проект"},
    {"id": 4, "owner_id": 2, "title": "Рабочие задачи", "content": "Закончить отчёт"},
    {"id": 5, "owner_id": 3, "title": "Рецепт", "content": "Паста с сыром"},
    {"id": 6, "owner_id": 2, "title": "Планы", "content": "Сходить в спортзал"},
    {"id": 7, "owner_id": 4, "title": "Фильмы", "content": "Посмотреть новый сериал"},
]

# Пользователи (id -> данные)
USERS = {
    1: {"login": "admin", "password": "admin"},
    2: {"login": "user", "password": "user"},
}
NEXT_USER_ID = 3

# Шаблоны интерфейса
INDEX_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title> Все заметки </title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    body{font-family:'Segoe UI',Roboto,Arial,sans-serif;background:#f5f7fb;margin:0;}
    header{background:linear-gradient(90deg,#1a73e8,#4285f4);color:#fff;padding:20px;text-align:center;font-size:24px;font-weight:600;box-shadow:0 2px 8px rgba(0,0,0,0.1)}
    main{max-width:900px;margin:30px auto;padding:30px;background:#fff;border-radius:16px;box-shadow:0 6px 18px rgba(0,0,0,0.08)}
    h2{color:#202124;margin-top:0}
    input,button{padding:12px;border-radius:8px;border:1px solid #ccc;margin:8px 0;width:100%;box-sizing:border-box;font-size:15px}
    button{background:#1a73e8;color:#fff;font-weight:600;border:none;cursor:pointer;transition:0.25s}
    button:hover{background:#1558b0}
    .note{border:1px solid #e0e0e0;padding:16px;margin:12px 0;border-radius:12px;background:#fafbff;transition:0.2s}
    .note:hover{box-shadow:0 2px 6px rgba(0,0,0,0.06)}
    .logout{text-align:right;margin-bottom:20px}
    a.note-link{text-decoration:none;color:#202124;display:block;font-size:16px}
    a.note-link:hover{color:#1a73e8}
  </style>
</head>
<body>
  <header>Заметочки</header>
  <main>
    {% if not session.get('user_id') %}
      <h2>Вход</h2>
      <form method="post" action="/login">
        <input type="text" name="login" placeholder="Логин" required>
        <input type="password" name="password" placeholder="Пароль" required>
        <button type="submit">Войти</button>
      </form>
      <h2>Регистрация</h2>
      <form method="post" action="/register">
        <input type="text" name="login" placeholder="Придумайте логин" required>
        <input type="password" name="password" placeholder="Придумайте пароль" required>
        <button type="submit">Зарегистрироваться</button>
      </form>
    {% else %}
      <div class="logout">
        <form method="post" action="/logout"><button type="submit">Выйти</button></form>
      </div>
      <h2>Заметки на дашборде</h2>
      {% for n in notes %}
        <div class="note"><a class="note-link" href="/notes/{{n.id}}"><b>{{n.title}}</b></a></div>
      {% endfor %}
     
    {% endif %}
  </main>
</body>
</html>
"""

NOTE_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>{{note.title}}</title>
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <style>
    body{font-family:'Segoe UI',Roboto,Arial,sans-serif;background:#f5f7fb;margin:0;}
    header{background:linear-gradient(90deg,#1a73e8,#4285f4);color:#fff;padding:20px;text-align:center;font-size:22px;font-weight:600;box-shadow:0 2px 8px rgba(0,0,0,0.1)}
    main{max-width:700px;margin:30px auto;padding:30px;background:#fff;border-radius:16px;box-shadow:0 6px 18px rgba(0,0,0,0.08)}
    .note{border:1px solid #e0e0e0;padding:20px;margin:12px 0;border-radius:12px;background:#fafbff;}
    a{color:#1a73e8;text-decoration:none;font-weight:500}
    a:hover{text-decoration:underline}
  </style>
</head>
<body>
  <header>{{note.title}}</header>
  <main>
    <div class="note">{{note.content}}</div>
    <p><a href="/">← Назад к дашборду</a></p>
  </main>
</body>
</html>
"""

# Декоратор: требовать вход
def login_required(f):
    @wraps(f)
    def wrapped(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return wrapped

@app.route('/', methods=['GET'])
def index():
    notes = []
    if 'user_id' in session:
        visible_notes = [n for n in NOTES if n['id'] != 1]  # исключаем секретную заметку
        notes = random.sample(visible_notes, min(4, len(visible_notes)))
    return render_template_string(INDEX_HTML, notes=notes, session=session)

@app.route('/login', methods=['POST'])
def login():
    login = request.form.get('login')
    password = request.form.get('password')
    for uid, data in USERS.items():
        if data['login'] == login and data['password'] == password:
            session['user_id'] = uid
            return redirect(url_for('index'))
    return "<p>Неверный логин или пароль</p><a href='/'>Назад</a>", 401

@app.route('/logout', methods=['POST'])
@login_required
def logout():
    session.pop('user_id')
    return redirect(url_for('index'))

@app.route('/register', methods=['POST'])
def register():
    global NEXT_USER_ID
    login = request.form.get('login')
    password = request.form.get('password')
    # Проверка на уникальность
    for data in USERS.values():
        if data['login'] == login:
            return "<p>Такой логин уже существует</p><a href='/'>Назад</a>", 400
    USERS[NEXT_USER_ID] = {"login": login, "password": password}
    session['user_id'] = NEXT_USER_ID
    NEXT_USER_ID += 1
    return redirect(url_for('index'))

# Уязвимый эндпоинт: просмотр заметки по ID (без проверки владельца)
@app.route('/notes/<int:note_id>')
@login_required
def get_note(note_id):
    note = next((n for n in NOTES if n['id']==note_id), None)
    if not note:
        return "<p>Заметка не найдена</p>", 404
    return render_template_string(NOTE_HTML, note=note)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
