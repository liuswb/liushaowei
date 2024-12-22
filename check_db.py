from models import Database

def check_projects():
    """检查数据库中的项目数据"""
    db = Database()
    
    print("\n检查项目表...")
    projects = db.cursor.execute('''
        SELECT id, client_name, stage, status, created_at, 
               last_updated, state, is_active, area
        FROM projects
        ORDER BY last_updated DESC
    ''').fetchall()
    
    print(f"\n找到 {len(projects)} 个项目：")
    for p in projects:
        print(f"\nID: {p[0]}")
        print(f"客户名称: {p[1]}")
        print(f"环节: {p[2]}")
        print(f"状态: {p[3]}")
        print(f"创建时间: {p[4]}")
        print(f"最后更新: {p[5]}")
        print(f"项目状态: {p[6]}")
        print(f"是否活动: {p[7]}")
        print(f"区域: {p[8]}")
        print("-" * 50)

if __name__ == '__main__':
    check_projects() 