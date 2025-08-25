from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
import jwt
from datetime import datetime, timedelta, timezone
from functools import wraps
import os
from werkzeug.utils import secure_filename
import logging



# Налаштування логування
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



app = Flask(__name__)
CORS(app)
app.config['SECRET_KEY'] = 'your-secret-key'  # В продакшені використовувати безпечний ключ
app.config['UPLOAD_FOLDER'] = 'files'

# Константи
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx', 'xls', 'xlsx'}
TOKEN_EXPIRE_HOURS = 24

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def init_db():
    conn = sqlite3.connect('project_management.db')
    c = conn.cursor()
    
    # Таблиця користувачів
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  email TEXT UNIQUE NOT NULL,
                  password TEXT NOT NULL,
                  role TEXT NOT NULL,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  last_login DATETIME)''')
    
    # Таблиця проєктів (змінюємо поле teacher_id на manager_id, max_students на max_specialists)
    c.execute('''CREATE TABLE IF NOT EXISTS projects
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  description TEXT,
                  manager_id INTEGER,
                  deadline DATE,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  status TEXT DEFAULT 'active' CHECK(status IN ('active', 'archived', 'completed')),
                  max_specialists INTEGER DEFAULT 0,
                  FOREIGN KEY (manager_id) REFERENCES users (id))''')
    
    # Таблиця учасників проєкту
    c.execute('''CREATE TABLE IF NOT EXISTS project_members
                 (project_id INTEGER,
                  user_id INTEGER,
                  role TEXT DEFAULT 'member',
                  join_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (project_id) REFERENCES projects (id),
                  FOREIGN KEY (user_id) REFERENCES users (id),
                  PRIMARY KEY (project_id, user_id))''')
    
    # Таблиця завдань
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  project_id INTEGER,
                  title TEXT NOT NULL,
                  description TEXT,
                  status TEXT CHECK(status IN ('not_started', 'in_progress', 'completed')) DEFAULT 'not_started',
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  deadline DATE,
                  assigned_to INTEGER,
                  priority TEXT DEFAULT 'medium' CHECK(priority IN ('low', 'medium', 'high')),
                  FOREIGN KEY (project_id) REFERENCES projects (id),
                  FOREIGN KEY (assigned_to) REFERENCES users (id))''')
    
    # Таблиця подій календаря
    c.execute('''CREATE TABLE IF NOT EXISTS calendar_events
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  project_id INTEGER,
                  title TEXT NOT NULL,
                  description TEXT,
                  event_type TEXT NOT NULL,
                  start_time DATETIME NOT NULL,
                  end_time DATETIME NOT NULL,
                  created_by INTEGER,
                  recurrence TEXT,
                  FOREIGN KEY (project_id) REFERENCES projects (id),
                  FOREIGN KEY (created_by) REFERENCES users (id))''')
    
    # Таблиця сповіщень
    c.execute('''CREATE TABLE IF NOT EXISTS notifications
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  project_id INTEGER,
                  type TEXT NOT NULL,
                  message TEXT NOT NULL,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  is_read BOOLEAN DEFAULT 0,
                  priority TEXT DEFAULT 'normal' CHECK(priority IN ('low', 'normal', 'high')),
                  expiry_date DATETIME,
                  FOREIGN KEY (user_id) REFERENCES users (id),
                  FOREIGN KEY (project_id) REFERENCES projects (id))''')
    
    # Таблиця коментарів
    c.execute('''CREATE TABLE IF NOT EXISTS comments
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  project_id INTEGER,
                  user_id INTEGER,
                  content TEXT NOT NULL,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  parent_id INTEGER,
                  FOREIGN KEY (project_id) REFERENCES projects (id),
                  FOREIGN KEY (user_id) REFERENCES users (id),
                  FOREIGN KEY (parent_id) REFERENCES comments (id))''')
    
    # Таблиця файлів
    c.execute('''CREATE TABLE IF NOT EXISTS files
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  project_id INTEGER,
                  user_id INTEGER,
                  filename TEXT NOT NULL,
                  file_size INTEGER,
                  file_type TEXT,
                  upload_date DATETIME DEFAULT CURRENT_TIMESTAMP,
                  file_path TEXT NOT NULL,
                  FOREIGN KEY (project_id) REFERENCES projects (id),
                  FOREIGN KEY (user_id) REFERENCES users (id))''')
    
    # Змінюємо таблицю оцінок на таблицю рейтингів
    c.execute('''CREATE TABLE IF NOT EXISTS ratings
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  project_id INTEGER,
                  specialist_id INTEGER,
                  rating FLOAT CHECK(rating >= 0 AND rating <= 100),
                  comment TEXT,
                  manager_id INTEGER,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  type TEXT DEFAULT 'final' CHECK(type IN ('interim', 'final')),
                  FOREIGN KEY (project_id) REFERENCES projects (id),
                  FOREIGN KEY (specialist_id) REFERENCES users (id),
                  FOREIGN KEY (manager_id) REFERENCES users (id))''')
    
    # Таблиця активності користувачів
    c.execute('''CREATE TABLE IF NOT EXISTS user_activity
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  user_id INTEGER,
                  project_id INTEGER,
                  action_type TEXT NOT NULL,
                  action_details TEXT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  FOREIGN KEY (user_id) REFERENCES users (id),
                  FOREIGN KEY (project_id) REFERENCES projects (id))''')
    
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect('project_management.db')
    conn.row_factory = sqlite3.Row
    return conn

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'message': 'Token is missing'}), 401

        try:
            if 'Bearer ' in token:
                token = token.split('Bearer ')[1]
            data = jwt.decode(token, app.config['SECRET_KEY'], algorithms=["HS256"])
            current_user = get_user_by_id(data['user_id'])
            if not current_user:
                return jsonify({'message': 'Invalid token'}), 401
        except jwt.ExpiredSignatureError:
            return jsonify({'message': 'Token expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'message': 'Invalid token'}), 401

        return f(current_user, *args, **kwargs)
    return decorated


def log_activity(user_id, project_id, action_type, action_details=None):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO user_activity (user_id, project_id, action_type, action_details)
            VALUES (?, ?, ?, ?)
        """, (user_id, project_id, action_type, action_details))
        conn.commit()
    except Exception as e:
        logger.error(f"Error logging activity: {str(e)}")
    finally:
        conn.close()

def create_notification(user_id, project_id, notification_type, message, priority='normal', expiry_days=30):
    conn = None
    try:
        conn = get_db()
        c = conn.cursor()
        expiry_date = datetime.now(timezone.utc) + timedelta(days=expiry_days)
        
        # Встановлюємо таймаут для операцій з базою даних
        conn.execute("PRAGMA busy_timeout = 5000")  # таймаут 5 секунд
        
        c.execute("""
            INSERT INTO notifications (user_id, project_id, type, message, priority, expiry_date)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, project_id, notification_type, message, priority, expiry_date))
        
        conn.commit()
    except Exception as e:
        logger.error(f"Помилка створення сповіщення: {str(e)}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
# Допоміжні функції для роботи з користувачами
def get_user_by_id(user_id):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = c.fetchone()
    conn.close()
    
    if user:
        return {
            'id': user['id'],
            'name': user['name'],
            'email': user['email'],
            'role': user['role']
        }
    return None

def get_user_by_email(email):
    conn = get_db()
    c = conn.cursor()
    c.execute("SELECT * FROM users WHERE email=?", (email,))
    user = c.fetchone()
    conn.close()
    return user if user else None

# Аутентифікація та реєстрація
@app.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    
    if not all(k in data for k in ['name', 'email', 'password', 'role']):
        return jsonify({'message': 'Відсутні обов\'язкові поля'}), 400
    
    if get_user_by_email(data['email']):
        return jsonify({'message': 'Користувач вже існує'}), 400
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        hashed_password = generate_password_hash(data['password'], method='scrypt')
        c.execute("""
            INSERT INTO users (name, email, password, role, created_at)
            VALUES (?, ?, ?, ?, ?)
        """, (data['name'], data['email'], hashed_password, data['role'], 
              datetime.now(timezone.utc)))
        
        conn.commit()
        return jsonify({'message': 'Реєстрація успішна'}), 201
    
    except Exception as e:
        logger.error(f"Помилка реєстрації: {str(e)}")
        return jsonify({'message': 'Помилка під час реєстрації'}), 500
    finally:
        conn.close()

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    
    if not all(k in data for k in ['email', 'password']):
        return jsonify({'message': 'Відсутня електронна пошта або пароль'}), 400
    
    try:
        user = get_user_by_email(data['email'])
        if not user:
            return jsonify({'message': 'Користувача не знайдено'}), 401
        
        if check_password_hash(user['password'], data['password']):
            # Оновлення часу останнього входу
            conn = get_db()
            c = conn.cursor()
            c.execute("UPDATE users SET last_login = ? WHERE id = ?",
                     (datetime.now(timezone.utc), user['id']))
            conn.commit()
            conn.close()
            
            token = jwt.encode({
                'user_id': user['id'],
                'exp': datetime.now(timezone.utc) + timedelta(hours=TOKEN_EXPIRE_HOURS)
            }, app.config['SECRET_KEY'])
            
            return jsonify({
                'token': token,
                'user': {
                    'id': user['id'],
                    'name': user['name'],
                    'email': user['email'],
                    'role': user['role']
                }
            })
        
        return jsonify({'message': 'Невірний пароль'}), 401
    
    except Exception as e:
        logger.error(f"Помилка входу: {str(e)}")
        return jsonify({'message': 'Помилка під час входу'}), 500

# Маршрути для проєктів
@app.route('/projects', methods=['GET'])
@token_required
def get_projects(current_user):
    try:
        conn = get_db()
        c = conn.cursor()
        
        # SQL запит залежить від ролі користувача
        if current_user['role'] == 'admin':
            # Адміністратор бачить усі проєкти
            c.execute("""
                SELECT 
                    p.*,
                    u.name as manager_name,
                    COUNT(DISTINCT pm.user_id) as members_count
                FROM projects p
                LEFT JOIN users u ON p.manager_id = u.id
                LEFT JOIN project_members pm ON p.id = pm.project_id
                WHERE p.status != 'archived'
                GROUP BY p.id
            """)
            
        elif current_user['role'] == 'manager':
            # Менеджер бачить свої проєкти
            c.execute("""
                SELECT 
                    p.*,
                    u.name as manager_name,
                    COUNT(DISTINCT pm.user_id) as members_count
                FROM projects p
                LEFT JOIN users u ON p.manager_id = u.id
                LEFT JOIN project_members pm ON p.id = pm.project_id
                WHERE p.manager_id = ? AND p.status != 'archived'
                GROUP BY p.id
            """, (current_user['id'],))
            
        else:  # specialist
            # Спеціаліст бачить всі активні проєкти та свою участь в них
            c.execute("""
                SELECT 
                    p.*,
                    u.name as manager_name,
                    COUNT(DISTINCT pm.user_id) as members_count,
                    CASE WHEN EXISTS (
                        SELECT 1 FROM project_members 
                        WHERE project_id = p.id AND user_id = ?
                    ) THEN 1 ELSE 0 END as is_member
                FROM projects p
                LEFT JOIN users u ON p.manager_id = u.id
                LEFT JOIN project_members pm ON p.id = pm.project_id
                WHERE p.status = 'active'
                GROUP BY p.id
            """, (current_user['id'],))
        
        projects = []
        rows = c.fetchall()
        
        for row in rows:
            # Отримуємо кількість непрочитаних сповіщень
            if current_user['role'] == 'specialist':
                c.execute("""
                    SELECT COUNT(*) FROM notifications
                    WHERE project_id = ? AND user_id = ? AND is_read = 0
                """, (row['id'], current_user['id']))
            else:
                c.execute("""
                    SELECT COUNT(*) FROM notifications
                    WHERE project_id = ? AND is_read = 0
                """, (row['id'],))
            
            unread_count = c.fetchone()[0]
            
            project = {
                'id': row['id'],
                'name': row['name'],
                'description': row['description'],
                'manager_id': row['manager_id'],
                'manager_name': row['manager_name'],
                'deadline': row['deadline'],
                'status': row['status'],
                'members_count': row['members_count'],
                'unread_notifications': unread_count
            }
            
            if current_user['role'] == 'specialist':
                project['is_member'] = bool(row['is_member'])
            
            projects.append(project)
        
        return jsonify(projects)
    
    except Exception as e:
        logger.error(f"Помилка отримання проєктів: {str(e)}")
        return jsonify({'message': 'Помилка отримання проєктів'}), 500
    finally:
        conn.close()

@app.route('/projects/<int:project_id>/comments', methods=['GET'])
@token_required
def get_comments(current_user, project_id):
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            SELECT c.id, c.content, c.timestamp, u.name as author_name
            FROM comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.project_id = ?
            ORDER BY c.timestamp ASC
        """, (project_id,))
        comments = [{
            'id': row['id'],
            'content': row['content'],
            'timestamp': row['timestamp'],
            'author_name': row['author_name']
        } for row in c.fetchall()]
        return jsonify(comments), 200
    except Exception as e:
        logger.error(f"Error fetching comments: {str(e)}")
        return jsonify({'message': 'Error fetching comments'}), 500
    finally:
        conn.close()

@app.route('/projects/<int:project_id>/comments', methods=['POST'])
@token_required
def add_comment(current_user, project_id):
    data = request.get_json()
    if 'content' not in data:
        return jsonify({'message': 'Missing comment content'}), 400
    try:
        conn = get_db()
        c = conn.cursor()
        c.execute("""
            INSERT INTO comments (project_id, user_id, content)
            VALUES (?, ?, ?)
        """, (project_id, current_user['id'], data['content']))
        conn.commit()
        return jsonify({'message': 'Comment added successfully'}), 201
    except Exception as e:
        logger.error(f"Error adding comment: {str(e)}")
        return jsonify({'message': 'Error adding comment'}), 500
    finally:
        conn.close()


@app.route('/projects', methods=['POST'])
@token_required
def create_project(current_user):
    if current_user['role'] not in ['manager', 'admin']:
        return jsonify({'message': 'Недостатньо прав'}), 403
    
    data = request.get_json()
    if not data:
        return jsonify({'message': 'Дані не надані'}), 400
    
    required_fields = ['name', 'description', 'deadline']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Відсутні обов\'язкові поля'}), 400
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Створюємо проєкт з правильними назвами колонок
        c.execute("""
            INSERT INTO projects (
                name, description, manager_id, deadline, 
                max_specialists, status, created_at
            )
            VALUES (?, ?, ?, ?, ?, 'active', datetime('now'))
        """, (
            data['name'],
            data['description'],
            current_user['id'],
            data['deadline'],
            data.get('max_specialists', 0)
        ))
        
        project_id = c.lastrowid
        
        # Додаємо творця як учасника проєкту
        c.execute("""
            INSERT INTO project_members (project_id, user_id, role, join_date)
            VALUES (?, ?, ?, datetime('now'))
        """, (project_id, current_user['id'], current_user['role']))
        
        # Логуємо активність
        log_activity(
            current_user['id'],
            project_id,
            'project_created',
            f"Створено проєкт: {data['name']}"
        )
        
        conn.commit()
        return jsonify({
            'message': 'Проєкт успішно створено',
            'project_id': project_id
        }), 201
        
    except Exception as e:
        logger.error(f"Помилка створення проєкту: {str(e)}")
        if conn:
            conn.rollback()
        return jsonify({'message': 'Помилка створення проєкту'}), 500
        
    finally:
        if conn:
            conn.close()

@app.route('/projects/<int:project_id>', methods=['PUT'])
@token_required
def update_project(current_user, project_id):
    if current_user['role'] not in ['manager', 'admin']:
        return jsonify({'message': 'Недостатньо прав'}), 403
    
    data = request.get_json()
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Перевіряємо права на проєкт
        c.execute("SELECT manager_id FROM projects WHERE id = ?", (project_id,))
        project = c.fetchone()
        
        if not project:
            return jsonify({'message': 'Проєкт не знайдено'}), 404
        
        if current_user['role'] == 'manager' and project['manager_id'] != current_user['id']:
            return jsonify({'message': 'Недостатньо прав'}), 403
        
        # Оновлюємо проєкт
        update_fields = []
        params = []
        
        if 'name' in data:
            update_fields.append('name = ?')
            params.append(data['name'])
        
        if 'description' in data:
            update_fields.append('description = ?')
            params.append(data['description'])
        
        if 'deadline' in data:
            update_fields.append('deadline = ?')
            params.append(data['deadline'])
        
        if 'status' in data and current_user['role'] == 'admin':
            update_fields.append('status = ?')
            params.append(data['status'])
        
        if update_fields:
            params.append(project_id)
            query = f"UPDATE projects SET {', '.join(update_fields)} WHERE id = ?"
            c.execute(query, params)
            
            # Логуємо зміни
            log_activity(current_user['id'], project_id, 'project_updated', 
                        f"Оновлено поля проєкту: {', '.join(update_fields)}")
            
            # Сповіщаємо учасників
            c.execute("SELECT user_id FROM project_members WHERE project_id = ?", (project_id,))
            members = c.fetchall()
            
            for member in members:
                create_notification(
                    member['user_id'],
                    project_id,
                    'project_update',
                    f"Проєкт '{data.get('name', 'Невідомий')}' був оновлений"
                )
        
        conn.commit()
        return jsonify({'message': 'Проєкт успішно оновлено'})
    
    except Exception as e:
        logger.error(f"Помилка оновлення проєкту: {str(e)}")
        return jsonify({'message': 'Помилка оновлення проєкту'}), 500
    finally:
        conn.close()

@app.route('/projects/<int:project_id>', methods=['DELETE'])
@token_required
def delete_project(current_user, project_id):
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Проверяем существование проекта
        c.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not c.fetchone():
            return jsonify({'message': 'Project not found'}), 404
        
        # Удаляем все связанные данные
        tables = [
            'project_members', 'tasks', 'calendar_events',
            'notifications', 'comments', 'grades',
            'user_activity', 'files'
        ]
        
        for table in tables:
            c.execute(f"DELETE FROM {table} WHERE project_id = ?", (project_id,))
        
        # Удаляем сам проект
        c.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        
        # Логируем удаление
        log_activity(current_user['id'], None, 'project_deleted', 
                    f"Deleted project ID: {project_id}")
        
        conn.commit()
        return jsonify({'message': 'Project deleted successfully'})
    
    except Exception as e:
        logger.error(f"Error deleting project: {str(e)}")
        return jsonify({'message': 'Error deleting project'}), 500
    finally:
        conn.close()

@app.route('/projects/<int:project_id>/join', methods=['POST'])
@token_required
def join_project(current_user, project_id):
    if current_user['role'] != 'specialist':
        return jsonify({'message': 'Тільки спеціалісти можуть приєднуватись до проєктів'}), 403
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Перевіряємо існування проєкту та його статус
        c.execute("""
            SELECT id, status, manager_id FROM projects 
            WHERE id = ? AND status = 'active'
        """, (project_id,))
        
        project = c.fetchone()
        if not project:
            return jsonify({'message': 'Проєкт не знайдено або він не активний'}), 404
        
        # Перевіряємо, чи не є спеціаліст вже учасником
        c.execute("""
            SELECT 1 FROM project_members
            WHERE project_id = ? AND user_id = ?
        """, (project_id, current_user['id']))
        
        if c.fetchone():
            return jsonify({'message': 'Ви вже є учасником цього проєкту'}), 400
        
        # Додаємо спеціаліста в проєкт
        c.execute("""
            INSERT INTO project_members (project_id, user_id, role)
            VALUES (?, ?, 'specialist')
        """, (project_id, current_user['id']))
        
        # Отримуємо інформацію про проєкт для сповіщення
        c.execute("""
            SELECT p.name, u.name as specialist_name
            FROM projects p
            JOIN users u ON u.id = ?
            WHERE p.id = ?
        """, (current_user['id'], project_id))
        
        project_info = c.fetchone()
        
        # Створюємо сповіщення для менеджера
        create_notification(
            project['manager_id'],
            project_id,
            'new_member',
            f"Спеціаліст {project_info['specialist_name']} приєднався до проєкту '{project_info['name']}'"
        )
        
        # Логуємо дію
        log_activity(
            current_user['id'],
            project_id,
            'project_joined',
            f"Приєднався до проєкту: {project_info['name']}"
        )
        
        conn.commit()
        return jsonify({'message': 'Успішно приєднано до проєкту'})
        
    except Exception as e:
        logger.error(f"Помилка приєднання до проєкту: {str(e)}")
        conn.rollback()
        return jsonify({'message': 'Помилка приєднання до проєкту'}), 500
    finally:
        conn.close()

@app.route('/projects/<int:project_id>/calendar', methods=['GET'])
@token_required
def get_calendar_events(current_user, project_id):
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute("""
            SELECT e.*, u.name as creator_name
            FROM calendar_events e
            LEFT JOIN users u ON e.created_by = u.id
            WHERE e.project_id = ?
            ORDER BY e.start_time
        """, (project_id,))
        
        events = [{
            'id': row['id'],
            'title': row['title'],
            'description': row['description'],
            'event_type': row['event_type'],
            'start_time': row['start_time'],
            'end_time': row['end_time'],
            'created_by': row['creator_name']
        } for row in c.fetchall()]
        
        return jsonify(events)
    except Exception as e:
        logger.error(f"Error getting calendar events: {str(e)}")
        return jsonify({'message': 'Error getting calendar events'}), 500
    finally:
        conn.close()

@app.route('/projects/<int:project_id>/calendar', methods=['POST'])
@token_required
def create_calendar_event(current_user, project_id):
    data = request.get_json()
    
    if not all(k in data for k in ['title', 'event_type', 'start_time', 'end_time']):
        return jsonify({'message': 'Відсутні обов\'язкові поля'}), 400
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Перевіряємо, чи існує проєкт і чи має користувач доступ
        c.execute("""
            SELECT 1 FROM project_members 
            WHERE project_id = ? AND user_id = ?
        """, (project_id, current_user['id']))
        
        if not c.fetchone() and current_user['role'] != 'admin':
            return jsonify({'message': 'У вас немає доступу до цього проєкту'}), 403
        
        # Створюємо подію
        c.execute("""
            INSERT INTO calendar_events (
                project_id, title, description, event_type,
                start_time, end_time, created_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            project_id,
            data['title'],
            data.get('description', ''),
            data['event_type'],
            data['start_time'],
            data['end_time'],
            current_user['id']
        ))
        
        event_id = c.lastrowid
        
        # Створюємо сповіщення для всіх учасників проєкту
        c.execute("""
            SELECT user_id FROM project_members
            WHERE project_id = ? AND user_id != ?
        """, (project_id, current_user['id']))
        
        for member in c.fetchall():
            create_notification(
                member['user_id'],
                project_id,
                'new_event',
                f"Додано нову подію до календаря: {data['title']}"
            )
        
        # Логуємо дію
        log_activity(
            current_user['id'],
            project_id,
            'event_created',
            f"Створено подію календаря: {data['title']}"
        )
        
        conn.commit()
        return jsonify({
            'message': 'Подію успішно додано',
            'event_id': event_id
        }), 201
        
    except Exception as e:
        logger.error(f"Помилка створення події: {str(e)}")
        return jsonify({'message': 'Помилка створення події'}), 500
    finally:
        conn.close()

@app.route('/projects/<int:project_id>/grades', methods=['GET'])
@token_required
def get_grades(current_user, project_id):
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Перевіряємо права доступу
        if current_user['role'] == 'specialist':
            # Спеціаліст бачить тільки свої оцінки
            c.execute("""
                SELECT g.*, u.name as student_name, t.name as teacher_name
                FROM grades g
                JOIN users u ON g.student_id = u.id
                JOIN users t ON g.teacher_id = t.id
                WHERE g.project_id = ? AND g.student_id = ?
            """, (project_id, current_user['id']))
        else:
            # Менеджер та адмін бачать всі оцінки
            c.execute("""
                SELECT g.*, u.name as student_name, t.name as teacher_name
                FROM grades g
                JOIN users u ON g.student_id = u.id
                JOIN users t ON g.teacher_id = t.id
                WHERE g.project_id = ?
            """, (project_id,))
        
        # Повертаємо як "ratings"
        grades = [{
            'id': row['id'],
            'specialist_id': row['student_id'],  
            'specialist_name': row['student_name'],  
            'rating': row['grade'],  
            'comment': row['comment'],
            'manager_name': row['teacher_name'],  
            'timestamp': row['timestamp'],
            'type': row['type']
        } for row in c.fetchall()]
        
        return jsonify(grades)
    
    except Exception as e:
        logger.error(f"Помилка отримання оцінок: {str(e)}")
        return jsonify({'message': 'Помилка отримання оцінок'}), 500
    finally:
        conn.close()

@app.route('/projects/<int:project_id>/members', methods=['GET'])
@token_required
def get_project_members(current_user, project_id):
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Отримуємо учасників проекту з їх ролями
        c.execute("""
            SELECT u.id, u.name, u.email, pm.role
            FROM project_members pm
            JOIN users u ON pm.user_id = u.id
            WHERE pm.project_id = ?
        """, (project_id,))
        
        members = [{
            'id': row['id'],
            'name': row['name'],
            'email': row['email'],
            'role': row['role']
        } for row in c.fetchall()]
        
        return jsonify(members)
    
    except Exception as e:
        logger.error(f"Error getting project members: {str(e)}")
        return jsonify({'message': 'Error getting project members'}), 500
    finally:
        conn.close()

@app.route('/projects/<int:project_id>/files', methods=['GET'])
@token_required
def get_project_files(current_user, project_id):
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute("""
            SELECT f.*, u.name as user_name
            FROM files f
            JOIN users u ON f.user_id = u.id
            WHERE f.project_id = ?
            ORDER BY f.upload_date DESC
        """, (project_id,))
        
        files = [{
            'id': row['id'],
            'filename': row['filename'],
            'file_size': row['file_size'],
            'file_type': row['file_type'],
            'upload_date': row['upload_date'],
            'user_name': row['user_name']
        } for row in c.fetchall()]
        
        return jsonify(files)
    
    except Exception as e:
        logger.error(f"Error getting project files: {str(e)}")
        return jsonify({'message': 'Error getting project files'}), 500
    finally:
        conn.close()



@app.route('/users', methods=['GET'])
@token_required
def get_users(current_user):
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute("""
            SELECT u.id, u.name, u.email, u.role, u.created_at,
                   COUNT(DISTINCT pm.project_id) as projects_count,
                   AVG(g.grade) as average_grade
            FROM users u
            LEFT JOIN project_members pm ON u.id = pm.user_id
            LEFT JOIN grades g ON u.id = g.student_id
            GROUP BY u.id
        """)
        
        users = [{
            'id': row['id'],
            'name': row['name'],
            'email': row['email'],
            'role': row['role'],
            'created_at': row['created_at'],
            'projects_count': row['projects_count'],
            'average_grade': float(row['average_grade']) if row['average_grade'] else None
        } for row in c.fetchall()]
        
        return jsonify(users)
    
    except Exception as e:
        logger.error(f"Error getting users: {str(e)}")
        return jsonify({'message': 'Error getting users'}), 500
    finally:
        conn.close()

@app.route('/notifications', methods=['GET'])
@token_required
def get_notifications(current_user):
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Отримуємо сповіщення з урахуванням терміну дії
        c.execute("""
            SELECT n.*, p.name as project_name
            FROM notifications n
            LEFT JOIN projects p ON n.project_id = p.id
            WHERE n.user_id = ? 
            AND (n.expiry_date IS NULL OR n.expiry_date > datetime('now'))
            ORDER BY n.created_at DESC
            LIMIT 50
        """, (current_user['id'],))
        
        notifications = [{
            'id': row['id'],
            'type': row['type'],
            'message': row['message'],
            'project_id': row['project_id'],
            'project_name': row['project_name'],
            'created_at': row['created_at'],
            'is_read': bool(row['is_read']),
            'priority': row['priority']
        } for row in c.fetchall()]
        
        return jsonify(notifications)
    
    except Exception as e:
        logger.error(f"Error getting notifications: {str(e)}")
        return jsonify({'message': 'Error getting notifications'}), 500
    finally:
        conn.close()

@app.route('/notifications/mark-read', methods=['POST'])
@token_required
def mark_notifications_read(current_user):
    data = request.get_json()
    if not data or 'notification_ids' not in data:
        return jsonify({'message': 'Missing notification IDs'}), 400
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Позначаємо сповіщення як прочитані
        for notification_id in data['notification_ids']:
            c.execute("""
                UPDATE notifications
                SET is_read = 1
                WHERE id = ? AND user_id = ?
            """, (notification_id, current_user['id']))
        
        conn.commit()
        return jsonify({'message': 'Notifications marked as read'})
    
    except Exception as e:
        logger.error(f"Error marking notifications as read: {str(e)}")
        return jsonify({'message': 'Error marking notifications as read'}), 500
    finally:
        conn.close()

@app.route('/notifications/unread-count', methods=['GET'])
@token_required
def get_unread_notifications_count(current_user):
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute("""
            SELECT COUNT(*) as count
            FROM notifications
            WHERE user_id = ? AND is_read = 0
            AND (expiry_date IS NULL OR expiry_date > datetime('now'))
        """, (current_user['id'],))
        
        result = c.fetchone()
        return jsonify({'unread_count': result['count']})
    
    except Exception as e:
        logger.error(f"Error getting unread notifications count: {str(e)}")
        return jsonify({'message': 'Error getting unread count'}), 500
    finally:
        conn.close()

@app.route('/projects/<int:project_id>/tasks', methods=['GET'])
@token_required
def get_tasks(current_user, project_id):
    try:
        conn = get_db()
        c = conn.cursor()
        
        c.execute("""
            SELECT t.*, u.name as assigned_user_name
            FROM tasks t
            LEFT JOIN users u ON t.assigned_to = u.id
            WHERE t.project_id = ?
            ORDER BY t.created_at DESC
        """, (project_id,))
        
        tasks = [{
            'id': row['id'],
            'title': row['title'],
            'description': row['description'],
            'status': row['status'],
            'priority': row['priority'],
            'created_at': row['created_at'],
            'deadline': row['deadline'],
            'assigned_to': row['assigned_to'],
            'assigned_user_name': row['assigned_user_name']
        } for row in c.fetchall()]
        
        return jsonify(tasks)
    
    except Exception as e:
        logger.error(f"Error getting tasks: {str(e)}")
        return jsonify({'message': 'Error getting tasks'}), 500
    finally:
        conn.close()

@app.route('/projects/<int:project_id>/tasks', methods=['POST'])
@token_required
def create_task(current_user, project_id):
    if current_user['role'] != 'manager':
        return jsonify({'message': 'Тільки менеджери можуть створювати завдання'}), 403
    
    data = request.get_json()
    required_fields = ['title', 'description', 'deadline']
    if not all(field in data for field in required_fields):
        return jsonify({'message': 'Відсутні обов\'язкові поля'}), 400
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Перевіряємо чи є менеджер власником проєкту
        c.execute("""
            SELECT 1 FROM projects
            WHERE id = ? AND manager_id = ?
        """, (project_id, current_user['id']))
        
        if not c.fetchone():
            return jsonify({'message': 'Ви не маєте прав створювати завдання в цьому проєкті'}), 403
        
        # Створюємо завдання
        c.execute("""
            INSERT INTO tasks (
                project_id, title, description, deadline,
                assigned_to, priority, status
            )
            VALUES (?, ?, ?, ?, ?, ?, 'not_started')
        """, (
            project_id, data['title'], data['description'],
            data['deadline'], data.get('assigned_to'),
            data.get('priority', 'medium')
        ))
        
        task_id = c.lastrowid
        
        # Якщо завдання призначено конкретному спеціалісту
        if data.get('assigned_to'):
            create_notification(
                data['assigned_to'],
                project_id,
                'task_assigned',
                f"Вам призначено нове завдання: {data['title']}"
            )
        else:
            # Сповіщаємо всіх учасників проєкту з роллю спеціаліст
            c.execute("""
                SELECT user_id FROM project_members
                WHERE project_id = ? AND role = 'specialist'
            """, (project_id,))
            
            for member in c.fetchall():
                create_notification(
                    member['user_id'],
                    project_id,
                    'new_task',
                    f"Додано нове завдання до проєкту: {data['title']}"
                )
        
        # Логуємо створення завдання
        log_activity(
            current_user['id'],
            project_id,
            'task_created',
            f"Створено завдання: {data['title']}"
        )
        
        conn.commit()
        return jsonify({
            'message': 'Завдання успішно створено',
            'task_id': task_id
        }), 201
        
    except Exception as e:
        logger.error(f"Помилка створення завдання: {str(e)}")
        return jsonify({'message': 'Помилка створення завдання'}), 500
    finally:
        conn.close()


@app.route('/projects/<int:project_id>/ratings', methods=['GET'])
@token_required
def get_ratings(current_user, project_id):
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Перевіряємо права доступу
        if current_user['role'] == 'specialist':
            # Спеціаліст бачить тільки свої оцінки
            c.execute("""
                SELECT r.*, u.name as specialist_name, m.name as manager_name
                FROM ratings r
                JOIN users u ON r.specialist_id = u.id
                JOIN users m ON r.manager_id = m.id
                WHERE r.project_id = ? AND r.specialist_id = ?
            """, (project_id, current_user['id']))
        else:
            # Менеджер та адмін бачать всі оцінки
            c.execute("""
                SELECT r.*, u.name as specialist_name, m.name as manager_name
                FROM ratings r
                JOIN users u ON r.specialist_id = u.id
                JOIN users m ON r.manager_id = m.id
                WHERE r.project_id = ?
            """, (project_id,))
        
        ratings = [{
            'id': row['id'],
            'specialist_id': row['specialist_id'],
            'specialist_name': row['specialist_name'],
            'rating': row['rating'],
            'comment': row['comment'],
            'manager_name': row['manager_name'],
            'timestamp': row['timestamp'],
            'type': row['type']
        } for row in c.fetchall()]
        
        return jsonify(ratings)
    
    except Exception as e:
        logger.error(f"Помилка отримання оцінок: {str(e)}")
        return jsonify({'message': 'Помилка отримання оцінок'}), 500
    finally:
        conn.close()

@app.route('/projects/<int:project_id>/ratings', methods=['POST'])
@token_required
def add_rating(current_user, project_id):
    if current_user['role'] != 'manager':
        return jsonify({'message': 'Тільки менеджери можуть додавати оцінки'}), 403
    
    data = request.get_json()
    if not all(k in data for k in ['specialist_id', 'rating']):
        return jsonify({'message': 'Відсутні обов\'язкові поля'}), 400
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Перевіряємо, чи є спеціаліст учасником проєкту
        c.execute("""
            SELECT 1 FROM project_members 
            WHERE project_id = ? AND user_id = ? AND role = 'specialist'
        """, (project_id, data['specialist_id']))
        
        if not c.fetchone():
            return jsonify({'message': 'Спеціаліст не є учасником цього проєкту'}), 400
        
        # Додаємо або оновлюємо оцінку
        c.execute("""
            INSERT OR REPLACE INTO ratings (
                project_id, specialist_id, rating, comment,
                manager_id, timestamp, type
            )
            VALUES (?, ?, ?, ?, ?, ?, 'final')
        """, (
            project_id,
            data['specialist_id'],
            data['rating'],
            data.get('comment', ''),
            current_user['id'],
            datetime.now(timezone.utc)
        ))
        
        conn.commit()
        return jsonify({'message': 'Оцінку успішно додано'})
    
    except Exception as e:
        logger.error(f"Помилка додавання оцінки: {str(e)}")
        return jsonify({'message': 'Помилка додавання оцінки'}), 500
    
    finally:
        conn.close()


@app.route('/projects/<int:project_id>/tasks/<int:task_id>', methods=['PUT'])
@token_required
def update_task(current_user, project_id, task_id):
    data = request.get_json()
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Перевіряємо існування завдання
        c.execute("""
            SELECT t.*, p.manager_id
            FROM tasks t
            JOIN projects p ON t.project_id = p.id
            WHERE t.id = ? AND t.project_id = ?
        """, (task_id, project_id))
        
        task = c.fetchone()
        if not task:
            return jsonify({'message': 'Завдання не знайдено'}), 404
        
        # Перевіряємо права на редагування
        if current_user['role'] == 'manager' and task['manager_id'] != current_user['id']:
            return jsonify({'message': 'Недостатньо прав для оновлення цього завдання'}), 403
        
        # Оновлюємо завдання
        update_fields = []
        params = []
        
        if 'title' in data and current_user['role'] == 'manager':
            update_fields.append('title = ?')
            params.append(data['title'])
        
        if 'description' in data and current_user['role'] == 'manager':
            update_fields.append('description = ?')
            params.append(data['description'])
        
        if 'status' in data:
            update_fields.append('status = ?')
            params.append(data['status'])
        
        if 'assigned_to' in data and current_user['role'] == 'manager':
            update_fields.append('assigned_to = ?')
            params.append(data['assigned_to'])
        
        if 'priority' in data and current_user['role'] == 'manager':
            update_fields.append('priority = ?')
            params.append(data['priority'])
        
        if update_fields:
            params.extend([task_id, project_id])
            query = f"""
                UPDATE tasks
                SET {', '.join(update_fields)}
                WHERE id = ? AND project_id = ?
            """
            c.execute(query, params)
            
            # Створюємо сповіщення про оновлення
            create_notification(
                task['assigned_to'] if task['assigned_to'] else None,
                project_id,
                'task_updated',
                f"Завдання '{task['title']}' було оновлено"
            )
            
            # Логуємо зміни
            log_activity(
                current_user['id'],
                project_id,
                'task_updated',
                f"Оновлено завдання: {task['title']}"
            )
        
        conn.commit()
        return jsonify({'message': 'Завдання успішно оновлено'})
    
    except Exception as e:
        logger.error(f"Помилка оновлення завдання: {str(e)}")
        return jsonify({'message': 'Помилка оновлення завдання'}), 500
    finally:
        conn.close()

@app.route('/projects/<int:project_id>/files', methods=['POST'])
@token_required
def upload_file(current_user, project_id):
    if 'file' not in request.files:
        return jsonify({'message': 'No file part'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'message': 'No selected file'}), 400
    
    if not allowed_file(file.filename):
        return jsonify({'message': 'File type not allowed'}), 400
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Перевіряємо права доступу до проекту
        c.execute("""
            SELECT 1 FROM project_members
            WHERE project_id = ? AND user_id = ?
        """, (project_id, current_user['id']))
        
        if not c.fetchone() and current_user['role'] != 'admin':
            return jsonify({'message': 'Not a member of this project'}), 403
        
        # Створюємо директорію для файлів проекту
        project_dir = os.path.join(app.config['UPLOAD_FOLDER'], f'project_{project_id}')
        os.makedirs(project_dir, exist_ok=True)
        
        # Зберігаємо файл
        filename = secure_filename(file.filename)
        file_path = os.path.join(project_dir, filename)
        file.save(file_path)
        
        # Зберігаємо інформацію про файл в базі даних
        file_size = os.path.getsize(file_path)
        file_type = os.path.splitext(filename)[1]
        
        c.execute("""
            INSERT INTO files (
                project_id, user_id, filename,
                file_size, file_type, file_path
            )
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            project_id, current_user['id'], filename,
            file_size, file_type, file_path
        ))
        
        # Створюємо сповіщення про новий файл
        c.execute("""
            SELECT user_id FROM project_members
            WHERE project_id = ? AND user_id != ?
        """, (project_id, current_user['id']))
        
        for member in c.fetchall():
            create_notification(
                member['user_id'],
                project_id,
                'new_file',
                f"New file uploaded: {filename}"
            )
        
        # Логуємо завантаження файлу
        log_activity(
            current_user['id'],
            project_id,
            'file_uploaded',
            f"Uploaded file: {filename}"
        )
        
        conn.commit()
        return jsonify({'message': 'File uploaded successfully'})
    
    except Exception as e:
        logger.error(f"Error uploading file: {str(e)}")
        return jsonify({'message': 'Error uploading file'}), 500
    finally:
        conn.close()

@app.route('/files/<int:file_id>/download', methods=['GET'])
@token_required
def download_file(current_user, file_id):
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Отримуємо інформацію про файл
        c.execute("""
            SELECT f.*, p.id as project_id
            FROM files f
            JOIN projects p ON f.project_id = p.id
            WHERE f.id = ?
        """, (file_id,))
        
        file_info = c.fetchone()
        if not file_info:
            return jsonify({'message': 'File not found'}), 404
        
        # Перевіряємо права доступу
        if current_user['role'] != 'admin':
            c.execute("""
                SELECT 1 FROM project_members
                WHERE project_id = ? AND user_id = ?
            """, (file_info['project_id'], current_user['id']))
            
            if not c.fetchone():
                return jsonify({'message': 'Not authorized to download this file'}), 403
        
        # Логуємо завантаження
        log_activity(
            current_user['id'],
            file_info['project_id'],
            'file_downloaded',
            f"Downloaded file: {file_info['filename']}"
        )
        
        return send_file(
            file_info['file_path'],
            as_attachment=True,
            download_name=file_info['filename']
        )
    
    except Exception as e:
        logger.error(f"Error downloading file: {str(e)}")
        return jsonify({'message': 'Error downloading file'}), 500
    finally:
        conn.close()

@app.route('/projects/<int:project_id>/statistics', methods=['GET'])
@token_required
def get_project_statistics(current_user, project_id):
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Базова інформація про проект
        c.execute("""
            SELECT p.*, 
                   COUNT(DISTINCT pm.user_id) as members_count,
                   COUNT(DISTINCT t.id) as total_tasks,
                   COUNT(DISTINCT CASE WHEN t.status = 'completed' THEN t.id END) as completed_tasks,
                   AVG(r.rating) as average_rating
            FROM projects p
            LEFT JOIN project_members pm ON p.id = pm.project_id
            LEFT JOIN tasks t ON p.id = t.project_id
            LEFT JOIN ratings r ON p.id = r.project_id
            WHERE p.id = ?
            GROUP BY p.id
        """, (project_id,))
        
        project_stats = c.fetchone()
        if not project_stats:
            return jsonify({'message': 'Проєкт не знайдено'}), 404
        
        # Прогрес за останній місяць
        c.execute("""
            SELECT DATE(created_at) as date,
                   COUNT(CASE WHEN status = 'completed' THEN 1 END) * 100.0 / COUNT(*) as completion_rate
            FROM tasks
            WHERE project_id = ?
            AND created_at >= date('now', '-30 days')
            GROUP BY DATE(created_at)
            ORDER BY date
        """, (project_id,))
        
        progress_history = [{
            'date': row['date'],
            'completion_rate': row['completion_rate']
        } for row in c.fetchall()]
        
        # Статистика по учасниках
        c.execute("""
            SELECT u.name,
                   COUNT(DISTINCT t.id) as assigned_tasks,
                   COUNT(DISTINCT CASE WHEN t.status = 'completed' THEN t.id END) as completed_tasks,
                   r.rating as current_rating
            FROM project_members pm
            JOIN users u ON pm.user_id = u.id
            LEFT JOIN tasks t ON t.assigned_to = u.id AND t.project_id = pm.project_id
            LEFT JOIN ratings r ON r.specialist_id = u.id AND r.project_id = pm.project_id
            WHERE pm.project_id = ? AND pm.role = 'specialist'
            GROUP BY u.id
        """, (project_id,))
        
        members_stats = [{
            'name': row['name'],
            'assigned_tasks': row['assigned_tasks'],
            'completed_tasks': row['completed_tasks'],
            'current_rating': row['current_rating']
        } for row in c.fetchall()]
        
        statistics = {
            'basic_info': {
                'members_count': project_stats['members_count'],
                'total_tasks': project_stats['total_tasks'],
                'completed_tasks': project_stats['completed_tasks'],
                'average_rating': float(project_stats['average_rating']) if project_stats['average_rating'] else None
            },
            'progress_history': progress_history,
            'members_statistics': members_stats
        }
        
        return jsonify(statistics)
    
    except Exception as e:
        logger.error(f"Помилка отримання статистики проєкту: {str(e)}")
        return jsonify({'message': 'Помилка отримання статистики проєкту'}), 500
    finally:
        conn.close()

@app.route('/projects/<int:project_id>/activity', methods=['GET'])
@token_required
def get_project_activity(current_user, project_id):
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Отримуємо останні дії в проекті
        c.execute("""
            SELECT ua.*, u.name as user_name
            FROM user_activity ua
            JOIN users u ON ua.user_id = u.id
            WHERE ua.project_id = ?
            ORDER BY ua.timestamp DESC
            LIMIT 50
        """, (project_id,))
        
        activities = [{
            'id': row['id'],
            'user_name': row['user_name'],
            'action_type': row['action_type'],
            'action_details': row['action_details'],
            'timestamp': row['timestamp']
        } for row in c.fetchall()]
        
        return jsonify(activities)
    
    except Exception as e:
        logger.error(f"Error getting project activity: {str(e)}")
        return jsonify({'message': 'Error getting project activity'}), 500
    finally:
        conn.close()

@app.route('/users/<int:user_id>', methods=['DELETE'])
@token_required
def delete_user(current_user, user_id):
    if current_user['role'] != 'admin':
        return jsonify({'message': 'Unauthorized'}), 403
    
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Проверяем существование пользователя
        c.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        user = c.fetchone()
        if not user:
            return jsonify({'message': 'User not found'}), 404
        
        # Удаляем связанные данные
        c.execute("DELETE FROM project_members WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM tasks WHERE assigned_to = ?", (user_id,))
        c.execute("DELETE FROM comments WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM grades WHERE student_id = ? OR teacher_id = ?", (user_id, user_id))
        c.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
        c.execute("DELETE FROM user_activity WHERE user_id = ?", (user_id,))
        
        # Удаляем самого пользователя
        c.execute("DELETE FROM users WHERE id = ?", (user_id,))
        
        conn.commit()
        return jsonify({'message': 'User deleted successfully'})
        
    except Exception as e:
        logger.error(f"Error deleting user: {str(e)}")
        return jsonify({'message': 'Error deleting user'}), 500
    finally:
        conn.close()

@app.route('/users/<int:user_id>/statistics', methods=['GET'])
@token_required
def get_user_statistics(current_user, user_id):
    # Перевіряємо права доступу
    if current_user['id'] != user_id and current_user['role'] not in ['teacher', 'admin']:
        return jsonify({'message': 'Unauthorized'}), 403
        
    try:
        conn = get_db()
        c = conn.cursor()
        
        # Загальна статистика
        c.execute("""
            SELECT 
                COUNT(DISTINCT pm.project_id) as total_projects,
                COUNT(DISTINCT t.id) as total_tasks,
                COUNT(DISTINCT CASE WHEN t.status = 'completed' THEN t.id END) as completed_tasks,
                AVG(g.grade) as average_grade
            FROM users u
            LEFT JOIN project_members pm ON u.id = pm.user_id
            LEFT JOIN tasks t ON u.id = t.assigned_to
            LEFT JOIN grades g ON u.id = g.student_id
            WHERE u.id = ?
        """, (user_id,))
        
        stats = c.fetchone()
        
        # Активні проекти
        c.execute("""
            SELECT p.name, 
                   p.deadline,
                   COUNT(t.id) as tasks_count,
                   COUNT(CASE WHEN t.status = 'completed' THEN 1 END) as completed_tasks,
                   g.grade
            FROM project_members pm
            JOIN projects p ON pm.project_id = p.id
            LEFT JOIN tasks t ON t.project_id = p.id AND t.assigned_to = pm.user_id
            LEFT JOIN grades g ON g.project_id = p.id AND g.student_id = pm.user_id
            WHERE pm.user_id = ? AND p.status = 'active'
            GROUP BY p.id
        """, (user_id,))
        
        active_projects = [{
            'name': row['name'],
            'deadline': row['deadline'],
            'tasks_count': row['tasks_count'],
            'completed_tasks': row['completed_tasks'],
            'grade': row['grade']
        } for row in c.fetchall()]
        
        # Останні дії
        c.execute("""
            SELECT action_type, action_details, timestamp
            FROM user_activity
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT 10
        """, (user_id,))
        
        recent_activity = [{
            'action_type': row['action_type'],
            'action_details': row['action_details'],
            'timestamp': row['timestamp']
        } for row in c.fetchall()]
        
        statistics = {
            'overview': {
                'total_projects': stats['total_projects'],
                'total_tasks': stats['total_tasks'],
                'completed_tasks': stats['completed_tasks'],
                'average_grade': float(stats['average_grade']) if stats['average_grade'] else None
            },
            'active_projects': active_projects,
            'recent_activity': recent_activity
        }
        
        return jsonify(statistics)
    
    except Exception as e:
        logger.error(f"Error getting user statistics: {str(e)}")
        return jsonify({'message': 'Error getting user statistics'}), 500
    finally:
        conn.close()

@app.errorhandler(404)
def not_found_error(error):
    return jsonify({'message': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'message': 'Internal server error'}), 500

# Ініціалізація при запуску
if __name__ == '__main__':
    with app.app_context():
        init_db()
    app.run(debug=True)