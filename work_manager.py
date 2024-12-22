from datetime import datetime, timedelta
from models import Database
import re

class WorkManager:
    def __init__(self):
        self.db = Database()
    
    def add_project(self, project_id, client_name, stage, status, notes, area, manager, manager_phone):
        """添加新项目"""
        try:
            print(f"开始添加项目：ID={project_id}, 客户={client_name}")
            
            # 验证项目ID
            if not isinstance(project_id, int):
                print(f"项目ID类型错误：{type(project_id)}")
                raise ValueError('项目ID必须为整数')
            if project_id <= 0:
                print(f"项目ID值无效：{project_id}")
                raise ValueError('项目ID必须为正整数')

            # 验证必填字段
            if not all([client_name, stage, area, manager, manager_phone]):
                missing = []
                if not client_name: missing.append('客户名称')
                if not stage: missing.append('项目环节')
                if not area: missing.append('项目区域')
                if not manager: missing.append('项��经理')
                if not manager_phone: missing.append('联系电话')
                print(f"缺少必填字段：{', '.join(missing)}")
                raise ValueError(f'以下字段为必填项：{", ".join(missing)}')

            # 检查项目ID是否已存在
            print(f"检查项目ID {project_id} 是否存在")
            existing = self.db.cursor.execute(
                'SELECT id FROM projects WHERE id = ?', 
                (project_id,)
            ).fetchone()
            
            if existing:
                print(f"项目ID {project_id} 已存在")
                raise ValueError('项目ID已存在')
            
            # 添加项目
            print(f"正在将新项目插入数据库")
            self.db.cursor.execute('''
                INSERT INTO projects (
                    id, client_name, stage, status, notes, 
                    created_at, last_updated, state, is_active,
                    area, manager, manager_phone
                )
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'active', 1, ?, ?, ?)
            ''', (
                project_id, client_name, stage, status, notes,
                area, manager, manager_phone
            ))
            
            # 获取所有用户ID
            print("正在为所有用户添加项目访问权限")
            users = self.db.cursor.execute('SELECT id FROM users').fetchall()
            for user in users:
                try:
                    self.db.cursor.execute('''
                        INSERT OR IGNORE INTO user_projects (user_id, project_id)
                        VALUES (?, ?)
                    ''', (user[0], project_id))
                except Exception as e:
                    print(f"为用户 {user[0]} 添加项目访问权限时出错：{e}")
            
            # 添加创建记录
            print("正在添加项目创建历史记录")
            self.add_history_record(
                project_id=project_id,
                change_type='create',
                description=f'创建项目: {client_name}'
            )
            
            self.db.conn.commit()
            print(f"项目 {project_id} 添加成功")
            return True
        except ValueError as e:
            print(f"添加项目时出现 ValueError：{e}")
            self.db.conn.rollback()
            raise
        except Exception as e:
            print(f"添加项目时出现错误：{e}")
            self.db.conn.rollback()
            raise ValueError(f'添加项目时出错：{str(e)}')
    
    def add_task(self, project_id, content, priority, user_id):
        """添加任务"""
        try:
            # 如果是日常工作
            if project_id == 'daily':
                project_id = None
            # 如果是临时任务
            elif project_id == '0':
                project_id = None
            else:
                # 确保project_id是整数
                project_id = int(project_id)
            
            # 转换优先级
            priority_map = {
                'high': 3,
                'medium': 2,
                'low': 1
            }
            priority_value = priority_map.get(priority, 2)  # 默认为中优先级
            
            # 获取当前时间
            current_time = datetime.now()
            
            # 插入任务
            self.db.cursor.execute('''
                INSERT INTO tasks (
                    project_id, content, priority, user_id, 
                    start_time, completed
                )
                VALUES (?, ?, ?, ?, ?, 0)
            ''', (project_id, content, priority_value, user_id, current_time))
            
            # 获取新插入的任务ID
            task_id = self.db.cursor.lastrowid
            
            # 添加到日报
            if project_id:
                project_name = self.db.cursor.execute(
                    'SELECT client_name FROM projects WHERE id = ?', 
                    (project_id,)
                ).fetchone()[0]
                task_record = f"新建任务：{content}\n所属项目：{project_name}\n"
            else:
                task_record = f"新建任务：{content}\n类型：{'日常工作' if project_id == 'daily' else '临时任务'}\n"
            
            self.add_task_to_report(user_id, task_record)
            
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"Error adding task: {e}")
            self.db.conn.rollback()
            return False
    
    def get_projects_by_activity(self):
        active = self.db.cursor.execute('''
            SELECT * FROM projects 
            WHERE state = 'active' AND is_active = 1
            ORDER BY last_updated DESC
        ''').fetchall()
        
        recent_inactive = self.db.cursor.execute('''
            SELECT * FROM projects 
            WHERE state = 'recent_inactive' AND is_active = 1
            ORDER BY last_updated DESC
        ''').fetchall()
        
        long_inactive = self.db.cursor.execute('''
            SELECT * FROM projects 
            WHERE state = 'long_inactive' AND is_active = 1
            ORDER BY last_updated DESC
        ''').fetchall()
        
        return {
            "active_projects": active,
            "recent_inactive": recent_inactive,
            "long_inactive": long_inactive
        }
    
    def get_today_tasks(self):
        return self.db.cursor.execute('''
            SELECT 
                id, project_id, content, priority,
                start_time, end_time, completed
            FROM tasks 
            WHERE DATE(start_time) = DATE('now', 'localtime')
            AND completed = 0
            ORDER BY priority DESC
        ''').fetchall()
    
    def get_next_task_number(self, report_content):
        """获取任务序号"""
        if not report_content:
            return 1
        
        # 查找所有序号（格式如：1. 2. 3.）
        numbers = re.findall(r'(\d+)\. ', report_content)
        if not numbers:
            return 1
        
        # 转换为整数并找出最大值
        max_number = max(map(int, numbers))
        return max_number + 1
    
    def complete_task(self, task_id, completion_note=''):
        """完成任务"""
        try:
            # 获取任务信息
            task = self.db.cursor.execute('''
                SELECT t.content, t.project_id, p.client_name, t.user_id
                FROM tasks t
                LEFT JOIN projects p ON t.project_id = p.id
                WHERE t.id = ?
            ''', (task_id,)).fetchone()
            
            if task:
                # 更新任务状态
                self.db.cursor.execute('''
                    UPDATE tasks 
                    SET completed = 1, 
                        end_time = CURRENT_TIMESTAMP,
                        completion_note = ?
                    WHERE id = ?
                ''', (completion_note, task_id))
                
                # 更新今日日报
                today = datetime.now().date()
                report = self.db.cursor.execute('''
                    SELECT id, content FROM daily_reports 
                    WHERE report_date = ? AND user_id = ?
                ''', (today, task[3])).fetchone()
                
                # 准备任务完成记录
                project_name = task[2] if task[2] else '临时任务'
                task_record = (
                    f"完成任务：{task[0]}\n"
                    f"所属项目：{project_name}\n"
                )
                if completion_note:
                    task_record += f"完成说明：{completion_note}\n"
                task_record += "\n"
                
                if report:
                    # 如果今日已有日报，在末尾添加任务记录
                    new_content = report[1].rstrip() + "\n" + task_record
                    self.db.cursor.execute('''
                        UPDATE daily_reports 
                        SET content = ?, created_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (new_content, report[0]))
                else:
                    # 创建新日报
                    date_title = f"{today.strftime('%Y年%m月%d日')}工作日报\n\n"
                    self.db.cursor.execute('''
                        INSERT INTO daily_reports (report_date, content, user_id)
                        VALUES (?, ?, ?)
                    ''', (today, date_title + task_record, task[3]))
                
                self.db.conn.commit()
                return True
            return False
        except Exception as e:
            print(f"Error completing task: {e}")
            self.db.conn.rollback()
            return False
    
    def update_project_state(self, project_id, new_state):
        """更新项目状态"""
        try:
            # 获取旧状态和项目名称
            project_info = self.db.cursor.execute(
                'SELECT state, client_name FROM projects WHERE id = ?', (project_id,)
            ).fetchone()
            
            if not project_info:
                return False
            
            old_state = project_info[0]
            client_name = project_info[1]
            
            self.db.cursor.execute('''
                UPDATE projects 
                SET state = ?, last_updated = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_state, project_id))
            
            # 记录状态变更
            self.add_history_record(
                project_id=project_id,
                change_type='update',
                description=f'项目 [{client_name}] 状态变更',
                old_value=self.get_state_display(old_state),
                new_value=self.get_state_display(new_state)
            )
            
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating project state: {e}")
            self.db.conn.rollback()
            return False
    
    def get_state_display(self, state):
        state_map = {
            'active': '进行中',
            'recent_inactive': '维保中',
            'long_inactive': '合同到期退网'
        }
        return state_map.get(state, state)
    
    def add_history_record(self, project_id, change_type, description, old_value=None, new_value=None):
        self.db.cursor.execute('''
            INSERT INTO project_history (
                project_id, change_type, change_time, old_value, new_value, description
            )
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (project_id, change_type, datetime.now(), old_value, new_value, description))
        self.db.conn.commit()
    
    def add_maintenance_record(self, project_id, description):
        self.add_history_record(
            project_id=project_id,
            change_type='maintenance',
            description=description
        )
    
    def add_issue_record(self, project_id, description):
        self.add_history_record(
            project_id=project_id,
            change_type='issue',
            description=description
        )
    
    def get_project_history(self, project_id=None, client_name=None):
        if project_id:
            return self.db.cursor.execute('''
                SELECT 
                    h.id,
                    h.project_id,
                    h.change_type,
                    h.change_time,
                    h.old_value,
                    h.new_value,
                    h.description,
                    p.client_name 
                FROM project_history h
                JOIN projects p ON h.project_id = p.id
                WHERE h.project_id = ?
                ORDER BY h.change_time DESC
            ''', (project_id,)).fetchall()
        elif client_name:
            return self.db.cursor.execute('''
                SELECT 
                    h.id,
                    h.project_id,
                    h.change_type,
                    h.change_time,
                    h.old_value,
                    h.new_value,
                    h.description,
                    p.client_name 
                FROM project_history h
                JOIN projects p ON h.project_id = p.id
                WHERE p.client_name LIKE ?
                ORDER BY h.change_time DESC
            ''', (f'%{client_name}%',)).fetchall()
    
    def get_project(self, project_id):
        """获取项目信息，包括所有字段"""
        project = self.db.cursor.execute('''
            SELECT id, client_name, stage, status, created_at, last_updated, 
                   notes, state, is_active, area, manager, manager_phone 
            FROM projects 
            WHERE id = ?
        ''', (project_id,)).fetchone()
        
        if project:
            # 将查询结果转为字典，方便访问
            return {
                'id': project[0],
                'client_name': project[1],
                'stage': project[2],
                'status': project[3],
                'created_at': project[4],
                'last_updated': project[5],
                'notes': project[6],
                'state': project[7],
                'is_active': project[8],
                'area': project[9],
                'manager': project[10],
                'manager_phone': project[11]
            }
        return None
    
    def update_project_stage(self, project_id, new_stage):
        # 获取旧环节和项目名称
        project_info = self.db.cursor.execute(
            'SELECT stage, client_name FROM projects WHERE id = ?', (project_id,)
        ).fetchone()
        old_stage = project_info[0]
        client_name = project_info[1]
        
        if old_stage != new_stage:  # 只在环节确实改变才更新
            self.db.cursor.execute('''
                UPDATE projects 
                SET stage = ?, last_updated = ?
                WHERE id = ?
            ''', (new_stage, datetime.now(), project_id))
            
            # 记录环节变更
            self.add_history_record(
                project_id=project_id,
                change_type='update',
                description=f'项目 [{client_name}] 环节变更',
                old_value=old_stage,
                new_value=new_stage
            )
            
            self.db.conn.commit()
    
    def update_project_status(self, project_id, new_status):
        # 获取旧状态和项目名称
        project_info = self.db.cursor.execute(
            'SELECT status, client_name FROM projects WHERE id = ?', (project_id,)
        ).fetchone()
        old_status = project_info[0]
        client_name = project_info[1]
        
        if old_status != new_status:  # 只在状态确实改变时才更新
            self.db.cursor.execute('''
                UPDATE projects 
                SET status = ?, last_updated = ?
                WHERE id = ?
            ''', (new_status, datetime.now(), project_id))
            
            # 记录状态变更
            self.add_history_record(
                project_id=project_id,
                change_type='update',
                description=f'项目 [{client_name}] 状态变更',
                old_value=old_status,
                new_value=new_status
            )
            
            self.db.conn.commit()
    
    def add_maintenance_record(self, project_id, description):
        self.add_history_record(
            project_id=project_id,
            change_type='maintenance',
            description=description
        )
    
    def add_issue_record(self, project_id, description):
        self.add_history_record(
            project_id=project_id,
            change_type='issue',
            description=description
        )
    
    def get_project_history(self, project_id=None, client_name=None):
        if project_id:
            return self.db.cursor.execute('''
                SELECT 
                    h.id,
                    h.project_id,
                    h.change_type,
                    h.change_time,
                    h.old_value,
                    h.new_value,
                    h.description,
                    p.client_name 
                FROM project_history h
                JOIN projects p ON h.project_id = p.id
                WHERE h.project_id = ?
                ORDER BY h.change_time DESC
            ''', (project_id,)).fetchall()
        elif client_name:
            return self.db.cursor.execute('''
                SELECT 
                    h.id,
                    h.project_id,
                    h.change_type,
                    h.change_time,
                    h.old_value,
                    h.new_value,
                    h.description,
                    p.client_name 
                FROM project_history h
                JOIN projects p ON h.project_id = p.id
                WHERE p.client_name LIKE ?
                ORDER BY h.change_time DESC
            ''', (f'%{client_name}%',)).fetchall()
    
    def get_daily_report(self, date, user_id):
        """获取指定日期的日报"""
        try:
            # 获取指定日期的任务
            tasks = self.get_daily_tasks(date, user_id)
            
            # 将日期字符串转换为datetime对象
            date_obj = datetime.strptime(date, '%Y-%m-%d')
            date_title = f"{date_obj.strftime('%Y年%m月%d日')}日报\n\n"
            
            # 生成报告内容
            content = date_title
            
            # 添加任务内容
            for i, task in enumerate(tasks, 1):
                content += f"{i}. \n"  # 添加任务序号
                content += f"任务类别：{task['project_name']}\n"  # 第一行：任务类别
                content += f"任务内容：{task['content']}\n"  # 第二行：任务内容
                content += f"完成情况：{task['status']}\n"  # 第三行：完成情况
                content += "\n"  # 添加空行分隔
            
            if not tasks:
                content += "今日暂无工作记录\n"
            
            return {
                'date': date,
                'content': content,
                'task_count': len(tasks)
            }
        except Exception as e:
            print(f"Error getting daily report: {e}")
            return {
                'date': date,
                'content': f"{date_title}今日暂无工作记录\n",
                'task_count': 0
            }
    
    def get_date_range_reports(self, start_date, end_date, user_id):
        """获取指定日期范围内的日报"""
        try:
            reports = self.db.cursor.execute("""
                SELECT report_date, content FROM daily_reports 
                WHERE user_id = ? AND report_date BETWEEN ? AND ?
                ORDER BY report_date DESC
            """, (user_id, start_date, end_date)).fetchall()
            return [{'date': report[0], 'content': report[1]} for report in reports]
        except Exception as e:
            print(f"Error getting date range reports: {e}")
            return None

    def generate_weekly_report(self, year, week, user_id):
        """生成周报"""
        try:
            # 计算周的起始日期和结束日期
            year = int(year)
            week = int(week)
            first_day = datetime.strptime(f'{year}-{week}-1', '%Y-%W-%w')
            last_day = first_day + timedelta(days=6)
            
            # 获取这一周每天的任务
            report_content = f"{year}年第{week}周工作周报\n\n"
            
            current_day = first_day
            task_number = 1
            while current_day <= last_day:
                date_str = current_day.strftime('%Y-%m-%d')
                tasks = self.get_daily_tasks(date_str, user_id)
                
                if tasks:
                    for task in tasks:
                        report_content += f"{task_number}. \n"
                        report_content += f"任务类别：{task['project_name']}\n"
                        report_content += f"任务内容：{task['content']}\n"
                        report_content += f"完成情况：{task['status']}\n"
                        report_content += "\n"
                        task_number += 1
                
                current_day += timedelta(days=1)
            
            if task_number == 1:
                report_content += "本周无工作记录\n"
            
            return report_content
        except Exception as e:
            print(f"Error generating weekly report: {e}")
            return None

    def generate_monthly_report(self, year, month, user_id):
        """生成月报"""
        try:
            # 确保年月是整数
            year = int(year)
            month = int(month)
            
            # 计算月的起始日期和结束日期
            first_day = datetime(year, month, 1)
            if month == 12:
                next_year = year + 1
                next_month = 1
            else:
                next_year = year
                next_month = month + 1
            last_day = datetime(next_year, next_month, 1) - timedelta(days=1)
            
            # 获取这个月每天的任务
            report_content = f"{year}年{month}月工作月报\n\n"
            
            current_day = first_day
            task_number = 1
            while current_day <= last_day:
                date_str = current_day.strftime('%Y-%m-%d')
                tasks = self.get_daily_tasks(date_str, user_id)
                
                if tasks:
                    for task in tasks:
                        report_content += f"{task_number}. \n"
                        report_content += f"任务类别：{task['project_name']}\n"
                        report_content += f"任务内容：{task['content']}\n"
                        report_content += f"完成情况：{task['status']}\n"
                        report_content += "\n"
                        task_number += 1
                
                current_day += timedelta(days=1)
            
            if task_number == 1:
                report_content += "本月无工作记录\n"
            
            return report_content
        except Exception as e:
            print(f"Error generating monthly report: {e}")
            return None
    
    def delete_project(self, project_id):
        """删除项目"""
        try:
            # 首先删除相关的历史记录
            self.db.cursor.execute('DELETE FROM project_history WHERE project_id = ?', (project_id,))
            # 删除相关的设备信息
            self.db.cursor.execute('DELETE FROM project_devices WHERE project_id = ?', (project_id,))
            # 删除相关的任务
            self.db.cursor.execute('DELETE FROM tasks WHERE project_id = ?', (project_id,))
            # 最后删除项目
            self.db.cursor.execute('DELETE FROM projects WHERE id = ?', (project_id,))
            
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting project: {e}")
            self.db.conn.rollback()
            return False
    
    def cancel_task(self, task_id, cancel_reason=''):
        """取消任务"""
        try:
            # 获取任务信息
            task = self.db.cursor.execute('''
                SELECT t.content, t.project_id, p.client_name, t.user_id
                FROM tasks t
                LEFT JOIN projects p ON t.project_id = p.id
                WHERE t.id = ?
            ''', (task_id,)).fetchone()
            
            if task:
                # 更新任务状态
                self.db.cursor.execute('''
                    UPDATE tasks 
                    SET completed = 2,  -- 2 表示已取消
                        end_time = CURRENT_TIMESTAMP,
                        completion_note = ?
                    WHERE id = ?
                ''', (cancel_reason, task_id))
                
                # 更新今日日报
                today = datetime.now().date()
                report = self.db.cursor.execute('''
                    SELECT id, content FROM daily_reports 
                    WHERE report_date = ? AND user_id = ?
                ''', (today, task[3])).fetchone()
                
                # 准备任务取消记录
                project_name = task[2] if task[2] else '临时任务'
                task_record = (
                    f"取消任务：{task[0]}\n"
                    f"所属项目：{project_name}\n"
                    f"取消原因：{cancel_reason}\n\n"
                )
                
                if report:
                    # 如果今日已有日报，在末尾添加任务记录
                    new_content = report[1].rstrip() + "\n" + task_record
                    self.db.cursor.execute('''
                        UPDATE daily_reports 
                        SET content = ?, created_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    ''', (new_content, report[0]))
                else:
                    # 创建新日报
                    date_title = f"{today.strftime('%Y年%m月%d日')}工作日报\n\n"
                    self.db.cursor.execute('''
                        INSERT INTO daily_reports (report_date, content, user_id)
                        VALUES (?, ?, ?)
                    ''', (today, date_title + task_record, task[3]))
                
                self.db.conn.commit()
                return True
            return False
        except Exception as e:
            print(f"Error canceling task: {e}")
            self.db.conn.rollback()
            return False
    
    def get_project_statistics(self):
        """获取项目统计信息"""
        stats = {
            'total': {'count': 0, 'projects': []},
            'active': {'count': 0, 'projects': []},
            'recent_inactive': {'count': 0, 'projects': []},
            'long_inactive': {'count': 0, 'projects': []},
            'completed': {'count': 0, 'projects': []},
            'stages': {}
        }
        
        # 查询所有项目
        all_projects = self.db.cursor.execute('''
            SELECT id, client_name, state, stage, is_active 
            FROM projects
        ''').fetchall()
        
        for project in all_projects:
            project_info = {'id': project[0], 'name': project[1]}
            stats['total']['count'] += 1
            stats['total']['projects'].append(project_info)
            
            if project[4] == 0:  # 已完成
                stats['completed']['count'] += 1
                stats['completed']['projects'].append(project_info)
            else:  # 进行中
                if project[2] == 'active':
                    stats['active']['count'] += 1
                    stats['active']['projects'].append(project_info)
                elif project[2] == 'recent_inactive':
                    stats['recent_inactive']['count'] += 1
                    stats['recent_inactive']['projects'].append(project_info)
                elif project[2] == 'long_inactive':
                    stats['long_inactive']['count'] += 1
                    stats['long_inactive']['projects'].append(project_info)
                
                # 统计环节
                stage = project[3]
                if stage not in stats['stages']:
                    stats['stages'][stage] = {'count': 0, 'projects': []}
                stats['stages'][stage]['count'] += 1
                stats['stages'][stage]['projects'].append(project_info)
        
        return stats
    
    def add_device_info(self, project_id, device_info):
        """添加设备信息"""
        try:
            for device in device_info:
                if device['type'] == '分流设备':
                    self.db.cursor.execute('''
                        INSERT INTO devices (
                            project_id, device_type, device_name, model,
                            mec_10g, ge_optical, electrical
                        )
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        project_id,
                        device['type'],
                        device['name'],
                        device['model'],
                        device['cards'].get('mec_10g', 0),
                        device['cards'].get('ge_optical', 0),
                        device['cards'].get('electrical', 0)
                    ))
                else:
                    self.db.cursor.execute('''
                        INSERT INTO devices (
                            project_id, device_type, device_name, 
                            model, card_quantity
                        )
                        VALUES (?, ?, ?, ?, ?)
                    ''', (
                        project_id,
                        device['type'],
                        device['name'],
                        device['model'],
                        device.get('card_quantity', 0)
                    ))
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"Error adding device info: {e}")
            self.db.conn.rollback()
            return False
    
    def get_project_devices(self, project_id):
        """获取项目的设备信息"""
        try:
            devices = self.db.cursor.execute('''
                SELECT id, device_type, device_name, model,
                       mec_10g, ge_optical, electrical, card_quantity
                FROM devices 
                WHERE project_id = ?
                ORDER BY device_type, id
            ''', (project_id,)).fetchall()
            
            if not devices:
                return []
            
            return [{
                'id': device[0],
                'type': device[1],
                'name': device[2],
                'model': device[3],
                'cards': {
                    'mec_10g': device[4],
                    'ge_optical': device[5],
                    'electrical': device[6]
                } if device[1] == '分流设备' else None,
                'card_quantity': device[7] if device[1] != '分流设备' else None
            } for device in devices]
        except Exception as e:
            print(f"Error getting project devices: {e}")
            return []
    
    def update_device_info(self, device_id, data):
        """更新设备信息"""
        try:
            device = self.db.cursor.execute(
                'SELECT device_type FROM devices WHERE id = ?', 
                (device_id,)
            ).fetchone()
            
            if not device:
                return False
            
            if device[0] == '分流设备':
                if 'cards' in data:
                    self.db.cursor.execute('''
                        UPDATE devices 
                        SET mec_10g = ?, ge_optical = ?, electrical = ?
                        WHERE id = ?
                    ''', (
                        data['cards'].get('mec_10g', 0),
                        data['cards'].get('ge_optical', 0),
                        data['cards'].get('electrical', 0),
                        device_id
                    ))
                else:
                    self.db.cursor.execute('''
                        UPDATE devices 
                        SET device_name = ?, model = ?
                        WHERE id = ?
                    ''', (data.get('name'), data.get('model'), device_id))
            else:
                self.db.cursor.execute('''
                    UPDATE devices 
                    SET device_name = ?, model = ?, card_quantity = ?
                    WHERE id = ?
                ''', (
                    data.get('name'),
                    data.get('model'),
                    data.get('card_quantity', 0),
                    device_id
                ))
            
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating device info: {e}")
            self.db.conn.rollback()
            return False
    
    def delete_device(self, device_id):
        """删除设备"""
        try:
            self.db.cursor.execute('DELETE FROM devices WHERE id = ?', (device_id,))
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting device: {e}")
            self.db.conn.rollback()
            return False
    
    def update_project_info(self, project_id, field, value):
        """更新项目信息"""
        try:
            # 如果是更新ID需要检查新ID是否已存在
            if field == 'id':
                existing = self.db.cursor.execute(
                    'SELECT id FROM projects WHERE id = ?', 
                    (value,)
                ).fetchone()
                if existing:
                    raise ValueError("新项目ID已存在")

            # 获取旧值用于历史记录
            old_value = self.db.cursor.execute(
                f'SELECT {field} FROM projects WHERE id = ?', 
                (project_id,)
            ).fetchone()[0]
            
            # 更新项目信息
            if field == 'id':
                # 更新项目ID需要同时更新相关
                self.db.cursor.execute('''
                    UPDATE project_history 
                    SET project_id = ? 
                    WHERE project_id = ?
                ''', (value, project_id))
                
                self.db.cursor.execute('''
                    UPDATE project_devices 
                    SET project_id = ? 
                    WHERE project_id = ?
                ''', (value, project_id))
                
                self.db.cursor.execute('''
                    UPDATE tasks 
                    SET project_id = ? 
                    WHERE project_id = ?
                ''', (value, project_id))

            # 更新主表
            self.db.cursor.execute(f'''
                UPDATE projects 
                SET {field} = ?, last_updated = ?
                WHERE id = ?
            ''', (value, datetime.now(), project_id))
            
            # 添加更新记录到历史表
            self.add_history_record(
                project_id=project_id,
                change_type='update',
                description=f'更新项目{field}',
                old_value=str(old_value),
                new_value=str(value)
            )
            
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating project info: {e}")
            self.db.conn.rollback()
            return False
    
    def complete_project(self, project_id):
        """完成项目"""
        try:
            print(f"尝试完成项目 {project_id}")
            
            # 检查项目是否存在且未完成
            project = self.db.cursor.execute('''
                SELECT client_name, is_active 
                FROM projects 
                WHERE id = ?
            ''', (project_id,)).fetchone()
            
            if not project:
                print(f"项目 {project_id} 不存在")
                return False
                
            if project[1] == 0:
                print(f"项目 {project_id} 已经完成")
                return False
            
            print(f"找到项目：{project[0]}")
            
            # 更新项目状态
            self.db.cursor.execute('''
                UPDATE projects 
                SET is_active = 0, 
                    last_updated = CURRENT_TIMESTAMP,
                    state = 'completed'
                WHERE id = ?
            ''', (project_id,))
            
            print(f"已更新项目状态为完成")
            
            # 添加完成记录
            self.add_history_record(
                project_id=project_id,
                change_type='complete',
                description=f'项目完成: {project[0]}'
            )
            
            print(f"已添加完成记录")
            
            self.db.conn.commit()
            print(f"项目 {project_id} ({project[0]}) 已成功完成")
            return True
            
        except Exception as e:
            print(f"完成项目 {project_id} 时出错：{e}")
            self.db.conn.rollback()
            return False
    
    def update_record(self, record_id, description, old_value=None, new_value=None):
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE project_history 
                    SET description = ?,
                        old_value = ?,
                        new_value = ?
                    WHERE id = ?
                """, (description, old_value, new_value, record_id))
                conn.commit()
                return True
        except Exception as e:
            print(f"Error in update_record: {e}")
            return False
    
    def delete_record(self, record_id):
        """删除记录"""
        try:
            self.db.cursor.execute('''
                DELETE FROM project_history 
                WHERE id = ?
            ''', (record_id,))
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting record: {e}")
            self.db.conn.rollback()
            return False
    
    def authenticate_user(self, username, password):
        """验证用户登录"""
        user = self.db.cursor.execute('''
            SELECT id, username, password, role 
            FROM users 
            WHERE username = ? AND is_active = 1
        ''', (username,)).fetchone()
        
        if user and self.db.verify_password(user[2], password):
            self.db.cursor.execute('''
                UPDATE users 
                SET last_login = CURRENT_TIMESTAMP 
                WHERE id = ?
            ''', (user[0],))
            self.db.conn.commit()
            return {
                'id': user[0],
                'username': user[1],
                'role': user[3]
            }
        return None
    
    def check_permission(self, user_id, module, action):
        """检查用户权限"""
        # 超级管理员拥有所有权限
        user = self.db.cursor.execute(
            'SELECT role FROM users WHERE id = ?', 
            (user_id,)
        ).fetchone()
        
        if user and user[0] == 'admin':
            return True
        
        # 普通用户默认拥有除用户管理外的所有权限
        if module == 'users':
            return False
        
        return True
    
    def get_user_tasks(self, user_id):
        """获取用户的任务"""
        return self.db.cursor.execute('''
            SELECT id, project_id, content, priority,
                   start_time, end_time, completed
            FROM tasks 
            WHERE user_id = ? AND completed = 0
            ORDER BY priority DESC
        ''', (user_id,)).fetchall()
    
    def get_user_projects(self, user_id):
        """获取用户的项目"""
        active = self.db.cursor.execute('''
            SELECT p.* FROM projects p
            JOIN user_projects up ON p.id = up.project_id
            WHERE up.user_id = ? AND p.state = 'active' AND p.is_active = 1
            ORDER BY p.last_updated DESC
        ''', (user_id,)).fetchall()
        
        recent_inactive = self.db.cursor.execute('''
            SELECT p.* FROM projects p
            JOIN user_projects up ON p.id = up.project_id
            WHERE up.user_id = ? AND p.state = 'recent_inactive' AND p.is_active = 1
            ORDER BY p.last_updated DESC
        ''', (user_id,)).fetchall()
        
        long_inactive = self.db.cursor.execute('''
            SELECT p.* FROM projects p
            JOIN user_projects up ON p.id = up.project_id
            WHERE up.user_id = ? AND p.state = 'long_inactive' AND p.is_active = 1
            ORDER BY p.last_updated DESC
        ''', (user_id,)).fetchall()
        
        return {
            "active_projects": active,
            "recent_inactive": recent_inactive,
            "long_inactive": long_inactive
        }
    
    def get_users(self):
        """获取所有用户列表"""
        users = self.db.cursor.execute('''
            SELECT id, username, role, created_at, last_login, is_active 
            FROM users
            ORDER BY created_at DESC
        ''').fetchall()
        
        # 将元组转换为字典列表
        return [{
            'id': user[0],
            'username': user[1],
            'role': user[2],
            'created_at': user[3],
            'last_login': user[4],
            'is_active': user[5]
        } for user in users]
    
    def add_user(self, data):
        """添加新用户"""
        try:
            # 检查用户名是否已存在
            existing = self.db.cursor.execute(
                'SELECT id FROM users WHERE username = ?', 
                (data['username'],)
            ).fetchone()
            
            if existing:
                return False
            
            # 添加用户
            self.db.cursor.execute('''
                INSERT INTO users (username, password, role)
                VALUES (?, ?, ?)
            ''', (
                data['username'],
                self.db.hash_password(data['password']),
                data['role']
            ))
            
            user_id = self.db.cursor.lastrowid
            
            # 设置默认权限：所有模块都有完全权限
            for module in ['projects', 'tasks', 'reports']:
                self.db.cursor.execute('''
                    INSERT INTO permissions (user_id, module, can_view, can_add, can_edit, can_delete)
                    VALUES (?, ?, 1, 1, 1, 1)
                ''', (user_id, module))
            
            # 为新用户添加所有现有项目的访问权限
            self.db.cursor.execute('''
                INSERT INTO user_projects (user_id, project_id)
                SELECT ?, id FROM projects
            ''', (user_id,))
            
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"Error adding user: {e}")
            self.db.conn.rollback()
            return False
    
    def update_user_permissions(self, user_id, permissions):
        """更新用户权限"""
        try:
            for module, perms in permissions.items():
                self.db.cursor.execute('''
                    INSERT OR REPLACE INTO permissions 
                    (user_id, module, can_view, can_add, can_edit, can_delete)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    user_id, module,
                    perms.get('view', False),
                    perms.get('add', False),
                    perms.get('edit', False),
                    perms.get('delete', False)
                ))
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating permissions: {e}")
            self.db.conn.rollback()
            return False
    
    def toggle_user_status(self, user_id):
        """启用/禁用用户"""
        try:
            self.db.cursor.execute('''
                UPDATE users 
                SET is_active = NOT is_active 
                WHERE id = ? AND username != 'liusw'
            ''', (user_id,))
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"Error toggling user status: {e}")
            self.db.conn.rollback()
            return False
    
    def delete_user(self, user_id):
        """删除用户"""
        try:
            # 检查是否是超级管理员
            user = self.db.cursor.execute(
                'SELECT username FROM users WHERE id = ?', 
                (user_id,)
            ).fetchone()
            
            if user and user[0] != 'liusw':
                # 删除用户的权限
                self.db.cursor.execute('DELETE FROM permissions WHERE user_id = ?', (user_id,))
                # 删除用户的项目访问权限
                self.db.cursor.execute('DELETE FROM user_projects WHERE user_id = ?', (user_id,))
                # 删除用户
                self.db.cursor.execute('DELETE FROM users WHERE id = ?', (user_id,))
                self.db.conn.commit()
                return True
            return False
        except Exception as e:
            print(f"Error deleting user: {e}")
            self.db.conn.rollback()
            return False
    
    def get_user_permissions(self, user_id):
        """获取用户权限"""
        permissions = {}
        modules = ['projects', 'tasks', 'reports']
        
        for module in modules:
            perm = self.db.cursor.execute('''
                SELECT can_view, can_add, can_edit, can_delete 
                FROM permissions 
                WHERE user_id = ? AND module = ?
            ''', (user_id, module)).fetchone()
            
            if perm:
                permissions[module] = {
                    'view': bool(perm[0]),
                    'add': bool(perm[1]),
                    'edit': bool(perm[2]),
                    'delete': bool(perm[3])
                }
            else:
                permissions[module] = {
                    'view': False,
                    'add': False,
                    'edit': False,
                    'delete': False
                }
        
        return permissions
    
    def reactivate_project(self, project_id, state='active'):
        """重新激活已完成的项目"""
        try:
            project = self.db.cursor.execute(
                'SELECT client_name, is_active FROM projects WHERE id = ?', 
                (project_id,)
            ).fetchone()
            
            if project and project[1] == 0:  # 确保项目存在且已完成
                self.db.cursor.execute('''
                    UPDATE projects 
                    SET is_active = 1,
                        state = ?,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', (state, project_id))
                
                # 添加重新激活记录
                self.add_history_record(
                    project_id=project_id,
                    change_type='reactivate',
                    description=f'项目重新激活: {project[0]}',
                    old_value='完成',
                    new_value=self.get_state_display(state)
                )
                
                self.db.conn.commit()
                return True
            return False
        except Exception as e:
            print(f"Error reactivating project: {e}")
            self.db.conn.rollback()
            return False
    
    def get_all_projects(self):
        """获取所有项目"""
        try:
            print("\n开始获取所有项目...")
            
            # 获取所有项目，按最后更新时间排序
            query = '''
                SELECT id, client_name, stage, status, created_at, 
                       last_updated, state, is_active, area
                FROM projects
                ORDER BY last_updated DESC
            '''
            print(f"执行查询：{query}")
            
            projects = self.db.cursor.execute(query).fetchall()
            print(f"查询到 {len(projects)} 个项目")
            
            result = [{
                'id': p[0],
                'client_name': p[1],
                'stage': p[2],
                'status': p[3],
                'created_at': p[4],
                'last_updated': p[5],
                'state': p[6],
                'is_active': p[7],
                'area': p[8] if p[8] else '未分类'
            } for p in projects]
            
            return result
        except Exception as e:
            print(f"获取所有项目时出错：{str(e)}")
            return []
    
    def add_task_to_report(self, user_id, task_record):
        """添加任务记录到日报"""
        today = datetime.now().date()
        report = self.db.cursor.execute('''
            SELECT id, content FROM daily_reports 
            WHERE report_date = ? AND user_id = ?
        ''', (today, user_id)).fetchone()
        
        if report:
            # 取下一个任务序号
            next_number = self.get_next_task_number(report[1])
            
            # 在任务记录前添加序号
            numbered_record = f"{next_number}. {task_record}"
            
            # 更新日报内容
            new_content = f"{report[1]}\n{numbered_record}"
            
            self.db.cursor.execute('''
                UPDATE daily_reports 
                SET content = ?
                WHERE id = ?
            ''', (new_content, report[0]))
    
    def get_project_status(self, project_id):
        """获取项目当前状态"""
        try:
            status = self.db.cursor.execute('''
                SELECT status FROM projects WHERE id = ?
            ''', (project_id,)).fetchone()
            
            return status[0] if status else None
        except Exception as e:
            print(f"Error getting project status: {e}")
            return None
    
    def update_project_status(self, project_id, new_status, old_status=None):
        """更新项目状态"""
        try:
            if old_status is None:
                old_status = self.get_project_status(project_id)
            
            # 获取项目名称用于历史记录
            project = self.db.cursor.execute('''
                SELECT client_name FROM projects WHERE id = ?
            ''', (project_id,)).fetchone()
            
            if not project:
                return False
            
            # 更新状态
            self.db.cursor.execute('''
                UPDATE projects 
                SET status = ?, last_updated = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (new_status, project_id))
            
            # 添加历史记录
            if old_status != new_status:
                self.add_history_record(
                    project_id=project_id,
                    change_type='update',
                    description=f'项目 [{project[0]}] 状态更新',
                    old_value=old_status,
                    new_value=new_status
                )
            
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating project status: {e}")
            self.db.conn.rollback()
            return False
    
    def get_daily_tasks(self, date, user_id):
        """获取指定日期的任务列表"""
        try:
            cursor = self.db.cursor
            cursor.execute("""
                SELECT t.project_id, t.content, t.completed, t.completion_note,
                       p.client_name as project_name
                FROM tasks t
                LEFT JOIN projects p ON t.project_id = p.id
                WHERE t.user_id = ? AND date(t.start_time) = date(?)
                ORDER BY t.start_time
            """, (user_id, date))
            
            tasks = []
            for row in cursor.fetchall():
                # 确定任务类别
                project_id = row[0]  # project_id
                if project_id is None or project_id == '0':
                    task_type = '临时任务'
                elif project_id == 'daily':
                    task_type = '日常工作'
                else:
                    task_type = row[4] or '未分配项'  # project_name
                
                # 确定完成情况
                if row[2] == 1:  # completed
                    status = row[3] if row[3] else "已完成"  # completion_note
                elif row[2] == 2:  # completed
                    status = "已取消"
                else:
                    status = "进行中"
                    
                tasks.append({
                    'project_name': task_type,
                    'content': row[1],  # content
                    'status': status
                })
            
            return tasks
        except Exception as e:
            print(f"Error getting daily tasks: {e}")
            return []
    
    def get_projects_by_state(self, state):
        """根据状态获取项目列表"""
        try:
            if state == 'completed':
                # 获取已完成的项目
                projects = self.db.cursor.execute('''
                    SELECT id, client_name, stage, status, created_at, 
                           last_updated, state, is_active, area
                    FROM projects
                    WHERE is_active = 0
                    ORDER BY last_updated DESC
                ''').fetchall()
            else:
                # 获取指定状态的项目
                projects = self.db.cursor.execute('''
                    SELECT id, client_name, stage, status, created_at, 
                           last_updated, state, is_active, area
                    FROM projects
                    WHERE state = ? AND is_active = 1
                    ORDER BY last_updated DESC
                ''', (state,)).fetchall()
            
            return [{
                'id': p[0],
                'client_name': p[1],
                'stage': p[2],
                'status': p[3],
                'created_at': p[4],
                'last_updated': p[5],
                'state': p[6],
                'is_active': p[7],
                'area': p[8] if p[8] else '未分类'
            } for p in projects]
        except Exception as e:
            print(f"Error getting projects by state: {e}")
            return []
    
    def export_project_record(self, project_id):
        """导出项目记录"""
        try:
            # 获取项目信息
            project = self.get_project(project_id)
            if not project:
                return None
            
            # 获取项目历史记录
            history = self.get_project_history(project_id)
            if not history:
                history = []
            
            # 获取设备信息
            devices = self.get_project_devices(project_id)
            
            # 生成导出内容
            content = f"项目记录 - {project['client_name']}\n"
            content += "=" * 50 + "\n\n"
            
            # 项目基本信息
            content += "项目基本信息：\n"
            content += "-" * 20 + "\n"
            content += f"项目ID：{project['id']}\n"
            content += f"客户名称：{project['client_name']}\n"
            content += f"当前环节：{project['stage']}\n"
            content += f"当前状态：{project['status']}\n"
            content += f"项目区域：{project['area']}\n"
            content += f"项目经理：{project['manager']}\n"
            content += f"联系电话：{project['manager_phone']}\n"
            content += "\n"
            
            # 设备信息
            content += "设备信息：\n"
            content += "-" * 20 + "\n"
            for device in devices:
                content += f"设备类型：{device['type']}\n"
                content += f"设备名称：{device['name']}\n"
                content += f"设备型号：{device['model']}\n"
                if device['type'] == '分流设备':
                    content += f"万兆光卡：{device['cards']['mec_10g']}\n"
                    content += f"千兆光卡：{device['cards']['ge_optical']}\n"
                    content += f"口卡：{device['cards']['electrical']}\n"
                else:
                    content += f"业务板卡数量：{device['card_quantity']}\n"
                content += "\n"
            
            # 历史记录
            content += "历史记录：\n"
            content += "-" * 20 + "\n"
            for record in history:
                # 使用索引访问元组中的值
                change_time = record[3]  # change_time 在索引 3
                change_type = record[2]  # change_type 在索引 2
                description = record[6]  # description 在索引 6
                old_value = record[4]    # old_value 在索引 4
                new_value = record[5]    # new_value 在索引 5
                
                content += f"时间：{change_time}\n"
                content += f"类型：{change_type}\n"
                content += f"描述：{description}\n"
                if old_value:
                    content += f"更新前：{old_value}\n"
                if new_value:
                    content += f"更新后：{new_value}\n"
                content += "\n"
            
            return content
        except Exception as e:
            print(f"Error exporting project record: {e}")
            return None
    
    def update_daily_report(self, date, content, user_id):
        """更新日报内容"""
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # 检查是否已存在该日期的日报
                cursor.execute("""
                    SELECT id FROM daily_reports 
                    WHERE report_date = ? AND user_id = ?
                """, (date, user_id))
                
                existing = cursor.fetchone()
                
                if existing:
                    # 更新现有日报
                    cursor.execute("""
                        UPDATE daily_reports 
                        SET content = ?, 
                            created_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """, (content, existing[0]))
                else:
                    # 创建新日报
                    cursor.execute("""
                        INSERT INTO daily_reports (report_date, content, user_id)
                        VALUES (?, ?, ?)
                    """, (date, content, user_id))
                
                conn.commit()
                return True
                
        except Exception as e:
            print(f"Error updating daily report: {e}")
            return False
    
    def create_project(self, project_data):
        """创建新项目"""
        try:
            self.db.cursor.execute('''
                INSERT INTO projects (
                    client_name, stage, status, notes, area,
                    created_at, last_updated
                ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
            ''', (
                project_data['client_name'],
                project_data.get('stage', ''),
                project_data.get('status', ''),
                project_data.get('notes', ''),
                project_data.get('area', '未分类')
            ))
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"Error creating project: {e}")
            return False
    
    def update_project(self, project_id, project_data):
        """更新项目信息"""
        try:
            self.db.cursor.execute('''
                UPDATE projects 
                SET client_name = ?,
                    stage = ?,
                    status = ?,
                    notes = ?,
                    area = ?,
                    last_updated = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (
                project_data['client_name'],
                project_data.get('stage', ''),
                project_data.get('status', ''),
                project_data.get('notes', ''),
                project_data.get('area', '未分类'),
                project_id
            ))
            self.db.conn.commit()
            return True
        except Exception as e:
            print(f"Error updating project: {e}")
            return False