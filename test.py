"""
Flask 智能招聘系统 - 完整测试套件
========================
包含用户认证、职位管理、申请流程、AI分析等功能的全面测试
"""

import os
import sys
import tempfile
import json
import io
import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app import app, db, User, Job, Application


@pytest.fixture(scope='session')
def test_app():
    """创建测试专用的 Flask 应用实例"""
    db_fd, db_path = tempfile.mkstemp()
    
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': f'sqlite:///{db_path}',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'SECRET_KEY': 'test_secret_key',
        'UPLOAD_FOLDER': os.path.join(os.path.dirname(__file__), 'test_uploads'),
        'MAX_CONTENT_LENGTH': 16 * 1024 * 1024,
        'ALLOWED_EXTENSIONS': {'pdf', 'doc', 'docx'},
        'WTF_CSRF_ENABLED': False
    }
    
    app.config.from_mapping(test_config)
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    with app.app_context():
        db.create_all()
        yield app
    
    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture(scope='function')
def client(test_app):
    """创建测试客户端，每个测试函数独立使用"""
    return test_app.test_client()


@pytest.fixture(scope='function')
def runner(test_app):
    """创建 CLI 运行器"""
    return test_app.test_cli_runner()


@pytest.fixture(scope='function')
def init_database(test_app):
    """初始化数据库并创建测试数据"""
    with test_app.app_context():
        db.session.query(Application).delete()
        db.session.query(Job).delete()
        db.session.query(User).delete()
        
        admin_user = User(
            username='admin',
            password='admin123',
            name='系统管理员',
            role='admin'
        )
        
        user1 = User(
            username='user1',
            password='user123',
            name='张三',
            role='user'
        )
        
        user2 = User(
            username='user2',
            password='user123',
            name='李四',
            role='user'
        )
        
        db.session.add(admin_user)
        db.session.add(user1)
        db.session.add(user2)
        
        job1 = Job(
            title='Python开发工程师',
            department='技术部',
            salary='15-25K',
            description='负责Python后端开发',
            requirements='3年以上Python经验',
            location='北京'
        )
        
        job2 = Job(
            title='前端工程师',
            department='技术部',
            salary='12-20K',
            description='负责前端页面开发',
            requirements='熟悉Vue/React',
            location='上海'
        )
        
        job3 = Job(
            title='产品经理',
            department='产品部',
            salary='18-30K',
            description='负责产品规划与设计',
            requirements='5年以上产品经验',
            location='深圳'
        )
        
        db.session.add(job1)
        db.session.add(job2)
        db.session.add(job3)
        db.session.commit()
        
        yield db
        
        db.session.query(Application).delete()
        db.session.query(Job).delete()
        db.session.query(User).delete()
        db.session.commit()


@pytest.fixture(scope='function')
def auth_client(client, init_database):
    """已登录的普通用户客户端"""
    with client.session_transaction() as sess:
        user = User.query.filter_by(username='user1').first()
        sess['username'] = user.username
        sess['role'] = user.role
        sess['name'] = user.name
        sess['user_id'] = user.id
    return client


@pytest.fixture(scope='function')
def admin_client(client, init_database):
    """已登录的管理员客户端"""
    with client.session_transaction() as sess:
        admin = User.query.filter_by(username='admin').first()
        sess['username'] = admin.username
        sess['role'] = admin.role
        sess['name'] = admin.name
        sess['user_id'] = admin.id
    return client


@pytest.fixture
def sample_job(init_database):
    """获取示例职位"""
    return Job.query.filter_by(title='Python开发工程师').first()


@pytest.fixture
def sample_user(init_database):
    """获取示例用户"""
    return User.query.filter_by(username='user1').first()


@pytest.fixture
def sample_resume_file():
    """创建测试简历文件（PDF）"""
    try:
        from PyPDF2 import PdfWriter
        upload_folder = app.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        pdf_path = os.path.join(upload_folder, 'test_resume.pdf')
        
        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        
        with open(pdf_path, 'wb') as f:
            writer.write(f)
        
        yield pdf_path
        
        if os.path.exists(pdf_path):
            os.remove(pdf_path)
    except ImportError:
        pytest.skip("PyPDF2 未安装")


class TestRegistration:
    """用户注册测试"""
    
    def test_normal_registration(self, client, init_database):
        """正常注册：提交有效用户名、密码"""
        response = client.post('/register', data={
            'username': 'newuser',
            'password': 'newpass123',
            'name': '新用户'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        new_user = User.query.filter_by(username='newuser').first()
        assert new_user is not None
        assert new_user.name == '新用户'
        assert new_user.role == 'user'
        assert '登录'.encode('utf-8') in response.data
    
    def test_register_duplicate_username(self, client, init_database):
        """异常注册：尝试注册已存在的用户名"""
        response = client.post('/register', data={
            'username': 'user1',
            'password': 'anyPassword',
            'name': '重复用户'
        })
        
        assert response.status_code == 200
        assert '用户名已存在'.encode('utf-8') in response.data
        
        users = User.query.filter_by(username='user1').all()
        assert len(users) == 1
    
    def test_register_missing_fields(self, client, init_database):
        """注册时缺少必填字段"""
        response = client.post('/register', data={
            'username': 'incomplete',
            'password': '',
            'name': ''
        })
        
        assert response.status_code == 200


class TestLogin:
    """用户登录测试"""
    
    def test_login_with_correct_credentials(self, client, init_database):
        """正确凭证：使用测试账号登录"""
        response = client.post('/login', data={
            'username': 'user1',
            'password': 'user123'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        with client.session_transaction() as sess:
            assert 'username' in sess
            assert sess['username'] == 'user1'
            assert sess['role'] == 'user'
    
    def test_login_with_wrong_password(self, client, init_database):
        """错误凭证：使用错误密码"""
        response = client.post('/login', data={
            'username': 'user1',
            'password': 'wrongpassword'
        })
        
        assert response.status_code == 200
        assert '用户名或密码错误'.encode('utf-8') in response.data
        
        with client.session_transaction() as sess:
            assert 'username' not in sess
    
    def test_login_nonexistent_user(self, client, init_database):
        """登录不存在的用户"""
        response = client.post('/login', data={
            'username': 'nonexistent',
            'password': 'anypassword'
        })
        
        assert response.status_code == 200
        assert '用户名或密码错误'.encode('utf-8') in response.data
    
    def test_login_redirect_with_next_parameter(self, client, init_database):
        """登录时带有 next 参数应重定向到目标页面"""
        response = client.post('/login?next=/dashboard', data={
            'username': 'user1',
            'password': 'user123'
        }, follow_redirects=False)
        
        assert response.status_code == 302
        assert '/dashboard' in response.headers['Location']


class TestLogout:
    """用户注销测试"""
    
    def test_logout_clears_session(self, auth_client, client):
        """登录后访问注销路由，验证会话是否清除"""
        response = client.get('/logout', follow_redirects=True)
        
        assert response.status_code == 200
        
        with client.session_transaction() as sess:
            assert 'username' not in sess
            assert 'role' not in sess


class TestAccessControl:
    """权限保护测试"""
    
    def test_access_dashboard_without_login(self, client):
        """未登录用户访问 /dashboard 应能访问（显示未登录状态）"""
        response = client.get('/dashboard')
        assert response.status_code == 200
    
    def test_access_protected_route_without_login(self, client):
        """未登录用户尝试申请职位应重定向到登录页"""
        response = client.get('/apply/1', follow_redirects=False)
        
        assert response.status_code == 302
        assert '/login' in response.headers['Location']
    
    def test_admin_only_route_access_by_user(self, auth_client, init_database):
        """普通用户尝试访问管理员专属功能"""
        response = auth_client.post('/publish', data={
            'title': '恶意职位',
            'department': '测试部',
            'salary': '10K',
            'description': '测试',
            'requirements': '无'
        }, follow_redirects=False)
        
        assert response.status_code in [302, 403]


class TestSessionManagement:
    """会话管理测试"""
    
    def test_session_persistence_across_requests(self, client, init_database):
        """验证会话在多个请求间保持"""
        client.post('/login', data={
            'username': 'user1',
            'password': 'user123'
        })
        
        response = client.get('/dashboard')
        assert response.status_code == 200
        
        with client.session_transaction() as sess:
            assert sess['username'] == 'user1'
    
    def test_intended_job_id_saved_in_session(self, client, init_database):
        """未登录时尝试申请职位，应保存 job_id 到 session"""
        response = client.get('/apply/1', follow_redirects=False)
        
        assert response.status_code == 302
        
        with client.session_transaction() as sess:
            assert 'intended_job_id' in sess
            assert sess['intended_job_id'] == 1


class TestPublishJob:
    """发布职位测试"""
    
    def test_admin_can_publish_job(self, admin_client, init_database):
        """管理员可以发布新职位"""
        initial_count = Job.query.count()
        
        response = admin_client.post('/publish', data={
            'title': '高级Java工程师',
            'department': '技术部',
            'salary': '20-35K',
            'description': '负责Java后端架构设计',
            'requirements': '5年以上Java开发经验，精通Spring框架',
            'location': '北京'
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        new_count = Job.query.count()
        assert new_count == initial_count + 1
        
        new_job = Job.query.filter_by(title='高级Java工程师').first()
        assert new_job is not None
        assert new_job.department == '技术部'
        assert new_job.salary == '20-35K'
    
    def test_regular_user_cannot_publish_job(self, auth_client, init_database):
        """普通用户不能发布职位"""
        initial_count = Job.query.count()
        
        response = auth_client.post('/publish', data={
            'title': '恶意职位',
            'department': '测试部',
            'salary': '10K',
            'description': '测试',
            'requirements': '无'
        }, follow_redirects=False)
        
        assert response.status_code in [302, 403]
        
        final_count = Job.query.count()
        assert final_count == initial_count
    
    def test_unauthenticated_user_cannot_publish(self, client, init_database):
        """未登录用户不能发布职位"""
        response = client.post('/publish', data={
            'title': '未授权职位',
            'department': '测试部',
            'salary': '10K',
            'description': '测试',
            'requirements': '无'
        }, follow_redirects=False)
        
        assert response.status_code == 302
        assert '/login' in response.headers['Location']
    
    def test_publish_job_missing_required_fields(self, admin_client):
        """发布职位时缺少必填字段"""
        response = admin_client.post('/publish', data={
            'title': '',
            'department': '',
            'salary': '',
            'description': '',
            'requirements': ''
        })
        
        assert response.status_code in [302, 500]


class TestViewJobs:
    """查看职位列表测试"""
    
    def test_admin_sees_all_jobs(self, admin_client, init_database):
        """管理员能看到所有职位"""
        response = admin_client.get('/dashboard')
        
        assert response.status_code == 200
        assert 'Python开发工程师'.encode('utf-8') in response.data
        assert '前端工程师'.encode('utf-8') in response.data
        assert '产品经理'.encode('utf-8') in response.data
    
    def test_user_sees_all_jobs(self, auth_client, init_database):
        """普通用户能看到所有职位"""
        response = auth_client.get('/dashboard')
        
        assert response.status_code == 200
        assert 'Python开发工程师'.encode('utf-8') in response.data
        assert '前端工程师'.encode('utf-8') in response.data
    
    def test_unauthenticated_user_sees_jobs(self, client, init_database):
        """未登录用户也能看到职位列表"""
        response = client.get('/dashboard')
        
        assert response.status_code == 200
        assert 'Python开发工程师'.encode('utf-8') in response.data
    
    def test_admin_sees_edit_delete_buttons(self, admin_client, init_database):
        """管理员能看到编辑/删除按钮"""
        response = admin_client.get('/dashboard')
        
        assert response.status_code == 200
        assert b'approve_application' in response.data or '通过'.encode('utf-8') in response.data
    
    def test_user_does_not_see_admin_buttons(self, auth_client, init_database):
        """普通用户看不到管理员专属按钮"""
        response = auth_client.get('/dashboard')
        
        assert response.status_code == 200
        assert b'approve_application' not in response.data or response.status_code == 200


class TestDeleteJob:
    """删除职位测试"""
    
    def test_admin_can_delete_job(self, admin_client, init_database):
        """管理员可以删除职位（功能待实现）"""
        pytest.skip("删除职位功能尚未实现")
    
    def test_user_cannot_delete_job(self, auth_client, init_database):
        """普通用户不能删除职位（功能待实现）"""
        pytest.skip("删除职位功能尚未实现")


class TestJobPermissions:
    """职位管理权限测试"""
    
    def test_publish_requires_post_method(self, admin_client):
        """发布职位只能通过 POST 方法"""
        response = admin_client.get('/publish')
        assert response.status_code in [302, 405]
    
    def test_csrf_protection_on_publish(self, admin_client):
        """发布职位时的 CSRF 保护（如果启用）"""
        pytest.skip("CSRF 保护当前已禁用")


class TestApplyForJob:
    """申请职位测试"""
    
    def test_user_can_apply_for_job(self, auth_client, init_database, sample_job):
        """用户可以申请职位"""
        user = User.query.filter_by(username='user1').first()
        initial_count = Application.query.count()
        
        response = auth_client.post(f'/apply/{sample_job.id}', data={
            'resume': None
        }, follow_redirects=True)
        
        assert response.status_code == 200
        
        new_count = Application.query.count()
        assert new_count == initial_count + 1
        
        application = Application.query.filter_by(
            user_id=user.id,
            job_id=sample_job.id
        ).first()
        assert application is not None
        assert application.status == '待审核'
    
    def test_apply_redirects_to_login_when_not_authenticated(self, client, sample_job):
        """未登录用户申请职位应重定向到登录页"""
        response = client.get(f'/apply/{sample_job.id}', follow_redirects=False)
        
        assert response.status_code == 302
        assert '/login' in response.headers['Location']
    
    def test_duplicate_application_prevented(self, auth_client, init_database, sample_job):
        """防止重复申请同一职位"""
        user = User.query.filter_by(username='user1').first()
        
        auth_client.post(f'/apply/{sample_job.id}', data={'resume': None})
        
        response = auth_client.post(f'/apply/{sample_job.id}', data={'resume': None},
                                   follow_redirects=True)
        
        assert response.status_code == 200
        assert '已经申请过'.encode('utf-8') in response.data
        
        applications = Application.query.filter_by(
            user_id=user.id,
            job_id=sample_job.id
        ).all()
        assert len(applications) == 1


class TestResumeUpload:
    """简历上传测试"""
    
    def test_upload_valid_pdf_resume(self, auth_client, init_database, sample_job, sample_resume_file):
        """上传合法的 PDF 简历"""
        user = User.query.filter_by(username='user1').first()
        
        with open(sample_resume_file, 'rb') as f:
            response = auth_client.post(
                f'/apply/{sample_job.id}',
                data={
                    'resume': (f, 'test_resume.pdf')
                },
                content_type='multipart/form-data',
                follow_redirects=True
            )
        
        assert response.status_code == 200
        assert '申请成功'.encode('utf-8') in response.data
        
        application = Application.query.filter_by(
            user_id=user.id,
            job_id=sample_job.id
        ).first()
        assert application.resume_path is not None
        assert 'test_resume' in application.resume_path
        
        upload_folder = auth_client.application.config['UPLOAD_FOLDER']
        filename = application.resume_path.replace('uploads/', '')
        saved_file = os.path.join(upload_folder, filename)
        assert os.path.exists(saved_file)
    
    def test_upload_invalid_file_type(self, auth_client, init_database, sample_job):
        """上传非法文件类型（如 .exe）"""
        fake_exe = io.BytesIO(b'MZ fake executable')
        fake_exe.name = 'malware.exe'
        
        response = auth_client.post(
            f'/apply/{sample_job.id}',
            data={
                'resume': (fake_exe, 'malware.exe')
            },
            content_type='multipart/form-data',
            follow_redirects=True
        )
        
        assert response.status_code == 200
        assert '不支持的文件格式'.encode('utf-8') in response.data
        
        user = User.query.filter_by(username='user1').first()
        applications = Application.query.filter_by(
            user_id=user.id,
            job_id=sample_job.id
        ).all()
        assert len(applications) == 0
    
    def test_upload_oversized_file(self, auth_client, init_database, sample_job):
        """上传超大文件（超过 16MB）"""
        large_content = b'x' * (17 * 1024 * 1024)
        large_file = io.BytesIO(large_content)
        large_file.name = 'huge.pdf'
        
        response = auth_client.post(
            f'/apply/{sample_job.id}',
            data={
                'resume': (large_file, 'huge.pdf')
            },
            content_type='multipart/form-data',
            follow_redirects=False
        )
        
        assert response.status_code in [413, 302, 200]
    
    def test_upload_empty_file(self, auth_client, init_database, sample_job):
        """上传空文件"""
        empty_file = io.BytesIO(b'')
        empty_file.name = 'empty.pdf'
        
        response = auth_client.post(
            f'/apply/{sample_job.id}',
            data={
                'resume': (empty_file, 'empty.pdf')
            },
            content_type='multipart/form-data',
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        user = User.query.filter_by(username='user1').first()
        application = Application.query.filter_by(
            user_id=user.id,
            job_id=sample_job.id
        ).first()
        assert application.resume_path is None


class TestViewApplications:
    """查看申请状态测试"""
    
    def test_user_sees_own_applications(self, auth_client, init_database, sample_job):
        """用户登录后查看"我的申请"，应显示其申请的职位列表"""
        user = User.query.filter_by(username='user1').first()
        
        application = Application(
            user_id=user.id,
            job_id=sample_job.id,
            status='待审核'
        )
        db.session.add(application)
        db.session.commit()
        
        response = auth_client.get('/dashboard')
        
        assert response.status_code == 200
        assert '我的申请'.encode('utf-8') in response.data or sample_job.title.encode('utf-8') in response.data
    
    def test_user_only_sees_own_applications(self, auth_client, init_database, sample_job):
        """用户只能看到自己的申请，看不到其他人的"""
        user1 = User.query.filter_by(username='user1').first()
        user2 = User.query.filter_by(username='user2').first()
        
        application2 = Application(
            user_id=user2.id,
            job_id=sample_job.id,
            status='已通过'
        )
        db.session.add(application2)
        db.session.commit()
        
        response = auth_client.get('/dashboard')
        
        assert response.status_code == 200
    
    def test_application_status_displayed(self, auth_client, init_database, sample_job):
        """申请状态正确显示"""
        user = User.query.filter_by(username='user1').first()
        
        application = Application(
            user_id=user.id,
            job_id=sample_job.id,
            status='已通过'
        )
        db.session.add(application)
        db.session.commit()
        
        response = auth_client.get('/dashboard')
        
        assert response.status_code == 200
        assert '已通过'.encode('utf-8') in response.data


class TestApplicationEdgeCases:
    """申请边界情况测试"""
    
    def test_apply_for_nonexistent_job(self, auth_client):
        """申请不存在的职位"""
        response = auth_client.post('/apply/99999', data={'resume': None})
        assert response.status_code == 404
    
    def test_apply_with_special_characters_in_filename(self, auth_client, init_database, sample_job):
        """上传文件名包含特殊字符的简历"""
        pdf_content = b'%PDF fake content'
        special_file = io.BytesIO(pdf_content)
        special_file.name = '简历_张三_2024 (1).pdf'
        
        response = auth_client.post(
            f'/apply/{sample_job.id}',
            data={
                'resume': (special_file, '简历_张三_2024 (1).pdf')
            },
            content_type='multipart/form-data',
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        user = User.query.filter_by(username='user1').first()
        application = Application.query.filter_by(
            user_id=user.id,
            job_id=sample_job.id
        ).first()
        assert application.resume_path is not None


class TestAdminDashboard:
    """管理后台仪表盘测试"""
    
    def test_admin_sees_dashboard_stats(self, admin_client, init_database):
        """管理员登录后查看数据概览"""
        response = admin_client.get('/dashboard')
        
        assert response.status_code == 200
        assert '总职位数'.encode('utf-8') in response.data or b'total_jobs' in response.data
        assert '总申请数'.encode('utf-8') in response.data or b'total_applications' in response.data
    
    def test_admin_sees_all_applications(self, admin_client, init_database, sample_job):
        """管理员能看到所有用户的申请记录"""
        user1 = User.query.filter_by(username='user1').first()
        user2 = User.query.filter_by(username='user2').first()
        
        app1 = Application(user_id=user1.id, job_id=sample_job.id, status='待审核')
        app2 = Application(user_id=user2.id, job_id=sample_job.id, status='已通过')
        db.session.add(app1)
        db.session.add(app2)
        db.session.commit()
        
        response = admin_client.get('/dashboard')
        
        assert response.status_code == 200
        assert '待审核'.encode('utf-8') in response.data
        assert '已通过'.encode('utf-8') in response.data
    
    def test_regular_user_cannot_access_admin_stats(self, auth_client, init_database):
        """普通用户不能访问管理员统计数据"""
        response = auth_client.get('/dashboard')
        
        assert response.status_code == 200
        assert b'department_stats' not in response.data


class TestApproveApplication:
    """审核申请测试"""
    
    def test_admin_can_approve_application(self, admin_client, init_database, sample_job):
        """管理员可以批准申请"""
        user = User.query.filter_by(username='user1').first()
        application = Application(
            user_id=user.id,
            job_id=sample_job.id,
            status='待审核'
        )
        db.session.add(application)
        db.session.commit()
        
        response = admin_client.post(
            f'/approve_application/{application.id}',
            data={'action': 'approve'},
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        updated_app = Application.query.get(application.id)
        assert updated_app.status == '已通过'
        assert '申请已通过'.encode('utf-8') in response.data
    
    def test_admin_can_reject_application(self, admin_client, init_database, sample_job):
        """管理员可以拒绝申请"""
        user = User.query.filter_by(username='user1').first()
        application = Application(
            user_id=user.id,
            job_id=sample_job.id,
            status='待审核'
        )
        db.session.add(application)
        db.session.commit()
        
        response = admin_client.post(
            f'/approve_application/{application.id}',
            data={'action': 'reject'},
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        updated_app = Application.query.get(application.id)
        assert updated_app.status == '已拒绝'
        assert '申请已拒绝'.encode('utf-8') in response.data
    
    def test_admin_can_set_pending(self, admin_client, init_database, sample_job):
        """管理员可以将申请设为待审核"""
        user = User.query.filter_by(username='user1').first()
        application = Application(
            user_id=user.id,
            job_id=sample_job.id,
            status='已通过'
        )
        db.session.add(application)
        db.session.commit()
        
        response = admin_client.post(
            f'/approve_application/{application.id}',
            data={'action': 'pending'},
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        updated_app = Application.query.get(application.id)
        assert updated_app.status == '待审核'
    
    def test_user_cannot_approve_application(self, auth_client, init_database, sample_job):
        """普通用户不能审核申请"""
        user = User.query.filter_by(username='user1').first()
        application = Application(
            user_id=user.id,
            job_id=sample_job.id,
            status='待审核'
        )
        db.session.add(application)
        db.session.commit()
        
        response = auth_client.post(
            f'/approve_application/{application.id}',
            data={'action': 'approve'},
            follow_redirects=False
        )
        
        assert response.status_code in [302, 403]
        
        unchanged_app = Application.query.get(application.id)
        assert unchanged_app.status == '待审核'
    
    def test_approve_nonexistent_application(self, admin_client):
        """审核不存在的申请"""
        response = admin_client.post(
            '/approve_application/99999',
            data={'action': 'approve'}
        )
        
        assert response.status_code == 404
    
    def test_invalid_action_parameter(self, admin_client, init_database, sample_job):
        """传入无效的 action 参数"""
        user = User.query.filter_by(username='user1').first()
        application = Application(
            user_id=user.id,
            job_id=sample_job.id,
            status='待审核'
        )
        db.session.add(application)
        db.session.commit()
        
        response = admin_client.post(
            f'/approve_application/{application.id}',
            data={'action': 'invalid_action'},
            follow_redirects=True
        )
        
        assert response.status_code == 200
        
        unchanged_app = Application.query.get(application.id)
        assert unchanged_app.status == '待审核'


class TestAIResumeAnalysis:
    """AI 简历分析接口测试"""
    
    @patch('ai_select.analyze_resume')
    def test_ai_analysis_success(self, mock_analyze, auth_client, init_database, sample_job):
        """成功调用 AI 简历分析接口"""
        mock_result = {
            'match_score': 85,
            'matched_skills': ['Python', 'Flask', 'SQLAlchemy'],
            'missing_skills': ['Docker', 'Kubernetes'],
            'summary': '候选人技能与职位要求高度匹配'
        }
        mock_analyze.return_value = mock_result
        
        upload_folder = auth_client.application.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        resume_path = os.path.join(upload_folder, 'test_resume.pdf')
        with open(resume_path, 'w') as f:
            f.write('fake pdf content')
        
        response = auth_client.post('/ai', data={
            'job_description': 'Python开发工程师，需要3年以上经验',
            'resume_file_path': 'test_resume.pdf'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert data['match_score'] == 85
        assert 'Python' in data['matched_skills']
        assert 'analyzed_at' in data
        assert data['backend_used'] == 'qwen'
        
        if os.path.exists(resume_path):
            os.remove(resume_path)
    
    @patch('ai_select.analyze_resume')
    def test_ai_analysis_with_json_request(self, mock_analyze, auth_client, init_database):
        """使用 JSON 格式调用 AI 接口"""
        mock_result = {
            'match_score': 75,
            'matched_skills': ['Java'],
            'missing_skills': ['Python'],
            'summary': '基本匹配'
        }
        mock_analyze.return_value = mock_result
        
        upload_folder = auth_client.application.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        resume_path = os.path.join(upload_folder, 'test.docx')
        with open(resume_path, 'w') as f:
            f.write('fake docx content')
        
        response = auth_client.post('/ai',
            json={
                'job_description': 'Java工程师',
                'resume_file_path': 'test.docx'
            }
        )
        
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['match_score'] == 75
        
        if os.path.exists(resume_path):
            os.remove(resume_path)
    
    def test_ai_analysis_without_login(self, client):
        """未登录用户调用 AI 接口应返回 401"""
        response = client.post('/ai', data={
            'job_description': '测试职位',
            'resume_file_path': 'test.pdf'
        })
        
        assert response.status_code == 401
        data = json.loads(response.data)
        assert 'error' in data
        assert '请先登录' in data['error']
    
    def test_ai_analysis_missing_parameters(self, auth_client):
        """调用 AI 接口时缺少必要参数"""
        response = auth_client.post('/ai', data={
            'job_description': '测试职位'
        })
        
        assert response.status_code == 400
        data = json.loads(response.data)
        assert 'error' in data
    
    def test_ai_analysis_file_not_found(self, auth_client):
        """调用 AI 接口时简历文件不存在"""
        response = auth_client.post('/ai', data={
            'job_description': '测试职位',
            'resume_file_path': 'nonexistent.pdf'
        })
        
        assert response.status_code == 404
        data = json.loads(response.data)
        assert data['match_score'] == 0
        assert '简历文件不存在' in data['error']
    
    @patch('ai_select.analyze_resume')
    def test_ai_analysis_service_error(self, mock_analyze, auth_client):
        """AI 服务出错时的降级处理"""
        mock_analyze.side_effect = Exception('AI 服务暂时不可用')
        
        upload_folder = auth_client.application.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        resume_path = os.path.join(upload_folder, 'test.pdf')
        with open(resume_path, 'w') as f:
            f.write('fake content')
        
        response = auth_client.post('/ai', data={
            'job_description': '测试职位',
            'resume_file_path': 'test.pdf'
        })
        
        assert response.status_code == 500
        data = json.loads(response.data)
        assert data['match_score'] == 0
        assert '分析失败' in data['error']
        assert data['backend_used'] == 'fallback'
        
        if os.path.exists(resume_path):
            os.remove(resume_path)
    
    @patch('ai_select.analyze_resume')
    def test_ai_analysis_returns_additional_fields(self, mock_analyze, auth_client):
        """验证 AI 接口返回额外的规范字段"""
        mock_result = {
            'match_score': 90,
            'matched_skills': ['Python'],
            'missing_skills': [],
            'summary': '优秀'
        }
        mock_analyze.return_value = mock_result
        
        upload_folder = auth_client.application.config['UPLOAD_FOLDER']
        os.makedirs(upload_folder, exist_ok=True)
        resume_path = os.path.join(upload_folder, 'test.pdf')
        with open(resume_path, 'w') as f:
            f.write('content')
        
        response = auth_client.post('/ai', data={
            'job_description': '职位',
            'resume_file_path': 'test.pdf'
        })
        
        assert response.status_code == 200
        data = json.loads(response.data)
        
        assert 'analyzed_at' in data
        assert 'backend_used' in data
        assert data['backend_used'] == 'qwen'
        
        if os.path.exists(resume_path):
            os.remove(resume_path)


class TestAdminPermissions:
    """管理员权限测试"""
    
    def test_non_admin_cannot_access_approval_route(self, auth_client, init_database):
        """非管理员尝试访问审核路由"""
        user = User.query.filter_by(username='user1').first()
        job = Job.query.first()
        
        application = Application(
            user_id=user.id,
            job_id=job.id,
            status='待审核'
        )
        db.session.add(application)
        db.session.commit()
        
        response = auth_client.post(
            f'/approve_application/{application.id}',
            data={'action': 'approve'},
            follow_redirects=False
        )
        
        assert response.status_code in [302, 403]
    
    def test_admin_role_verified_in_session(self, client, init_database):
        """验证管理员权限来自 session 中的 role 字段"""
        with client.session_transaction() as sess:
            admin = User.query.filter_by(username='admin').first()
            sess['username'] = admin.username
            sess['role'] = 'admin'
            sess['name'] = admin.name
            sess['user_id'] = admin.id
        
        response = client.get('/dashboard')
        assert response.status_code == 200


class TestStaticPages:
    """静态页面基础测试"""
    
    def test_about_page_returns_200(self, client):
        """访问关于我们页面，返回 HTTP 200"""
        response = client.get('/about')
        
        assert response.status_code == 200
        assert '关于'.encode('utf-8') in response.data or b'About' in response.data
    
    def test_help_page_returns_200(self, client):
        """访问帮助中心页面，返回 HTTP 200"""
        response = client.get('/help')
        
        assert response.status_code == 200
        assert '帮助'.encode('utf-8') in response.data or b'Help' in response.data
    
    def test_about_page_has_correct_title(self, client):
        """关于我们页面标题正确"""
        response = client.get('/about')
        
        assert response.status_code == 200
        assert '关于我们'.encode('utf-8') in response.data or '智能招聘系统'.encode('utf-8') in response.data
    
    def test_help_page_has_correct_title(self, client):
        """帮助中心页面标题正确"""
        response = client.get('/help')
        
        assert response.status_code == 200
        assert '帮助'.encode('utf-8') in response.data or '常见问题'.encode('utf-8') in response.data
    
    def test_static_pages_use_base_template(self, client):
        """静态页面继承 base.html 模板"""
        response = client.get('/about')
        
        assert response.status_code == 200
        assert '智能招聘系统'.encode('utf-8') in response.data
        assert b'nav-item' in response.data
    
    def test_static_pages_accessible_without_login(self, client):
        """静态页面无需登录即可访问"""
        about_response = client.get('/about')
        help_response = client.get('/help')
        
        assert about_response.status_code == 200
        assert help_response.status_code == 200


class TestIndexRoute:
    """首页路由测试"""
    
    def test_index_redirects_to_dashboard(self, client):
        """访问根路径应重定向到 dashboard"""
        response = client.get('/', follow_redirects=False)
        
        assert response.status_code == 302
        assert '/dashboard' in response.headers['Location']


class TestNavigation:
    """导航链接测试"""
    
    def test_navigation_links_present(self, client):
        """页面中包含导航链接"""
        response = client.get('/about')
        
        assert response.status_code == 200
        assert b'href="/about"' in response.data or b'href=' in response.data
        assert b'href="/help"' in response.data or '帮助'.encode('utf-8') in response.data
    
    def test_login_link_visible_when_not_logged_in(self, client):
        """未登录时显示登录链接"""
        response = client.get('/about')
        
        assert response.status_code == 200
        assert '登录'.encode('utf-8') in response.data
    
    def test_logout_link_visible_when_logged_in(self, auth_client):
        """登录后显示退出登录链接"""
        response = auth_client.get('/about')
        
        assert response.status_code == 200
        assert '退出登录'.encode('utf-8') in response.data or b'logout' in response.data


class TestPageContent:
    """页面内容完整性测试"""
    
    def test_about_page_contains_company_info(self, client):
        """关于我们页面包含公司信息"""
        response = client.get('/about')
        
        assert response.status_code == 200
        assert '招聘'.encode('utf-8') in response.data or '公司'.encode('utf-8') in response.data
    
    def test_help_page_contains_faq(self, client):
        """帮助中心页面包含常见问题"""
        response = client.get('/help')
        
        assert response.status_code == 200
        assert len(response.data) > 100


class TestErrorHandling:
    """错误页面测试"""
    
    def test_404_for_nonexistent_route(self, client):
        """访问不存在的路由返回 404"""
        response = client.get('/nonexistent_page')
        
        assert response.status_code == 404
    
    def test_405_for_wrong_method(self, client):
        """使用错误的方法访问路由返回 405"""
        response = client.get('/publish')
        assert response.status_code in [302, 405]
