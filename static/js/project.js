// 项目状态更新
function updateProjectState(projectId, newState) {
    fetch(`/update_project_state/${projectId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ state: newState })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert('状态更新失败，不允许此转');
            // 重置选择到原来的状态
            location.reload();
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('状态更新失败，请重试');
        location.reload();
    });
}

// 项目完成
function completeProject(projectId) {
    if (confirm('确定要将此项目标记为完成吗？')) {
        fetch(`/complete_project/${projectId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('完成项目失败，请重试');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('完成项目失败，请重试');
        });
    }
}

// 项目环节更新
function updateProjectStage(projectId, newStage) {
    fetch(`/update_project_stage/${projectId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ stage: newStage })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        }
    });
}

// 项目状态更新
function updateProjectStatus(projectId, newStatus) {
    fetch(`/update_project_status/${projectId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ status: newStatus })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        }
    });
}

// 状态输入框变化处理
function handleStatusChange(input, projectId) {
    const container = input.parentElement;
    const tooltip = container.querySelector('.status-tooltip');
    tooltip.textContent = input.value;
    
    // 显示保存按钮
    const saveBtn = container.querySelector('.save-status-btn');
    saveBtn.style.opacity = '1';
}

// 状态自动保存
function autoSaveStatus(input, projectId) {
    // 如果内容有变化，自动保存
    if (input.value !== input.defaultValue) {
        saveProjectStatus(input, projectId);
    }
}

// 保存状态
function saveStatus(button, projectId) {
    const input = button.previousElementSibling.previousElementSibling;
    saveProjectStatus(input, projectId);
}

// 保存项目状态
function saveProjectStatus(input, projectId) {
    const newStatus = input.value;
    
    fetch(`/update_project_status/${projectId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ 
            status: newStatus,
            add_history: true  // 添加这个标志来记录历史
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            // 输入框的默认值
            input.defaultValue = newStatus;
            
            // 更新tooltip
            const tooltip = input.parentElement.querySelector('.status-tooltip');
            tooltip.textContent = newStatus;
            
            // 隐藏保存按钮
            const saveBtn = input.parentElement.querySelector('.save-status-btn');
            saveBtn.style.opacity = '0';
            
            // 显示保存成功的提示
            showToast('状态已更新');
        } else {
            showToast('保存失败，请重试', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showToast('保存失败，请重试', 'error');
    });
}

// 显示提示信息
function showToast(message, type = 'success') {
    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = message;
    document.body.appendChild(toast);
    
    setTimeout(() => {
        toast.remove();
    }, 2000);
}

// 重新激活项目
function reactivateProject(projectId) {
    const stateSelect = event.target.previousElementSibling;
    const newState = stateSelect.value;
    
    if (confirm(`确定要将此项目重新激活为${newState === 'active' ? '进行中' : '维保中'}状态吗？`)) {
        fetch(`/reactivate_project/${projectId}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ state: newState })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                location.reload();
            } else {
                alert('重新激活项目失败，请重试');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            alert('重新激活项目失败，请重试');
        });
    }
}

// 加载日报
function loadDailyReport() {
    const date = document.getElementById('reportDate').value;
    if (!date) {
        alert('请选择日期');
        return;
    }
    
    fetch(`/get_daily_report/${date}`)
        .then(response => response.json())
        .then(data => {
            const reportContent = document.getElementById('reportContent');
            if (data.success && data.report) {
                reportContent.innerHTML = `<pre>${data.report.content}</pre>`;
            } else {
                reportContent.innerHTML = '<p>该日无工作记录</p>';
            }
        })
        .catch(error => {
            console.error('Error:', error);
            document.getElementById('reportContent').innerHTML = '<p>加载失败，请重试</p>';
        });
}

// 关闭日报弹窗
function closeReportModal() {
    document.getElementById('reportModal').style.display = 'none';
}

// 显示日报弹窗
function showReportModal() {
    const modal = document.getElementById('reportModal');
    const today = new Date().toISOString().split('T')[0];
    document.getElementById('reportDate').value = today;
    modal.style.display = 'block';
    loadDailyReport();  // 自动加载今天的日报
}

// 点击模态框外部关闭
window.onclick = function(event) {
    const modal = document.getElementById('reportModal');
    if (event.target == modal) {
        modal.style.display = 'none';
    }
}

// 导出日报
function exportDailyReport() {
    const date = document.getElementById('exportDate').value;
    if (!date) {
        alert('请选择日期');
        return;
    }
    window.location.href = `/export_daily_report/${date}`;
}

// 导出周报
function exportWeeklyReport() {
    const weekStr = document.getElementById('exportWeek').value;
    if (!weekStr) {
        alert('请选择周');
        return;
    }
    // 解析周字符串 (格式: 2024-W01)
    const [year, weekPart] = weekStr.split('-W');
    if (!year || !weekPart) {
        alert('周格式不正确');
        return;
    }
    window.location.href = `/export_weekly_report/${year}/${weekPart}`;
}

// 导出月报
function exportMonthlyReport() {
    const monthStr = document.getElementById('exportMonth').value;
    if (!monthStr) {
        alert('请选择月份');
        return;
    }
    // 解析月份字符串 (格式: 2024-01)
    const [year, month] = monthStr.split('-');
    if (!year || !month) {
        alert('月份格式不正确');
        return;
    }
    window.location.href = `/export_monthly_report/${year}/${month}`;
}

// 导出日期范围
function exportDateRange() {
    const startDate = document.getElementById('exportStartDate').value;
    const endDate = document.getElementById('exportEndDate').value;
    if (!startDate || !endDate) {
        alert('请选择开始和结束日期');
        return;
    }
    window.location.href = `/export_date_range/${startDate}/${endDate}`;
}

// 显示导出对话框
function showExportDialog() {
    const dropdown = document.getElementById('exportDropdown');
    dropdown.style.display = 'block';
}

// 关闭导出对话框
function closeExportDialog() {
    const dropdown = document.getElementById('exportDropdown');
    dropdown.style.display = 'none';
}

// 完成任务
function completeTask(taskId, btn) {
    const taskElement = document.getElementById(`task-${taskId}`);
    const completionNote = taskElement.querySelector('.completion-note').value;
    
    fetch(`/complete_task/${taskId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ completion_note: completionNote })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            location.reload();
        } else {
            alert('完成任务失败，请重试');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('完成任务失败，请重试');
    });
} 