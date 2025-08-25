#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sqlite3
import datetime
import random
from werkzeug.security import generate_password_hash
import os
import logging
from faker import Faker
import uuid

# Налаштування логування
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Ініціалізація Faker для генерації реалістичних даних
fake = Faker('uk_UA')  # Використовуємо українську локаль

# Шлях до бази даних
DB_PATH = 'project_management.db'

# Створення директорії для файлів
UPLOAD_DIR = 'files'
if not os.path.exists(UPLOAD_DIR):
    os.makedirs(UPLOAD_DIR)
    logger.info(f"Створено директорію {UPLOAD_DIR}")

def get_db_connection():
    """Отримання з'єднання з базою даних"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def clear_database():
    """Очищення бази даних перед заповненням"""
    logger.info("Очищення бази даних...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Список таблиць для очищення
    tables = [
        'notifications', 'user_activity', 'files',
        'comments', 'tasks', 'calendar_events',
        'ratings', 'project_members', 'projects',
        'users'
    ]
    
    # Відключення перевірки зовнішніх ключів
    cursor.execute('PRAGMA foreign_keys = OFF')
    
    # Видалення даних з таблиць
    for table in tables:
        try:
            cursor.execute(f'DELETE FROM {table}')
            logger.info(f"Очищено таблицю {table}")
        except sqlite3.Error as e:
            logger.warning(f"Помилка при очищенні таблиці {table}: {e}")
    
    # Скидання лічильників автоінкременту
    for table in tables:
        try:
            cursor.execute(f'DELETE FROM sqlite_sequence WHERE name="{table}"')
        except sqlite3.Error:
            pass
    
    # Включення перевірки зовнішніх ключів
    cursor.execute('PRAGMA foreign_keys = ON')
    
    conn.commit()
    conn.close()
    logger.info("База даних очищена")

def create_users():
    """Створення користувачів: адміністратор, менеджери та спеціалісти"""
    logger.info("Створення користувачів...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Створення адміністратора
    admin_password = generate_password_hash('admin123', method='scrypt')
    cursor.execute(
        'INSERT INTO users (name, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)',
        ('Адміністратор', 'admin@example.com', admin_password, 'admin', datetime.datetime.now())
    )
    logger.info("Адміністратор створений")
    
    # Створення менеджерів (3)
    managers = []
    for i in range(3):
        name = fake.name()
        email = f"manager{i+1}@example.com"
        password = generate_password_hash(f'manager{i+1}', method='scrypt')
        
        cursor.execute(
            'INSERT INTO users (name, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)',
            (name, email, password, 'manager', datetime.datetime.now())
        )
        manager_id = cursor.lastrowid
        managers.append({
            'id': manager_id,
            'name': name,
            'email': email
        })
    
    logger.info(f"Створено {len(managers)} менеджерів")
    
    # Створення спеціалістів (10)
    specialists = []
    for i in range(10):
        name = fake.name()
        email = f"specialist{i+1}@example.com"
        password = generate_password_hash(f'specialist{i+1}', method='scrypt')
        
        cursor.execute(
            'INSERT INTO users (name, email, password, role, created_at) VALUES (?, ?, ?, ?, ?)',
            (name, email, password, 'specialist', datetime.datetime.now())
        )
        specialist_id = cursor.lastrowid
        specialists.append({
            'id': specialist_id,
            'name': name,
            'email': email
        })
    
    logger.info(f"Створено {len(specialists)} спеціалістів")
    
    conn.commit()
    conn.close()
    
    return {
        'managers': managers,
        'specialists': specialists
    }

def create_projects(users):
    """Створення проєктів"""
    logger.info("Створення проєктів...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    managers = users['managers']
    specialists = users['specialists']
    
    # Типові статуси проєктів
    statuses = ['active', 'completed', 'archived']
    
    # Створення 20 проєктів
    projects = []
    for i in range(20):
        # Вибір випадкового менеджера
        manager = random.choice(managers)
        
        # Генерація даних проєкту
        name = fake.catch_phrase()
        description = fake.paragraph(nb_sentences=5)
        status = random.choices(statuses, weights=[0.7, 0.2, 0.1])[0]
        
        # Генерація дати дедлайну (від 1 до 6 місяців від сьогодні)
        deadline = datetime.datetime.now() + datetime.timedelta(days=random.randint(30, 180))
        
        # Максимальна кількість спеціалістів (від 3 до 7)
        max_specialists = random.randint(3, 7)
        
        # Вставка проєкту
        cursor.execute(
            '''INSERT INTO projects 
               (name, description, manager_id, deadline, max_specialists, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)''',
            (name, description, manager['id'], deadline.strftime('%Y-%m-%d'), 
             max_specialists, status, datetime.datetime.now())
        )
        project_id = cursor.lastrowid
        
        # Додавання менеджера як учасника проєкту
        cursor.execute(
            '''INSERT INTO project_members 
               (project_id, user_id, role, join_date)
               VALUES (?, ?, ?, ?)''',
            (project_id, manager['id'], 'manager', datetime.datetime.now())
        )
        
        # Визначення кількості спеціалістів для проєкту (від 0 до max_specialists)
        num_specialists = random.randint(0, min(max_specialists, len(specialists)))
        
        # Випадкові спеціалісти для цього проєкту
        project_specialists = random.sample(specialists, num_specialists)
        
        # Додавання спеціалістів до проєкту
        for specialist in project_specialists:
            cursor.execute(
                '''INSERT INTO project_members 
                   (project_id, user_id, role, join_date)
                   VALUES (?, ?, ?, ?)''',
                (project_id, specialist['id'], 'specialist', 
                 (datetime.datetime.now() - datetime.timedelta(days=random.randint(1, 30))))
            )
        
        # Зберігання інформації про проєкт
        projects.append({
            'id': project_id,
            'name': name,
            'manager_id': manager['id'],
            'status': status,
            'specialists': [s['id'] for s in project_specialists]
        })
    
    logger.info(f"Створено {len(projects)} проєктів")
    
    conn.commit()
    conn.close()
    
    return projects

def create_tasks(projects, users):
    """Створення завдань для проєктів"""
    logger.info("Створення завдань...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Статуси завдань
    task_statuses = ['not_started', 'in_progress', 'completed']
    
    # Пріоритети завдань
    priorities = ['low', 'medium', 'high']
    
    # Лічильник створених завдань
    task_count = 0
    
    for project in projects:
        # Генеруємо випадкову кількість завдань для проєкту (від 0 до 5)
        num_tasks = random.randint(0, 5)
        
        # Якщо проєкт неактивний, менше завдань
        if project['status'] != 'active':
            num_tasks = min(num_tasks, 2)
        
        # Спеціалісти в цьому проєкті
        project_specialists = project['specialists']
        
        for i in range(num_tasks):
            # Генерація даних завдання
            title = fake.sentence(nb_words=6)
            description = fake.paragraph(nb_sentences=3)
            
            # Випадковий статус, з перевагою для 'in_progress' для активних проєктів
            if project['status'] == 'active':
                status = random.choices(task_statuses, weights=[0.3, 0.5, 0.2])[0]
            else:
                status = random.choices(task_statuses, weights=[0.1, 0.2, 0.7])[0]
            
            # Дедлайн завдання
            task_deadline = datetime.datetime.now() + datetime.timedelta(days=random.randint(7, 60))
            
            # Випадковий пріоритет
            priority = random.choice(priorities)
            
            # Призначення завдання випадковому спеціалісту з проєкту (якщо такі є)
            assigned_to = None
            if project_specialists:
                assigned_to = random.choice(project_specialists)
            
            # Вставка завдання
            cursor.execute(
                '''INSERT INTO tasks 
                   (project_id, title, description, status, created_at, 
                    deadline, assigned_to, priority)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (project['id'], title, description, status, 
                 datetime.datetime.now(), task_deadline.strftime('%Y-%m-%d'), 
                 assigned_to, priority)
            )
            
            task_count += 1
    
    logger.info(f"Створено {task_count} завдань")
    conn.commit()
    conn.close()

def create_calendar_events(projects):
    """Створення подій календаря для проєктів"""
    logger.info("Створення подій календаря...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Типи подій
    event_types = ['meeting', 'deadline', 'other']
    
    # Лічильник створених подій
    event_count = 0
    
    for project in projects:
        # Тільки для активних проєктів
        if project['status'] != 'active':
            continue
        
        # Генеруємо випадкову кількість подій (від 1 до 3)
        num_events = random.randint(1, 3)
        
        for i in range(num_events):
            # Генерація даних події
            title = fake.sentence(nb_words=4)
            description = fake.paragraph(nb_sentences=2)
            event_type = random.choice(event_types)
            
            # Дата початку (від сьогодні до 30 днів у майбутньому)
            start_date = datetime.datetime.now() + datetime.timedelta(days=random.randint(1, 30))
            
            # Тривалість події (від 30 хвилин до 3 годин)
            duration = datetime.timedelta(minutes=random.randint(30, 180))
            
            # Дата закінчення
            end_date = start_date + duration
            
            # Вставка події
            cursor.execute(
                '''INSERT INTO calendar_events 
                   (project_id, title, description, event_type, 
                    start_time, end_time, created_by)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (project['id'], title, description, event_type, 
                 start_date.strftime('%Y-%m-%d %H:%M:%S'), 
                 end_date.strftime('%Y-%m-%d %H:%M:%S'), 
                 project['manager_id'])
            )
            
            event_count += 1
    
    logger.info(f"Створено {event_count} подій календаря")
    conn.commit()
    conn.close()

def create_comments(projects, users):
    """Створення коментарів для проєктів"""
    logger.info("Створення коментарів...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Лічильник створених коментарів
    comment_count = 0
    
    for project in projects:
        # Генеруємо випадкову кількість коментарів (від 0 до 8)
        num_comments = random.randint(0, 8)
        
        # Учасники проєкту (включаючи менеджера)
        participants = [project['manager_id']] + project['specialists']
        if not participants:
            continue
            
        # Дати для впорядкування коментарів
        base_date = datetime.datetime.now() - datetime.timedelta(days=random.randint(10, 30))
        
        for i in range(num_comments):
            # Випадковий автор коментаря
            author_id = random.choice(participants)
            
            # Генерація тексту коментаря
            content = fake.paragraph(nb_sentences=random.randint(1, 3))
            
            # Дата коментаря (хронологічно)
            comment_date = base_date + datetime.timedelta(hours=i*random.randint(1, 5))
            
            # Вставка коментаря
            cursor.execute(
                '''INSERT INTO comments 
                   (project_id, user_id, content, timestamp)
                   VALUES (?, ?, ?, ?)''',
                (project['id'], author_id, content, comment_date.strftime('%Y-%m-%d %H:%M:%S'))
            )
            
            comment_count += 1
    
    logger.info(f"Створено {comment_count} коментарів")
    conn.commit()
    conn.close()

def create_ratings(projects, users):
    """Створення оцінок виконання для проєктів"""
    logger.info("Створення оцінок виконання...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Лічильник створених оцінок
    rating_count = 0
    
    for project in projects:
        # Тільки для проєктів з статусом "completed" чи для деяких активних
        if project['status'] != 'completed' and random.random() > 0.3:
            continue
        
        # Спеціалісти в проєкті
        project_specialists = project['specialists']
        
        # Оцінюємо кожного спеціаліста
        for specialist_id in project_specialists:
            # Генерація оцінки (від 60 до 100)
            rating_value = round(random.uniform(60, 100), 1)
            
            # Генерація коментаря до оцінки
            comment = fake.sentence(nb_words=random.randint(5, 15))
            
            # Дата оцінювання
            rating_date = datetime.datetime.now() - datetime.timedelta(days=random.randint(1, 14))
            
            # Вставка оцінки
            cursor.execute(
                '''INSERT INTO ratings 
                   (project_id, specialist_id, rating, comment, 
                    manager_id, timestamp, type)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (project['id'], specialist_id, rating_value, comment, 
                 project['manager_id'], rating_date.strftime('%Y-%m-%d %H:%M:%S'), 
                 'final')
            )
            
            rating_count += 1
    
    logger.info(f"Створено {rating_count} оцінок виконання")
    conn.commit()
    conn.close()

def create_notifications(projects, users):
    """Створення сповіщень для користувачів"""
    logger.info("Створення сповіщень...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Типи сповіщень
    notification_types = [
        'task_assigned', 'task_completed', 'new_comment', 
        'new_member', 'project_update', 'deadline_approaching'
    ]
    
    # Пріоритети сповіщень
    priorities = ['low', 'normal', 'high']
    
    # Лічильник створених сповіщень
    notification_count = 0
    
    # Для кожного користувача створюємо кілька сповіщень
    all_users = []
    for manager in users['managers']:
        all_users.append(manager['id'])
    for specialist in users['specialists']:
        all_users.append(specialist['id'])
    
    for user_id in all_users:
        # Випадкова кількість сповіщень для користувача (від 0 до 5)
        num_notifications = random.randint(0, 5)
        
        for i in range(num_notifications):
            # Випадковий проєкт
            project = random.choice(projects)
            
            # Випадковий тип сповіщення
            notification_type = random.choice(notification_types)
            
            # Генерація тексту сповіщення
            message = fake.sentence(nb_words=random.randint(5, 10))
            
            # Випадковий пріоритет
            priority = random.choice(priorities)
            
            # Дата створення (останні 7 днів)
            created_at = datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 7))
            
            # Дата закінчення (від 7 до 30 днів у майбутньому)
            expiry_date = datetime.datetime.now() + datetime.timedelta(days=random.randint(7, 30))
            
            # Статус прочитання (більшість непрочитані)
            is_read = random.choices([0, 1], weights=[0.7, 0.3])[0]
            
            # Вставка сповіщення
            cursor.execute(
                '''INSERT INTO notifications 
                   (user_id, project_id, type, message, created_at, 
                    is_read, priority, expiry_date)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
                (user_id, project['id'], notification_type, message, 
                 created_at.strftime('%Y-%m-%d %H:%M:%S'), 
                 is_read, priority, expiry_date.strftime('%Y-%m-%d %H:%M:%S'))
            )
            
            notification_count += 1
    
    logger.info(f"Створено {notification_count} сповіщень")
    conn.commit()
    conn.close()

def create_files(projects, users):
    """Створення файлів для проєктів"""
    logger.info("Створення файлів...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Типи файлів
    file_types = ['.pdf', '.doc', '.xlsx', '.png', '.jpg', '.txt']
    
    # Лічильник створених файлів
    file_count = 0
    
    for project in projects:
        # Створюємо директорію для файлів проєкту
        project_dir = os.path.join(UPLOAD_DIR, f'project_{project["id"]}')
        os.makedirs(project_dir, exist_ok=True)
        
        # Випадкова кількість файлів (від 0 до 3)
        num_files = random.randint(0, 3)
        
        # Учасники проєкту
        participants = [project['manager_id']] + project['specialists']
        if not participants:
            continue
            
        for i in range(num_files):
            # Випадковий автор файлу
            author_id = random.choice(participants)
            
            # Генерація імені файлу
            file_type = random.choice(file_types)
            filename = fake.word() + "_" + str(uuid.uuid4())[:8] + file_type
            
            # Розмір файлу (від 10KB до 5MB)
            file_size = random.randint(10000, 5000000)
            
            # Шлях до файлу
            file_path = os.path.join(project_dir, filename)
            
            # Створення пустого файлу
            with open(file_path, 'wb') as f:
                f.write(b'x' * min(file_size, 100))  # Записуємо тільки початок для економії місця
            
            # Дата завантаження
            upload_date = datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 14))
            
            # Вставка запису про файл
            cursor.execute(
                '''INSERT INTO files 
                   (project_id, user_id, filename, file_size, file_type,
                    upload_date, file_path)
                   VALUES (?, ?, ?, ?, ?, ?, ?)''',
                (project['id'], author_id, filename, file_size, file_type,
                 upload_date.strftime('%Y-%m-%d %H:%M:%S'), file_path)
            )
            
            file_count += 1
    
    logger.info(f"Створено {file_count} файлів")
    conn.commit()
    conn.close()

def create_activity_logs(projects, users):
    """Створення логів активності"""
    logger.info("Створення логів активності...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Типи активності
    activity_types = [
        'login', 'file_upload', 'comment_added', 'task_created',
        'task_updated', 'project_joined', 'rating_given'
    ]
    
    # Лічильник створених логів
    log_count = 0
    
    # Для кожного користувача створюємо записи активності
    all_users = []
    for manager in users['managers']:
        all_users.append(manager['id'])
    for specialist in users['specialists']:
        all_users.append(specialist['id'])
    
    for user_id in all_users:
        # Випадкова кількість записів активності (від 3 до 15)
        num_logs = random.randint(3, 15)
        
        for i in range(num_logs):
            # Випадковий тип активності
            activity_type = random.choice(activity_types)
            
            # Детальна інформація про активність
            action_details = fake.sentence(nb_words=random.randint(3, 8))
            
            # Випадковий проєкт (або None для деяких типів активності)
            project_id = None
            if activity_type != 'login' and random.random() > 0.2:
                project = random.choice(projects)
                project_id = project['id']
            
            # Дата активності (останні 30 днів)
            timestamp = datetime.datetime.now() - datetime.timedelta(days=random.randint(0, 30), 
                                                                 hours=random.randint(0, 23),
                                                                 minutes=random.randint(0, 59))
            
            # Вставка запису активності
            cursor.execute(
                '''INSERT INTO user_activity 
                   (user_id, project_id, action_type, action_details, timestamp)
                   VALUES (?, ?, ?, ?, ?)''',
                (user_id, project_id, activity_type, action_details, 
                 timestamp.strftime('%Y-%m-%d %H:%M:%S'))
            )
            
            log_count += 1
    
    logger.info(f"Створено {log_count} записів активності")
    conn.commit()
    conn.close()

def main():
    """Головна функція для заповнення бази даних"""
    logger.info("Початок заповнення бази даних...")
    
    # Очищення бази даних
    clear_database()
    
    # Створення користувачів
    users = create_users()
    
    # Створення проєктів
    projects = create_projects(users)
    
    # Створення завдань
    create_tasks(projects, users)
    
    # Створення подій календаря
    create_calendar_events(projects)
    
    # Створення коментарів
    create_comments(projects, users)
    
    # Створення оцінок
    create_ratings(projects, users)
    
    # Створення сповіщень
    create_notifications(projects, users)
    
    # Створення файлів
    create_files(projects, users)
    
    # Створення логів активності
    create_activity_logs(projects, users)
    
    logger.info("Заповнення бази даних завершено")
    logger.info("\nОблікові дані для входу:")
    logger.info("Адміністратор: admin@example.com / admin123")
    
    for i, manager in enumerate(users['managers']):
        logger.info(f"Менеджер {i+1}: {manager['email']} / manager{i+1}")
    
    for i, specialist in enumerate(users['specialists']):
        logger.info(f"Спеціаліст {i+1}: {specialist['email']} / specialist{i+1}")

if __name__ == "__main__":
    main()