from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from work_manager import WorkManager
from functools import wraps

bp = Blueprint('project', __name__)
manager = WorkManager()

@bp.route('/projects')
def projects():
    """显示所有项目"""
    try:
        projects = manager.get_all_projects()
        return render_template('projects.html', projects=projects)
    except Exception as e:
        flash('获取项目列表失败')
        return redirect(url_for('index'))

@bp.route('/project/<int:project_id>')
def project_detail(project_id):
    """显示项目详情"""
    try:
        project = manager.get_project(project_id)
        if project:
            return render_template('project_detail.html', project=project)
        flash('项目不存在')
        return redirect(url_for('projects'))
    except Exception as e:
        flash('获取项目详情失败')
        return redirect(url_for('projects'))

@bp.route('/project/create', methods=['GET', 'POST'])
def create_project():
    """创建新项目"""
    if request.method == 'POST':
        try:
            project_data = {
                'client_name': request.form.get('client_name'),
                'stage': request.form.get('stage'),
                'status': request.form.get('status'),
                'area': request.form.get('area'),
                'notes': request.form.get('notes')
            }
            
            if manager.create_project(project_data):
                flash('项目创建成功')
                return redirect(url_for('projects'))
            else:
                flash('项目创建失败')
        except Exception as e:
            flash('项目创建失败')
    
    return render_template('project_form.html', title='创建项目')

@bp.route('/project/<int:project_id>/edit', methods=['GET', 'POST'])
def edit_project(project_id):
    """编辑项目"""
    if request.method == 'POST':
        try:
            project_data = {
                'client_name': request.form.get('client_name'),
                'stage': request.form.get('stage'),
                'status': request.form.get('status'),
                'area': request.form.get('area'),
                'notes': request.form.get('notes')
            }
            
            if manager.update_project(project_id, project_data):
                flash('项目更新成功')
                return redirect(url_for('project_detail', project_id=project_id))
            else:
                flash('项目更新失败')
        except Exception as e:
            flash('项目更新失败')
    
    project = manager.get_project(project_id)
    if not project:
        flash('项目不存在')
        return redirect(url_for('projects'))
    
    return render_template('project_form.html', project=project, title='编辑项目') 