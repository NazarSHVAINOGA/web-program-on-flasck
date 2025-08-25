import streamlit as st
import requests
import json
from datetime import datetime, timedelta
import pandas as pd
from io import BytesIO
import plotly.graph_objects as go
import plotly.express as px

from streamlit_calendar import calendar
import streamlit.components.v1 as components
from datetime import datetime, timezone
import time

# Колірна палітра з еталонного зображення
COLORS = {
    "primary": "#806543",     # Бронзовий/Коричневий
    "secondary": "#33266E",   # Темно-фіолетовий
    "dark": "#111111",        # Чорний
    "accent1": "#542F34",     # Бордовий
    "accent2": "#A6607C",     # Рожевий/Фіолетовий
    "white": "#FFFFFF",       # Білий
    "light_gray": "#F8F9FA",  # Світло-сірий
    "success": "#4CAF50",     # Зелений
    "danger": "#f44336",      # Червоний
    "info": "#2196F3"         # Синій
}

# Налаштування сторінки
st.set_page_config(
    page_title="📚 Система управління проєктами",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Кастомні стилі CSS з оновленою кольоровою гамою
st.markdown(f"""
    <style>
        /* Базові елементи */
        .stApp {{
            background-color: {COLORS["white"]};
            color: {COLORS["dark"]};
        }}
        
        /* Оформлення бічної панелі */
        .css-1d391kg, .css-12oz5g7 {{
            background-color: {COLORS["primary"]};
        }}
        
        header {{
            background-color: {COLORS["primary"]};
        }}
        
        /* Інформація про користувача у бічній панелі */
        .user-info {{
            background-color: {COLORS["secondary"]};
            color: {COLORS["white"]};
            padding: 20px;
            border-radius: 10px;
            margin-bottom: 20px;
        }}
        
        /* Кнопки */
        .stButton button {{
            width: 100%;
            border-radius: 5px;
            height: 3em;
            background-color: {COLORS["secondary"]};
            color: white;
            border: none;
            margin: 5px 0px;
        }}
        
        .stButton button:hover {{
            background-color: {COLORS["primary"]};
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
        }}
        
        .delete-button button {{
            background-color: {COLORS["danger"]};
        }}
        
        .delete-button button:hover {{
            background-color: #da190b;
        }}
        
        /* Картки проєктів */
        .project-card {{
            padding: 20px;
            border-radius: 10px;
            border: 1px solid #ddd;
            margin: 10px 0px;
            background-color: {COLORS["white"]};
            position: relative;
            transition: all 0.3s ease;
        }}
        
        .project-card:hover {{
            box-shadow: 0 5px 15px rgba(0,0,0,0.1);
            border-left: 5px solid {COLORS["primary"]};
        }}
        
        /* Картки завдань */
        .kanban-column {{
            background-color: {COLORS["light_gray"]};
            border-radius: 10px;
            padding: 15px;
            margin: 10px;
            min-height: 300px;
            border-top: 4px solid {COLORS["secondary"]};
        }}
        
        .task-card {{
            background-color: {COLORS["white"]};
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 10px;
            margin: 5px 0;
            cursor: pointer;
            transition: all 0.2s ease;
        }}
        
        .task-card:hover {{
            box-shadow: 0 2px 5px rgba(0,0,0,0.2);
            border-left: 3px solid {COLORS["primary"]};
        }}
        
        /* Значок сповіщень */
        .notification-badge {{
            background-color: {COLORS["danger"]};
            color: white;
            padding: 2px 6px;
            border-radius: 50%;
            font-size: 12px;
            position: absolute;
            top: -5px;
            right: -5px;
        }}
        
        /* Таблиці */
        .grades-table {{
            width: 100%;
            border-collapse: collapse;
            margin: 20px 0;
        }}
        
        .grades-table th, .grades-table td {{
            border: 1px solid #ddd;
            padding: 8px;
            text-align: left;
        }}
        
        .grades-table th {{
            background-color: {COLORS["secondary"]};
            color: white;
        }}
        
        .user-row {{
            padding: 10px;
            border-bottom: 1px solid #ddd;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .user-info {{
            padding: 20px;
            background-color: {COLORS["secondary"]};
            border-radius: 10px;
            margin-bottom: 20px;
            color: white;
        }}
        
        /* Події календаря */
         .calendar-event {{
            padding: 10px;
            border-radius: 5px;
            margin: 5px 0;
        }}
        
        .event-meeting {{
            background-color: #E8F5E9;
            border-left: 4px solid {COLORS["success"]};
        }}
        
        .event-deadline {{
            background-color: #FFEBEE;
            border-left: 4px solid {COLORS["danger"]};
        }}
        
        .event-other {{
            background-color: #E3F2FD;
            border-left: 4px solid {COLORS["info"]};
        }}
        
        /* Стилі для повноекранного календаря */
        .fc {{
            background-color: white;
            padding: 10px;
            border-radius: 5px;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
        }}
        
        .fc-event {{
            cursor: pointer;
            padding: 2px 5px;
        }}
        
        .fc-daygrid-day {{
            height: 100px;
        }}
        
        /* Коментарі */
        .comment-card {{
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
            background-color: {COLORS["light_gray"]};
            border-left: 3px solid {COLORS["primary"]};
        }}
        
        /* Картки файлів */
        .file-card {{
            padding: 10px;
            border-radius: 5px;
            margin: 5px 0;
            background-color: {COLORS["light_gray"]};
            border-left: 3px solid {COLORS["info"]};
        }}
        
        /* Заголовки та назви розділів */
        h1, h2 {{
            color: {COLORS["primary"]};
        }}
        
        h3, h4, h5, h6 {{
            color: {COLORS["secondary"]};
        }}
        
        /* Поля форм та введення */
        .stTextInput input, .stTextArea textarea, .stSelectbox, .stMultiselect {{
            border-radius: 5px;
            border: 1px solid #ddd;
        }}
        
        .stTextInput input:focus, .stTextArea textarea:focus {{
            border: 1px solid {COLORS["primary"]};
            box-shadow: 0 0 3px {COLORS["primary"]};
        }}
    </style>
""", unsafe_allow_html=True)

# Константи
API_URL = "http://localhost:5000"
ROLES = {
    'specialist': 'Спеціаліст',
    'manager': 'Менеджер',
    'admin': 'Адміністратор'
}

# Клас для роботи з API та JWT токенами
class ApiClient:
    def __init__(self):
        self.token = st.session_state.get('token', None)
        self.headers = {'Authorization': f'Bearer {self.token}'} if self.token else {}
    
    def refresh_token(self):
        """Оновлення JWT токена"""
        if self.token and self._is_token_expired():
            response = requests.post(f"{API_URL}/refresh-token", headers=self.headers)
            if response.status_code == 200:
                self.token = response.json()['token']
                self.headers = {'Authorization': f'Bearer {self.token}'}
                st.session_state.token = self.token
    
    def _is_token_expired(self):
        """Перевірка чи токен прострочений"""
        try:
            import jwt
            decoded = jwt.decode(self.token, options={"verify_signature": False})
            exp = datetime.fromtimestamp(decoded['exp'])
            # Використовуємо timezone-aware datetime
            current_time = datetime.now(timezone.utc)
            return current_time + timedelta(minutes=5) >= exp.replace(tzinfo=timezone.utc)
        except:
            return True
    
    def post(self, endpoint, data):
        self.refresh_token()
        headers = {
            'Content-Type': 'application/json',
            **self.headers
        }
        return requests.post(
            f"{API_URL}{endpoint}", 
            json=data,  
            headers=headers
        )
    
    def get(self, endpoint):
        self.refresh_token()
        return requests.get(f"{API_URL}{endpoint}", headers=self.headers)
    
    def put(self, endpoint, data):
        self.refresh_token()
        return requests.put(f"{API_URL}{endpoint}", json=data, headers=self.headers)
    
    def delete(self, endpoint):
        self.refresh_token()
        return requests.delete(f"{API_URL}{endpoint}", headers=self.headers)
    
    def upload_file(self, endpoint, files):
        self.refresh_token()
        return requests.post(f"{API_URL}{endpoint}", files=files, headers=self.headers)

# Ініціалізація стану
if 'token' not in st.session_state:
    st.session_state.token = None
if 'user' not in st.session_state:
    st.session_state.user = None
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'login'
if 'notifications' not in st.session_state:
    st.session_state.notifications = []
if 'project_members' not in st.session_state:
    st.session_state.project_members = []
if 'unread_count' not in st.session_state:
    st.session_state.unread_count = 0

api_client = ApiClient()

def show_messages():
    """Відображення повідомлень"""
    if 'show_success_message' in st.session_state and st.session_state.show_success_message:
        st.success(st.session_state.success_message)
        del st.session_state.show_success_message
        del st.session_state.success_message
    
    if 'show_error_message' in st.session_state and st.session_state.show_error_message:
        st.error(st.session_state.error_message)
        del st.session_state.show_error_message
        del st.session_state.error_message

def update_notifications():
    """Оптимізована функція оновлення сповіщень"""
    if st.session_state.token:
        try:
            response = api_client.get("/notifications/unread-count")
            if response.status_code == 200:
                st.session_state.unread_count = response.json()['unread_count']
                
                # Отримуємо сповіщення тільки якщо є непрочитані
                if st.session_state.unread_count > 0:
                    notifications_response = api_client.get("/notifications")
                    if notifications_response.status_code == 200:
                        st.session_state.notifications = notifications_response.json()
        except Exception as e:
            st.error(f"Помилка оновлення сповіщень: {str(e)}")

def show_login_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"<h1 style='text-align: center; color: {COLORS['primary']};'>🎓 Система управління проєктами</h1>", unsafe_allow_html=True)
        
        with st.form("login_form"):
            st.markdown(f"<p class='big-text' style='color: {COLORS['secondary']};'>Вхід у систему</p>", unsafe_allow_html=True)
            email = st.text_input("Електронна пошта")
            password = st.text_input("Пароль", type="password")
            
            submitted = st.form_submit_button("Увійти")
            
            if submitted:
                try:
                    response = api_client.post("/login", {
                        "email": email,
                        "password": password
                    })
                    
                    if response.status_code == 200:
                        data = response.json()
                        st.session_state.token = data['token']
                        st.session_state.user = data['user']
                        st.session_state.current_page = 'projects'
                        st.rerun()
                    else:
                        st.error("Невірна пошта або пароль")
                except Exception as e:
                    st.error(f"Помилка підключення до сервера: {str(e)}")
        
        if st.button("Зареєструватися"):
            st.session_state.current_page = 'register'
            st.rerun()

def show_register_page():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.markdown(f"<h1 style='text-align: center; color: {COLORS['primary']};'>🎓 Реєстрація</h1>", unsafe_allow_html=True)
        
        with st.form("register_form"):
            name = st.text_input("Ім'я")
            email = st.text_input("Електронна пошта")
            password = st.text_input("Пароль", type="password")
            role = st.selectbox("Роль", ['specialist', 'manager'], format_func=lambda x: ROLES[x])
            
            submitted = st.form_submit_button("Зареєструватися")
            
            if submitted:
                try:
                    response = api_client.post("/register", {
                        "name": name,
                        "email": email,
                        "password": password,
                        "role": role
                    })
                    
                    if response.status_code == 201:
                        st.success("Реєстрація успішна!")
                        st.session_state.current_page = 'login'
                        st.rerun()
                    else:
                        st.error("Користувач з такою поштою вже існує")
                except Exception as e:
                    st.error(f"Помилка реєстрації: {str(e)}")

def show_admin_panel():
    st.title("Панель адміністратора")
    
    response = api_client.get("/users")
    if response.status_code == 200:
        users = response.json()
        
        managers = [u for u in users if u['role'] == 'manager']
        specialists = [u for u in users if u['role'] == 'specialist']
        
        tab1, tab2 = st.tabs(["Менеджери", "Спеціалісти"])
        
        with tab1:
            st.header("Список менеджерів")
            for manager in managers:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"""
                            <div class="user-card">
                                <h4>{manager['name']}</h4>
                                <p>Email: {manager['email']}</p>
                                <p>Проєктів: {manager.get('projects_count', 0)}</p>
                            </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        if st.button("❌ Видалити", key=f"delete_manager_{manager['id']}"):
                            response = api_client.delete(f"/users/{manager['id']}")
                            if response.status_code == 200:
                                st.success("Менеджера видалено")
                                st.rerun()
                            else:
                                st.error("Помилка при видаленні менеджера")
        
        with tab2:
            st.header("Список спеціалістів")
            for specialist in specialists:
                with st.container():
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"""
                            <div class="user-card">
                                <h4>{specialist['name']}</h4>
                                <p>Email: {specialist['email']}</p>
                                <p>Проєктів: {specialist.get('projects_count', 0)}</p>
                            </div>
                        """, unsafe_allow_html=True)
                    with col2:
                        if st.button("❌ Видалити", key=f"delete_specialist_{specialist['id']}"):
                            response = api_client.delete(f"/users/{specialist['id']}")
                            if response.status_code == 200:
                                st.success("Спеціаліста видалено")
                                st.rerun()
                            else:
                                st.error("Помилка при видаленні спеціаліста")

def show_project_details():
    project = st.session_state.current_project
    st.title(project['name'])
    
    # Вкладки проєкту
    tabs = ["Деталі", "Завдання", "Календар", "Обговорення", "Файли"]
    if st.session_state.user['role'] == 'manager':
        tabs.append("Оцінка виконання")
    
    current_tab = st.tabs(tabs)
    
    with current_tab[0]:
        show_project_info(project)
    
    with current_tab[1]:
        show_kanban_board(project['id'])
    
    with current_tab[2]:
        show_calendar(project['id'])
    
    with current_tab[3]:
        if st.session_state.user['role'] != 'admin':
            show_comments(project['id'])
        else:
            st.info("Адміністратор не може брати участь в обговоренні")
    
    with current_tab[4]:
        show_files(project['id'])
    
    if st.session_state.user['role'] == 'manager' and len(current_tab) > 5:
        with current_tab[5]:
            show_performance_evaluation(project['id'])

def show_project_info(project):
    """Відображення детальної інформації про проект"""
    st.markdown(f"""
        <div class="project-card">
            <h3>{project['name']}</h3>
            <p>{project.get('description', 'Опис відсутній')}</p>
            <p><strong>Менеджер:</strong> {project.get('manager_name', 'Не призначено')}</p>
            <p><strong>Дедлайн:</strong> {project.get('deadline', 'Не встановлено')}</p>
            <p><strong>Статус:</strong> {project.get('status', 'Активний')}</p>
            <p><strong>Максимум спеціалістів:</strong> {project.get('max_specialists', 'Не обмежено')}</p>
        </div>
    """, unsafe_allow_html=True)
    
    # Відображення статистики проекту
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Учасників", project.get('members_count', 0))
    with col2:
        st.metric("Завдань", project.get('total_tasks', 0))
    with col3:
        st.metric("Завершено", project.get('completed_tasks', 0))

def show_performance_evaluation(project_id):
    st.header("📚 Оцінка виконання")
    
    # Отримуємо список спеціалістів проекту
    members_response = api_client.get(f"/projects/{project_id}/members")
    if members_response.status_code != 200:
        st.error("Помилка при отриманні списку учасників")
        return
    
    # Фільтруємо тільки спеціалістів
    specialists = [m for m in members_response.json() if m['role'] == 'specialist']
    
    # Отримуємо існуючі оцінки
    ratings_response = api_client.get(f"/projects/{project_id}/ratings")
    if ratings_response.status_code != 200:
        st.error("Помилка при отриманні оцінок")
        return
    
    ratings = ratings_response.json()
    ratings_dict = {r['specialist_id']: r for r in ratings}
    
    # Відображення таблиці оцінок
    if specialists:
        data = []
        for specialist in specialists:
            rating_info = ratings_dict.get(specialist['id'], {})
            data.append({
                'ID': specialist['id'],
                'Спеціаліст': specialist['name'],
                'Оцінка': rating_info.get('rating', '-'),
                'Коментар': rating_info.get('comment', ''),
                'Дата оцінювання': rating_info.get('timestamp', '')
            })
        
        df = pd.DataFrame(data)
        st.dataframe(df.set_index('ID'), use_container_width=True)
        
        # Форма для виставлення оцінок (тільки для менеджера)
        if st.session_state.user['role'] == 'manager':
            with st.form("rating_form"):
                st.subheader("Оцінити виконання")
                
                specialist = st.selectbox(
                    "Оберіть спеціаліста",
                    options=specialists,
                    format_func=lambda x: x['name']
                )
                
                rating = st.number_input(
                    "Оцінка",
                    min_value=0.0,
                    max_value=100.0,
                    value=60.0,
                    step=0.5
                )
                
                comment = st.text_area("Коментар")
                
                if st.form_submit_button("Виставити оцінку"):
                    response = api_client.post(f"/projects/{project_id}/ratings", {
                        "specialist_id": specialist['id'],
                        "rating": rating,
                        "comment": comment
                    })
                    
                    if response.status_code == 200:
                        st.success("Оцінку успішно виставлено")
                        st.rerun()
                    else:
                        st.error("Помилка при виставленні оцінки")
    else:
        st.info("У проєкті ще немає спеціалістів")

def show_admin_users():
    """Відображення списку користувачів для адміністратора"""
    st.title("Керування користувачами")
    
    # Отримуємо список всіх користувачів
    response = api_client.get("/users")
    if response.status_code != 200:
        st.error("Не вдалося завантажити список користувачів")
        return
        
    users = response.json()
    
    # Розділяємо користувачів за ролями
    managers = [u for u in users if u['role'] == 'manager']
    specialists = [u for u in users if u['role'] == 'specialist']
    
    # Створюємо вкладки для різних типів користувачів
    tab1, tab2 = st.tabs(["Менеджери", "Спеціалісти"])
    
    with tab1:
        st.subheader("Список менеджерів")
        for manager in managers:
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"""
                        <div class="user-card">
                            <h4>{manager['name']}</h4>
                            <p>Email: {manager['email']}</p>
                            <p>Проєктів: {manager.get('projects_count', 0)}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                with col2:
                    if st.button("Детальніше", key=f"manager_{manager['id']}"):
                        show_manager_details(manager['id'])
    
    with tab2:
        st.subheader("Список спеціалістів")
        for specialist in specialists:
            with st.container():
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"""
                        <div class="user-card">
                            <h4>{specialist['name']}</h4>
                            <p>Email: {specialist['email']}</p>
                            <p>Проєктів: {specialist.get('projects_count', 0)}</p>
                            <p>Середня оцінка: {specialist.get('average_rating', 'Немає оцінок')}</p>
                        </div>
                    """, unsafe_allow_html=True)
                    
                with col2:
                    if st.button("Детальніше", key=f"specialist_{specialist['id']}"):
                        show_specialist_details(specialist['id'])

def show_manager_details(manager_id):
    """Відображення детальної інформації про менеджера"""
    response = api_client.get(f"/users/{manager_id}/details")
    if response.status_code != 200:
        st.error("Не вдалося завантажити інформацію про менеджера")
        return
        
    manager = response.json()
    
    st.subheader(f"Менеджер: {manager['name']}")
    
    # Статистика по проєктах
    st.markdown("### Проєкти")
    
    if manager.get('projects'):
        for project in manager['projects']:
            st.markdown(f"""
                <div class="project-card">
                    <h4>{project['name']}</h4>
                    <p>Спеціалістів: {project['specialists_count']}</p>
                    <p>Середня оцінка: {project['average_rating']:.1f}</p>
                    <p>Завершеність: {project['completion_rate']}%</p>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Немає активних проєктів")

def show_specialist_details(specialist_id):
    """Відображення детальної інформації про спеціаліста"""
    response = api_client.get(f"/users/{specialist_id}/details")
    if response.status_code != 200:
        st.error("Не вдалося завантажити інформацію про спеціаліста")
        return
        
    specialist = response.json()
    
    st.subheader(f"Спеціаліст: {specialist['name']}")
    
    # Статистика по проєктах
    st.markdown("### Проєкти та оцінки")
    
    if specialist.get('projects'):
        for project in specialist['projects']:
            st.markdown(f"""
                <div class="project-card">
                    <h4>{project['name']}</h4>
                    <p>Менеджер: {project['manager_name']}</p>
                    <p>Оцінка: {project.get('rating', 'Не виставлена')}</p>
                    <p>Виконаних завдань: {project['completed_tasks']}/{project['total_tasks']}</p>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.info("Спеціаліст не бере участі в проєктах")

# Додаткові функції для оптимізованої системи сповіщень
def notify_users(project_id, message, user_ids=None):
    """Надсилання сповіщень користувачам"""
    data = {
        "project_id": project_id,
        "message": message,
        "user_ids": user_ids
    }
    
    response = api_client.post("/notifications/send", data)
    return response.status_code == 200

def mark_notifications_read(notification_ids):
    """Позначення сповіщень як прочитаних"""
    response = api_client.post("/notifications/mark-read", {
        "notification_ids": notification_ids
    })
    return response.status_code == 200

def get_notifications_count():
    """Отримання кількості непрочитаних сповіщень"""
    response = api_client.get("/notifications/unread-count")
    if response.status_code == 200:
        return response.json()['unread_count']
    return 0

def show_notifications_popup():
    """Відображення спливаючого вікна зі сповіщеннями"""
    # Отримуємо останні сповіщення
    response = api_client.get("/notifications?limit=5")
    if response.status_code == 200:
        notifications = response.json()
        
        with st.container():
            for notification in notifications:
                st.markdown(f"""
                    <div class="notification-card {'unread' if not notification['is_read'] else ''}">
                        <h4>{notification['title']}</h4>
                        <p>{notification['message']}</p>
                        <small>{notification['created_at']}</small>
                    </div>
                """, unsafe_allow_html=True)
                
                if not notification['is_read']:
                    if st.button("Позначити як прочитане", key=f"mark_read_{notification['id']}"):
                        mark_notifications_read([notification['id']])
                        st.rerun()

# Покращені функції для роботи з проєктами
def get_project_statistics(project_id):
    """Отримання статистики по проєкту"""
    response = api_client.get(f"/projects/{project_id}/statistics")
    if response.status_code == 200:
        return response.json()
    return None

def show_project_statistics(project_id):
    """Відображення статистики проєкту"""
    stats = get_project_statistics(project_id)
    if not stats:
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Учасників", stats['members_count'])
    
    with col2:
        st.metric("Виконано завдань", f"{stats['completed_tasks']}/{stats['total_tasks']}")
    
    with col3:
        st.metric("Середня оцінка", f"{stats['average_rating']:.1f}")
    
    # Графік прогресу
    progress_data = pd.DataFrame(stats['progress_history'])
    fig = px.line(progress_data, x='date', y='completion_rate', 
                  title='Прогрес виконання проєкту')
    st.plotly_chart(fig)

def show_projects():
    st.title("Проєкти")
    
    # Для менеджера - можливість створення
    if st.session_state.user['role'] == 'manager':
        if st.button("➕ Створити новий проект"):
            st.session_state.current_page = 'create_project'
            st.rerun()
    
    response = api_client.get("/projects")
    if response.status_code == 200:
        projects = response.json()
        
        # Відображення проєктів
        for project in projects:
            with st.container():
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    st.markdown(f"""
                        <div class="project-card">
                            <h3>{project['name']}</h3>
                            <p>{project.get('description', 'Опис відсутній')}</p>
                            <p><strong>Менеджер:</strong> {project.get('manager_name', 'Не призначено')}</p>
                            <p><strong>Дедлайн:</strong> {project.get('deadline', 'Не встановлено')}</p>
                        </div>
                    """, unsafe_allow_html=True)
                
                with col2:
                    if st.button("📋 Деталі", key=f"details_{project['id']}"):
                        st.session_state.current_project = project
                        st.session_state.current_page = 'project_details'
                        st.rerun()
                    
                    if (st.session_state.user['role'] == 'specialist' and 
                        not project.get('is_member', False)):
                        if st.button("📥 Приєднатися", key=f"join_{project['id']}"):
                            response = api_client.post(f"/projects/{project['id']}/join", {})
                            if response.status_code == 200:
                                st.success("✅ Ви успішно приєднались до проєкту!")
                                st.rerun()
                            else:
                                st.error(response.json().get('message', 'Помилка при приєднанні до проєкту'))

    # Показуємо повідомлення після оновлення сторінки
    if 'show_success_message' in st.session_state and st.session_state.show_success_message:
        st.success(st.session_state.success_message)
        # Очищуємо повідомлення
        del st.session_state.show_success_message
        del st.session_state.success_message
    
    if 'show_error_message' in st.session_state and st.session_state.show_error_message:
        st.error(st.session_state.error_message)
        # Очищуємо повідомлення
        del st.session_state.show_error_message
        del st.session_state.error_message


def show_kanban_board(project_id):
    st.header("Завдання")
    
    # Отримання всіх завдань
    response = api_client.get(f"/projects/{project_id}/tasks")
    if response.status_code == 200:
        tasks = response.json()
        
        # Додавання нового завдання (тільки для менеджера)
        if st.session_state.user['role'] == 'manager':
            with st.expander("Додати нове завдання"):
                with st.form("new_task_form"):
                    title = st.text_input("Назва завдання")
                    description = st.text_area("Опис")
                    deadline = st.date_input("Дедлайн")
                    assigned_to = st.selectbox(
                        "Призначити спеціалісту",
                        options=[m['id'] for m in st.session_state.project_members if m['role'] == 'specialist'],
                        format_func=lambda x: next(m['name'] for m in st.session_state.project_members if m['id'] == x)
                    )
                    
                    if st.form_submit_button("Створити"):
                        create_task(project_id, title, description, deadline, assigned_to)
        
        # Відображення дошки
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.subheader("Не розпочато")
            show_task_column(tasks, "not_started", project_id)
        
        with col2:
            st.subheader("В процесі")
            show_task_column(tasks, "in_progress", project_id)
        
        with col3:
            st.subheader("Завершено")
            show_task_column(tasks, "completed", project_id)

def show_task_column(tasks, status, project_id):
    filtered_tasks = [t for t in tasks if t['status'] == status]
    for task in filtered_tasks:
        with st.container():
            st.markdown(f"""
                <div class="task-card">
                    <h4>{task['title']}</h4>
                    <p>{task['description']}</p>
                    <p><small>Дедлайн: {task['deadline']}</small></p>
                    <p><small>Виконавець: {task.get('assigned_user_name', 'Не призначено')}</small></p>
                </div>
            """, unsafe_allow_html=True)
            
            if st.session_state.user['role'] != 'admin':
                if status == "not_started":
                    if st.button("→ В процес", key=f"start_{task['id']}"):
                        update_task_status(project_id, task['id'], "in_progress")
                elif status == "in_progress":
                    if st.button("→ Завершено", key=f"complete_{task['id']}"):
                        update_task_status(project_id, task['id'], "completed")

def show_calendar(project_id):
    st.header("📅 Календар")
    
    # Отримання подій
    response = api_client.get(f"/projects/{project_id}/calendar")
    if response.status_code == 200:
        events = response.json()
        
        # Додавання нової події (тільки для менеджера)
        if st.session_state.user['role'] == 'manager':
            with st.expander("Додати подію"):
                with st.form("new_event_form"):
                    title = st.text_input("Назва події")
                    description = st.text_area("Опис")
                    event_type = st.selectbox(
                        "Тип події",
                        ["meeting", "deadline", "other"],
                        format_func=lambda x: {
                            "meeting": "Зустріч",
                            "deadline": "Дедлайн",
                            "other": "Інше"
                        }[x]
                    )
                    col1, col2 = st.columns(2)
                    with col1:
                        start_date = st.date_input("Дата початку")
                        start_time = st.time_input("Час початку")
                    with col2:
                        end_date = st.date_input("Дата завершення")
                        end_time = st.time_input("Час завершення")
                    
                    if st.form_submit_button("Додати"):
                        start_datetime = datetime.combine(start_date, start_time)
                        end_datetime = datetime.combine(end_date, end_time)
                        
                        response = api_client.post(f"/projects/{project_id}/calendar", {
                            "title": title,
                            "description": description,
                            "event_type": event_type,
                            "start_time": start_datetime.isoformat(),
                            "end_time": end_datetime.isoformat()
                        })
                        
                        if response.status_code == 201:
                            st.session_state.show_success_message = True
                            st.session_state.success_message = "Подію успішно додано!"
                        else:
                            st.error("Помилка при додаванні події")

        try:
            # Форматування подій для календаря
            calendar_events = []
            for event in events:
                calendar_events.append({
                    'id': str(event['id']),  # ID повинен бути рядком
                    'title': event['title'],
                    'start': event['start_time'],
                    'end': event['end_time'],
                    'extendedProps': {
                        'type': event['event_type'],
                        'description': event.get('description', '')
                    },
                    'backgroundColor': {
                        'meeting': '#4CAF50',
                        'deadline': '#f44336',
                        'other': '#2196F3'
                    }.get(event['event_type'], '#9E9E9E')
                })

            # Конфігурація календаря
            calendar_options = {
                "headerToolbar": {
                    "left": "prev,next today",
                    "center": "title",
                    "right": "dayGridMonth,timeGridWeek,timeGridDay"
                },
                "initialView": "dayGridMonth",
                "selectable": True,
                "editable": False,
                "dayMaxEvents": True,
                "slotMinTime": "08:00:00",
                "slotMaxTime": "20:00:00",
                "expandRows": True,
                "locale": "uk"
            }

            # Відображення календаря в контейнері
            with st.container():
                calendar(
                    events=calendar_events,
                    options=calendar_options,
                    key=f"calendar_{project_id}"  # Унікальний ключ для кожного проекту
                )

        except Exception as e:
            st.error(f"Помилка при відображенні календаря: {str(e)}")

        # Показ списку подій
        st.subheader("Список подій")
        for event in sorted(events, key=lambda x: x['start_time']):
            with st.expander(f"{event['title']} ({event['start_time']})"):
                st.markdown(f"""
                    <div class="event-{event['event_type']}">
                        <p><strong>Опис:</strong> {event.get('description', 'Без опису')}</p>
                        <p><strong>Тип:</strong> {
                            {'meeting': 'Зустріч', 
                             'deadline': 'Дедлайн', 
                             'other': 'Інше'
                            }.get(event['event_type'], 'Інше')
                        }</p>
                        <p><strong>Початок:</strong> {event['start_time']}</p>
                        <p><strong>Кінець:</strong> {event['end_time']}</p>
                    </div>
                """, unsafe_allow_html=True)

def create_project():
    st.title("Створення нового проєкту")
    
    with st.form("create_project_form"):
        name = st.text_input("Назва проєкту")
        description = st.text_area("Опис проєкту")
        deadline = st.date_input("Дедлайн")
        max_specialists = st.number_input("Максимальна кількість спеціалістів", 
                                     min_value=1, value=5)
        
        submitted = st.form_submit_button("Створити проєкт")
        
        if submitted:
            try:
                if not name:
                    st.error("Введіть назву проєкту")
                    return
                    
                data = {
                    "name": name,
                    "description": description,
                    "deadline": deadline.strftime("%Y-%m-%d"),
                    "max_specialists": max_specialists
                }
                
                response = api_client.post("/projects", data)
                
                if response.status_code == 201:
                    st.success("✅ Проєкт успішно створено!")
                    time.sleep(1)  # Даємо користувачу час побачити повідомлення про успіх
                    st.session_state.current_page = 'projects'
                    st.rerun()
                else:
                    error_msg = response.json().get('message', 'Невідома помилка')
                    st.error(f"❌ Помилка при створенні проєкту: {error_msg}")
                    
            except Exception as e:
                st.error(f"❌ Помилка: {str(e)}")

    if st.button("↩️ Назад до проєктів"):
        st.session_state.current_page = 'projects'
        st.rerun()

def show_comments(project_id):
    st.header("Обговорення")
    
    # Додавання нового коментаря
    if st.session_state.user['role'] != 'admin':
        with st.form("new_comment_form"):
            comment_text = st.text_area("Новий коментар")
            if st.form_submit_button("Додати коментар"):
                response = api_client.post(f"/projects/{project_id}/comments", {
                    "content": comment_text
                })
                if response.status_code == 201:
                    st.success("Коментар додано!")
                    st.rerun()
                else:
                    st.error("Помилка при додаванні коментаря")
    
    # Відображення коментарів
    response = api_client.get(f"/projects/{project_id}/comments")
    if response.status_code == 200:
        comments = response.json()
        for comment in comments:
            st.markdown(f"""
                <div class="comment-card">
                    <strong>{comment['author_name']}</strong>
                    <small>{comment['timestamp']}</small>
                    <p>{comment['content']}</p>
                </div>
            """, unsafe_allow_html=True)
    else:
        st.error("Помилка при завантаженні коментарів")

def show_files(project_id):
    st.header("Файли")
    
    # Завантаження файлу
    if st.session_state.user['role'] != 'admin':
        uploaded_file = st.file_uploader("Завантажити файл")
        if uploaded_file:
            if st.button("Завантажити"):
                upload_file(project_id, uploaded_file)
    
    # Список файлів
    response = api_client.get(f"/projects/{project_id}/files")
    if response.status_code == 200:
        files = response.json()
        for file in files:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(f"""
                    <div class="file-card">
                        <strong>{file['filename']}</strong><br>
                        <small>Завантажив: {file['user_name']} • {file['upload_date']}</small>
                    </div>
                """, unsafe_allow_html=True)
            
            with col2:
                if st.button("Завантажити", key=f"download_{file['id']}"):
                    download_file(file['id'])

# Допоміжні функції
def set_current_project(project):
    st.session_state.current_project = project
    st.session_state.current_page = 'project_details'
    st.rerun()

def join_project(project_id):
    response = api_client.post(f"/projects/{project_id}/join", {})
    if response.status_code == 200:
        st.success("Ви успішно приєднались до проекту!")
        st.rerun()
    else:
        st.error("Помилка при приєднанні до проекту")

def delete_project(project_id):
    if st.session_state.user['role'] == 'admin':
        response = api_client.delete(f"/projects/{project_id}")
        if response.status_code == 200:
            st.success("Проект видалено!")
            st.rerun()
        else:
            st.error("Помилка при видаленні проекту")

def create_task(project_id, title, description, deadline, assigned_to):
    response = api_client.post(f"/projects/{project_id}/tasks", {
        "title": title,
        "description": description,
        "deadline": deadline.isoformat(),
        "assigned_to": assigned_to
    })
    if response.status_code == 201:
        st.success("Завдання створено!")
        st.rerun()
    else:
        st.error("Помилка при створенні завдання")

def update_task_status(project_id, task_id, new_status):
    response = api_client.put(f"/projects/{project_id}/tasks/{task_id}", {
        "status": new_status
    })
    if response.status_code == 200:
        st.rerun()
    else:
        st.error("Помилка при оновленні статусу завдання")

def create_event(project_id, title, description, event_type, start_date, end_date):
    response = api_client.post(f"/projects/{project_id}/calendar", {
        "title": title,
        "description": description,
        "event_type": event_type,
        "start_time": start_date.isoformat(),
        "end_time": end_date.isoformat()
    })
    if response.status_code == 201:
        st.success("Подію створено!")
        st.rerun()
    else:
        st.error("Помилка при створенні події")

def create_comment(project_id, content):
    response = api_client.post(f"/projects/{project_id}/comments", {
        "content": content
    })
    if response.status_code == 201:
        st.success("Коментар додано!")
        st.rerun()
    else:
        st.error("Помилка при додаванні коментаря")

def upload_file(project_id, file):
    files = {"file": file}
    response = api_client.upload_file(f"/projects/{project_id}/files", files)
    if response.status_code == 201:
        st.success("Файл завантажено!")
        st.rerun()
    else:
        st.error("Помилка при завантаженні файлу")

def download_file(file_id):
    response = api_client.get(f"/files/{file_id}/download")
    if response.status_code == 200:
        st.download_button(
            label="Завантажити файл",
            data=response.content,
            file_name=response.headers['Content-Disposition'].split('filename=')[1],
            mime=response.headers['Content-Type']
        )

def logout():
    st.session_state.token = None
    st.session_state.user = None
    st.session_state.current_page = 'login'
    st.rerun()

def main():
    update_notifications()
    
    if not st.session_state.token:
        if st.session_state.current_page == 'register':
            show_register_page()
        else:
            show_login_page()
    else:
        with st.sidebar:
            st.markdown(f"""
                <div class="user-info">
                    <h3>👤 {st.session_state.user['name']}</h3>
                    <p>{ROLES[st.session_state.user['role']]}</p>
                </div>
            """, unsafe_allow_html=True)
            
            st.button("Проєкти", on_click=lambda: setattr(st.session_state, 'current_page', 'projects'))
            
            if st.session_state.user['role'] == 'admin':
                st.button("Користувачі", on_click=lambda: setattr(st.session_state, 'current_page', 'admin_panel'))
            
            if st.session_state.unread_count > 0:
                st.button(f"Сповіщення ({st.session_state.unread_count})")
            
            st.button("Вийти", on_click=logout)
        
        # Основний контент
        if st.session_state.current_page == 'projects':
            show_projects()
        elif st.session_state.current_page == 'create_project':
            create_project()
        elif st.session_state.current_page == 'project_details':
            show_project_details()
        elif st.session_state.current_page == 'admin_panel':
            show_admin_panel()

if __name__ == "__main__":
    main()