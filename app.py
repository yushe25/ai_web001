from flask import render_template, request, redirect, url_for, session, flash, jsonify
from collections import Counter
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
import os
import logging
from datetime import datetime
from ai_select import analyze_resume

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# 配置MySQL数据库连接
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:xxxx@localhost/recruitment_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')  #存储文件上传目录路径
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 最大上传16MB
app.config['ALLOWED_EXTENSIONS'] = {'pdf', 'doc', 'docx'}

db = SQLAlchemy(app)

# 确保上传目录存在
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


# 数据库模型定义
class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password = db.Column(db.String(120), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    applications = db.relationship('Application', backref='applicant', lazy=True)
    
    def __repr__(self):
        return f'<User {self.username}>'


class Job(db.Model):
    __tablename__ = 'jobs'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    department = db.Column(db.String(100), nullable=False)
    salary = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    requirements = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(100), default='未设置')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    applications = db.relationship('Application', backref='job_posting', lazy=True)
    
    def __repr__(self):
        return f'<Job {self.title}>'


class Application(db.Model):
    __tablename__ = 'applications'
    
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    job_id = db.Column(db.Integer, db.ForeignKey('jobs.id'), nullable=False, index=True)
    resume_path = db.Column(db.String(500), nullable=True)
    status = db.Column(db.String(20), nullable=False, default='待审核')
    applied_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<Application {self.id}>'


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']


def init_db():
    """初始化数据库并创建默认管理员账号"""
    with app.app_context():
        db.create_all()
        
        # 检查是否已有管理员账号
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            admin_user = User(
                username='admin',
                password='admin123',
                name='系统管理员',
                role='admin'
            )
            db.session.add(admin_user)
            
            # 添加示例用户
            user1 = User(username='user1', password='user123', name='张三', role='user')
            user2 = User(username='user2', password='user123', name='李四', role='user')
            db.session.add(user1)
            db.session.add(user2)
            
            # 添加示例职位
            sample_jobs = [
                Job(title='Python开发工程师', department='技术部', salary='15-25K',
                    description='负责Python后端开发', requirements='3年以上Python经验', location='北京'),
                Job(title='前端工程师', department='技术部', salary='12-20K',
                    description='负责前端页面开发', requirements='熟悉Vue/React', location='上海'),
                Job(title='产品经理', department='产品部', salary='18-30K',
                    description='负责产品规划与设计', requirements='5年以上产品经验', location='深圳')
            ]
            for job in sample_jobs:
                db.session.add(job)
            
            db.session.commit()


@app.route('/')
def index():
    return redirect(url_for('dashboard'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        next_page = request.args.get('next')

        user = User.query.filter_by(username=username).first()
        
        if user and user.password == password:
            session['username'] = username
            session['role'] = user.role
            session['name'] = user.name
            session['user_id'] = user.id
            flash('登录成功！', 'success')
            
            # 优先使用next参数，其次检查session中保存的原始意图
            if next_page:
                return redirect(next_page)
            elif 'intended_job_id' in session:
                job_id = session.pop('intended_job_id')
                return redirect(url_for('apply_job', job_id=job_id))
            else:
                return redirect(url_for('dashboard'))
        else:
            flash('用户名或密码错误！', 'error')

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        name = request.form.get('name')

        # 检查用户名是否已存在
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('用户名已存在！', 'error')
        else:
            new_user = User(username=username, password=password, name=name, role='user')
            db.session.add(new_user)
            db.session.commit()
            flash('注册成功，请登录！', 'success')
            return redirect(url_for('login'))

    return render_template('register.html')


@app.route('/dashboard')
def dashboard():
    username = session.get('username')
    role = session.get('role')

    if role == 'admin':
        total_jobs = Job.query.count()
        total_applications = Application.query.count()
        
        # 获取每个职位的申请数量
        job_application_count = db.session.query(
            Job.title, 
            db.func.count(Application.id).label('count')
        ).outerjoin(Application, Job.id == Application.job_id).group_by(Job.id).all()
        
        job_app_dict = dict(job_application_count)
        
        # 获取部门统计信息
        all_jobs = Job.query.all()
        department_stats = {}
        for job in all_jobs:
            dept = job.department
            if dept not in department_stats:
                department_stats[dept] = {'total': 0, 'applications': 0}
            department_stats[dept]['total'] += 1
        
        # 统计各部门申请数
        dept_applications = db.session.query(
            Job.department,
            db.func.count(Application.id).label('count')
        ).join(Application, Job.id == Application.job_id).group_by(Job.department).all()
        
        for dept, count in dept_applications:
            if dept in department_stats:
                department_stats[dept]['applications'] = count
        
        # 获取状态统计
        status_stats_query = db.session.query(
            Application.status,
            db.func.count(Application.id).label('count')
        ).group_by(Application.status).all()
        
        status_stats = dict(status_stats_query)
        
        # 获取所有职位和申请记录
        jobs = Job.query.order_by(Job.created_at.desc()).all()
        applications = Application.query.order_by(Application.applied_at.desc()).all()
        
        return render_template('admin_dashboard.html', 
                             jobs=jobs, 
                             applications=applications,
                             total_jobs=total_jobs,
                             total_applications=total_applications,
                             job_application_count=job_app_dict,
                             department_stats=department_stats,
                             status_stats=status_stats)
    else:
        user = User.query.filter_by(username=username).first()
        user_applications = []
        jobs = Job.query.order_by(Job.created_at.desc()).all()
        
        if user:
            user_applications = Application.query.filter_by(user_id=user.id).all()
        
        return render_template('user_dashboard.html', jobs=jobs, applications=user_applications)


@app.route('/apply/<int:job_id>', methods=['GET', 'POST'])
def apply_job(job_id):
    # 检查用户是否登录
    if 'username' not in session:
        flash('请先登录后再申请职位！', 'warning')
        # 保存用户想要申请的职位ID，登录后自动跳转
        session['intended_job_id'] = job_id
        return redirect(url_for('login', next=url_for('apply_job', job_id=job_id)))

    job = Job.query.get_or_404(job_id)
    user = User.query.filter_by(username=session['username']).first()
    
    if not user:
        flash('用户不存在，请重新登录！', 'error')
        return redirect(url_for('login'))
    
    # 检查是否已经申请过该职位
    already_applied = Application.query.filter_by(
        user_id=user.id, 
        job_id=job_id
    ).first()
    
    if already_applied:
        flash('您已经申请过这个职位了！', 'warning')
        return redirect(url_for('dashboard'))
    
    # 处理简历上传
    resume_path = None
    if request.method == 'POST' and 'resume' in request.files:
        file = request.files['resume']
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            # 添加时间戳避免文件名冲突
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"{timestamp}_{filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            resume_path = f"uploads/{filename}"
        elif file and file.filename != '':
            flash('不支持的文件格式！请上传PDF或Word文档。', 'error')
            return redirect(url_for('dashboard'))
    
    # 创建申请记录
    application = Application(
        user_id=user.id,
        job_id=job_id,
        resume_path=resume_path,
        status='待审核'
    )
    db.session.add(application)
    db.session.commit()
    
    flash('申请成功！等待管理员审核。', 'success')
    return redirect(url_for('dashboard'))


@app.route('/publish', methods=['POST'])
def publish_job():
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    title = request.form.get('title')
    department = request.form.get('department')
    salary = request.form.get('salary')
    description = request.form.get('description')
    requirements = request.form.get('requirements')
    location = request.form.get('location', '未设置')

    new_job = Job(
        title=title,
        department=department,
        salary=salary,
        description=description,
        requirements=requirements,
        location=location
    )
    db.session.add(new_job)
    db.session.commit()
    flash('职位发布成功！', 'success')

    return redirect(url_for('dashboard'))


@app.route('/approve_application/<int:application_id>', methods=['POST'])
def approve_application(application_id):
    if 'username' not in session or session['role'] != 'admin':
        return redirect(url_for('login'))

    action = request.form.get('action')
    
    application = Application.query.get_or_404(application_id)
    
    if action == 'approve':
        application.status = '已通过'
        flash('申请已通过！', 'success')
    elif action == 'reject':
        application.status = '已拒绝'
        flash('申请已拒绝！', 'success')
    elif action == 'pending':
        application.status = '待审核'
        flash('申请已设为待审核！', 'success')
    
    db.session.commit()

    return redirect(url_for('dashboard'))


@app.route('/logout')
def logout():
    session.clear()
    flash('已退出登录！', 'success')
    return redirect(url_for('dashboard'))


@app.route('/about')
def about():
    """关于我们页面"""
    return render_template('about.html')


@app.route('/help')
def help():
    """帮助中心页面"""
    return render_template('help.html')


@app.route('/ai', methods=['POST'])
def ai():
    """AI 简历分析 API"""
    # 检查用户是否登录
    if 'username' not in session:
        return jsonify({'error': '请先登录'}), 401
    
    try:
        # 获取请求数据（支持表单和 JSON）
        job_description = request.form.get('job_description') or (request.json.get('job_description') if request.is_json else None)
        resume_file_path = request.form.get('resume_file_path') or (request.json.get('resume_file_path') if request.is_json else None)
        
        if not job_description or not resume_file_path:
            return jsonify({'error': '缺少职位描述或简历文件路径'}), 400
        
        # 将相对路径转换为绝对路径
        if not os.path.isabs(resume_file_path):
            resume_file_path = os.path.join(app.config['UPLOAD_FOLDER'], os.path.basename(resume_file_path))
        
        # 检查文件是否存在
        if not os.path.exists(resume_file_path):
            return jsonify({
                'error': '简历文件不存在',
                'message': f'找不到文件: {resume_file_path}',
                'match_score': 0,
                'matched_skills': [],
                'missing_skills': [],
                'summary': '简历文件不存在，请重新上传',
                'analyzed_at': datetime.now().isoformat(),
                'backend_used': 'fallback'
            }), 404
        
        # 调用 AI 分析函数
        result = analyze_resume(job_description, resume_file_path)
        
        # 添加额外字段以符合规范
        result['analyzed_at'] = datetime.now().isoformat()
        result['backend_used'] = 'qwen'
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"API 调用失败: {str(e)}")
        return jsonify({
            'error': '分析失败',
            'message': str(e),
            'match_score': 0,
            'matched_skills': [],
            'missing_skills': [],
            'summary': '系统错误，请稍后重试',
            'analyzed_at': datetime.now().isoformat(),
            'backend_used': 'fallback'
        }), 500


if __name__ == '__main__':
    init_db()
    app.run(debug=True)