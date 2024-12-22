from work_manager import WorkManager

def test_add_project():
    manager = WorkManager()
    
    # 测试数据
    test_cases = [
        {
            'project_id': 110,
            'client_name': '测试客户1',
            'stage': '设备安装',
            'status': '进行中',
            'notes': '',
            'area': '重庆',
            'manager': '张三',
            'manager_phone': '13800138000'
        },
        {
            'project_id': 111,
            'client_name': '测试客户2',
            'stage': '设备调测',
            'status': '准备中',
            'notes': '',
            'area': '成都',
            'manager': '李四',
            'manager_phone': '13900139000'
        }
    ]
    
    for case in test_cases:
        try:
            print(f"\n测试添加项目: ID={case['project_id']}")
            success = manager.add_project(
                case['project_id'],
                case['client_name'],
                case['stage'],
                case['status'],
                case['notes'],
                case['area'],
                case['manager'],
                case['manager_phone']
            )
            if success:
                print(f"项目 {case['project_id']} 添加成功")
            else:
                print(f"项目 {case['project_id']} 添加失败")
        except Exception as e:
            print(f"添加项目 {case['project_id']} 时出错: {e}")

if __name__ == '__main__':
    test_add_project() 