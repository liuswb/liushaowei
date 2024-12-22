import sqlite3

def get_max_project_id():
    conn = sqlite3.connect('work_management.db')
    cursor = conn.cursor()
    cursor.execute('SELECT MAX(id) FROM projects')
    max_id = cursor.fetchone()[0]
    conn.close()
    return max_id or 0

def test_add_project():
    try:
        # 获取当前最大项目ID
        max_id = get_max_project_id()
        new_id = max_id + 1
        
        # 连接数据库
        conn = sqlite3.connect('work_management.db')
        cursor = conn.cursor()
        
        # 测试数据
        project_data = (
            new_id,  # id
            '测试客户1',  # client_name
            '设备安装',  # stage
            '进行中',  # status
            '',  # notes
            '重庆',  # area
            '张三',  # manager
            '13800138000'  # manager_phone
        )
        
        print(f"尝试添加项目，ID={new_id}")
        
        # 添加项目
        cursor.execute('''
            INSERT INTO projects (
                id, client_name, stage, status, notes, 
                created_at, last_updated, state, is_active,
                area, manager, manager_phone
            )
            VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP, 'active', 1, ?, ?, ?)
        ''', project_data)
        
        # 提交事务
        conn.commit()
        print("项目添加成功")
        
        # 验证项目是否添加成功
        cursor.execute('SELECT * FROM projects WHERE id = ?', (project_data[0],))
        project = cursor.fetchone()
        if project:
            print(f"项目验证成功：ID={project[0]}, 客户={project[1]}")
        else:
            print("项目验证失败：未找到项目")
        
        conn.close()
    except sqlite3.IntegrityError as e:
        print(f"数据完整性错误：{e}")
    except Exception as e:
        print(f"发生错误：{e}")

if __name__ == '__main__':
    test_add_project() 