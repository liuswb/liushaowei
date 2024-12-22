import sqlite3
from datetime import datetime
import threading
import bcrypt

class Database:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(Database, cls).__new__(cls)
                    cls._instance.local = threading.local()
        return cls._instance
    
    def __init__(self):
        self._lock.acquire()
        try:
            if not hasattr(self.local, 'initialized'):
                self.local.conn = sqlite3.connect('work_management.db', check_same_thread=False)
                self.local.cursor = self.local.conn.cursor()
                self.local.initialized = True
                self.create_tables()
        finally:
            self._lock.release()
    
    def get_cursor(self):
        if not hasattr(self.local, 'cursor'):
            self.local.conn = sqlite3.connect('work_management.db', check_same_thread=False)
            self.local.cursor = self.local.conn.cursor()
        return self.local.cursor
    
    def get_connection(self):
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect('work_management.db', check_same_thread=False)
            self.local.cursor = self.local.conn.cursor()
        return self.local.conn
    
    def create_tables(self):
        """创建数据库表"""
        try:
            # 检查表是否存在
            self.cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND (
                    name='projects' OR 
                    name='tasks' OR 
                    name='project_history' OR 
                    name='daily_reports' OR
                    name='project_devices' OR
                    name='devices' OR
                    name='users' OR
                    name='permissions' OR
                    name='user_projects'
                )
            ''')
            existing_tables = {table[0] for table in self.cursor.fetchall()}
            
            # 创建设备表（如果不存在）
            if 'devices' not in existing_tables:
                self.cursor.execute('''
                    CREATE TABLE devices (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id INTEGER NOT NULL,
                        device_type TEXT NOT NULL,  -- 设备类型：分流设备/光旁路保护设备/数通设备/电源设备
                        device_name TEXT NOT NULL,  -- 设备名称
                        model TEXT NOT NULL,        -- 设备型号
                        mec_10g INTEGER,           -- 万兆光卡数量（仅分流设备）
                        ge_optical INTEGER,        -- 千兆光卡数量（仅分流设备）
                        electrical INTEGER,        -- 电口卡数量（仅分流设备）
                        card_quantity INTEGER,     -- 业务板卡数量（非分流设备）
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (project_id) REFERENCES projects(id) ON DELETE CASCADE
                    )
                ''')
            
            # 创建任务表（如果不存在）
            if 'tasks' not in existing_tables:
                self.cursor.execute('''
                    CREATE TABLE tasks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id INTEGER,
                        content TEXT NOT NULL,
                        priority INTEGER,
                        start_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        end_time TIMESTAMP,
                        completed BOOLEAN DEFAULT 0,
                        completion_note TEXT,
                        user_id INTEGER,
                        FOREIGN KEY (project_id) REFERENCES projects (id),
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
            else:
                # 检查是否需要添加新列
                self.cursor.execute('PRAGMA table_info(tasks)')
                columns = {col[1] for col in self.cursor.fetchall()}
                if 'user_id' not in columns:
                    self.cursor.execute('ALTER TABLE tasks ADD COLUMN user_id INTEGER REFERENCES users(id)')
                if 'completion_note' not in columns:
                    self.cursor.execute('ALTER TABLE tasks ADD COLUMN completion_note TEXT')
            
            # 创建项目表（如果不存在）
            if 'projects' not in existing_tables:
                self.cursor.execute('''
                    CREATE TABLE projects (
                        id INTEGER PRIMARY KEY,
                        client_name TEXT NOT NULL,
                        stage TEXT,
                        status TEXT,
                        created_at TIMESTAMP,
                        last_updated TIMESTAMP,
                        notes TEXT,
                        state TEXT,
                        is_active INTEGER,
                        area TEXT,
                        manager TEXT,
                        manager_phone TEXT
                    )
                ''')
            else:
                # 检查是否需要添加新列
                self.cursor.execute('PRAGMA table_info(projects)')
                columns = {col[1] for col in self.cursor.fetchall()}
                if 'area' not in columns:
                    self.cursor.execute('ALTER TABLE projects ADD COLUMN area TEXT')
                if 'manager' not in columns:
                    self.cursor.execute('ALTER TABLE projects ADD COLUMN manager TEXT')
                if 'manager_phone' not in columns:
                    self.cursor.execute('ALTER TABLE projects ADD COLUMN manager_phone TEXT')
            
            # 创建项目历史表（如果不存在）
            if 'project_history' not in existing_tables:
                self.cursor.execute('''
                    CREATE TABLE project_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        project_id INTEGER,
                        change_type TEXT,
                        change_time TIMESTAMP,
                        old_value TEXT,
                        new_value TEXT,
                        description TEXT,
                        FOREIGN KEY (project_id) REFERENCES projects (id)
                    )
                ''')
            
            # 创建日报表（如果不存在）
            if 'daily_reports' not in existing_tables:
                self.cursor.execute('''
                    CREATE TABLE daily_reports (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        report_date DATE NOT NULL,
                        content TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        user_id INTEGER NOT NULL,
                        FOREIGN KEY (user_id) REFERENCES users (id)
                    )
                ''')
            else:
                # 检查是否需要添加新列
                self.cursor.execute('PRAGMA table_info(daily_reports)')
                columns = {col[1] for col in self.cursor.fetchall()}
                if 'user_id' not in columns:
                    self.cursor.execute('ALTER TABLE daily_reports ADD COLUMN user_id INTEGER REFERENCES users(id)')
            
            # 创建用户表（如果不存在）
            if 'users' not in existing_tables:
                self.cursor.execute('''
                    CREATE TABLE users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT UNIQUE NOT NULL,
                        password TEXT NOT NULL,
                        role TEXT NOT NULL,  -- 'admin' 或 'user'
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1
                    )
                ''')
                
                # 添加超级管理员账号
                self.cursor.execute('''
                    INSERT INTO users (username, password, role)
                    VALUES (?, ?, ?)
                ''', ('liusw', self.hash_password('LiuShaowei@2020'), 'admin'))
            
            # 创建权限表（如果不存在）
            if 'permissions' not in existing_tables:
                self.cursor.execute('''
                    CREATE TABLE permissions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        module TEXT NOT NULL,  -- 'projects', 'tasks', 'reports'
                        can_view BOOLEAN DEFAULT 0,
                        can_add BOOLEAN DEFAULT 0,
                        can_edit BOOLEAN DEFAULT 0,
                        can_delete BOOLEAN DEFAULT 0,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        UNIQUE(user_id, module)
                    )
                ''')
            
            # 创建用户项目关联表（如果不存在）
            if 'user_projects' not in existing_tables:
                self.cursor.execute('''
                    CREATE TABLE user_projects (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER,
                        project_id INTEGER,
                        FOREIGN KEY (user_id) REFERENCES users (id),
                        FOREIGN KEY (project_id) REFERENCES projects (id),
                        UNIQUE(user_id, project_id)
                    )
                ''')
            
            self.conn.commit()
        except Exception as e:
            print(f"Error creating tables: {e}")
            self.conn.rollback()
            raise
    
    @property
    def conn(self):
        return self.get_connection()
    
    @property
    def cursor(self):
        return self.get_cursor()
    
    def hash_password(self, password):
        """使用 bcrypt 对密码进行加密"""
        return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    
    def verify_password(self, stored_password, provided_password):
        """验证密码"""
        return bcrypt.checkpw(provided_password.encode('utf-8'), stored_password.encode('utf-8'))