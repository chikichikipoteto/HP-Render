from flask import Flask, send_from_directory, request, jsonify, render_template_string, session
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
import smtplib
from email.mime.text import MIMEText
import random

app = Flask(__name__, static_folder="TAKERU")

# データベース設定
database_url = os.environ.get('DATABASE_URL')
if database_url:
    # PostgreSQLの場合、URLを修正
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # ローカル開発用SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///takesoft.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# データベースモデル
class Contact(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), nullable=False)
    message = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Download(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    file_name = db.Column(db.String(100), nullable=False)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.String(200))
    downloaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(128), nullable=False)

@app.route("/")
def index():
    static_dir = app.static_folder if app.static_folder else "."
    return send_from_directory(static_dir, "index.html")

@app.route("/<path:path>")
def static_files(path):
    static_dir = app.static_folder if app.static_folder else "."
    return send_from_directory(static_dir, path)

@app.route("/api/contact", methods=["POST"])
def submit_contact():
    try:
        data = request.get_json()
        contact = Contact(
            name=data['name'],
            email=data['email'],
            message=data['message']
        )
        db.session.add(contact)
        db.session.commit()

        # --- ここからメール送信処理 ---
        from_addr = "takesoftservice@gmail.com"
        to_addr = "takesoftservice@gmail.com"
        password = os.environ.get('GMAIL_APP_PASSWORD')
        subject = "[TakeSoft] お問い合わせ受信"
        body = f"お名前: {data['name']}\nメール: {data['email']}\n内容:\n{data['message']}"
        msg = MIMEText(body, "plain", "utf-8")
        msg["Subject"] = subject
        msg["From"] = from_addr
        msg["To"] = to_addr
        if password:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(from_addr, password)
                server.send_message(msg)
        # --- ここまでメール送信処理 ---

        return jsonify({"success": True, "message": "お問い合わせを受け付けました"}), 200
    except Exception as e:
        return jsonify({"success": False, "message": "エラーが発生しました"}), 500

@app.route("/api/download", methods=["POST"])
def record_download():
    try:
        data = request.get_json()
        download = Download(
            file_name=data['file_name'],
            ip_address=request.remote_addr,
            user_agent=request.headers.get('User-Agent', '')
        )
        db.session.add(download)
        db.session.commit()
        return jsonify({"success": True}), 200
    except Exception as e:
        return jsonify({"success": False}), 500

@app.route("/api/stats")
def get_stats():
    try:
        contact_count = Contact.query.count()
        download_count = Download.query.count()
        return jsonify({
            "contacts": contact_count,
            "downloads": download_count
        }), 200
    except Exception as e:
        return jsonify({"error": "統計の取得に失敗しました"}), 500

@app.route("/admin")
def admin():
    try:
        contacts = Contact.query.order_by(Contact.created_at.desc()).limit(10).all()
        downloads = Download.query.order_by(Download.downloaded_at.desc()).limit(10).all()
        
        contact_list = []
        for contact in contacts:
            contact_list.append({
                'id': contact.id,
                'name': contact.name,
                'email': contact.email,
                'message': contact.message,
                'created_at': contact.created_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        download_list = []
        for download in downloads:
            download_list.append({
                'id': download.id,
                'file_name': download.file_name,
                'ip_address': download.ip_address,
                'downloaded_at': download.downloaded_at.strftime('%Y-%m-%d %H:%M:%S')
            })
        
        return jsonify({
            'contacts': contact_list,
            'downloads': download_list,
            'total_contacts': Contact.query.count(),
            'total_downloads': Download.query.count()
        }), 200
    except Exception as e:
        return jsonify({"error": "管理データの取得に失敗しました"}), 500

@app.route("/api/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')
    user = User.query.filter_by(email=email, password=password).first()
    if user:
        session['user_id'] = user.id
        return jsonify({"success": True, "message": "ログイン成功"})
    else:
        return jsonify({"success": False, "message": "メールアドレスまたはパスワードが違います"}), 401

@app.route("/api/logout", methods=["POST"])
def logout():
    session.pop('user_id', None)
    return jsonify({"success": True, "message": "ログアウトしました"})

@app.route("/api/login_status")
def login_status():
    user_id = session.get('user_id')
    if user_id:
        user = User.query.get(user_id)
        if user:
            return jsonify({"logged_in": True, "email": user.email})
    return jsonify({"logged_in": False})

@app.route("/api/send_code", methods=["POST"])
def send_code():
    data = request.get_json()
    email = data.get('email')
    if not email or '@' not in email:
        return jsonify({"success": False, "message": "正しいメールアドレスを入力してください"}), 400
    code = str(random.randint(10000, 99999))
    session['auth_email'] = email
    session['auth_code'] = code
    # メール送信
    from_addr = "takesoftservice@gmail.com"
    to_addr = email
    password = os.environ.get('GMAIL_APP_PASSWORD')
    subject = "【TakeSoft】認証コードのお知らせ"
    body = f"ログイン認証コード: {code}\n\nこのコードを画面に入力してください。\n\nTakeSoft"
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = from_addr
    msg["To"] = to_addr
    try:
        if password:
            with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
                server.login(from_addr, password)
                server.send_message(msg)
        else:
            return jsonify({"success": False, "message": "メール送信設定がありません"}), 500
    except Exception as e:
        return jsonify({"success": False, "message": "メール送信に失敗しました"}), 500
    return jsonify({"success": True, "message": "認証コードを送信しました"})

@app.route("/api/verify_code", methods=["POST"])
def verify_code():
    data = request.get_json()
    email = data.get('email')
    code = data.get('code')
    if not email or not code:
        return jsonify({"success": False, "message": "情報が不足しています"}), 400
    if session.get('auth_email') == email and session.get('auth_code') == code:
        session['user_id'] = email  # ログイン状態としてメールアドレスを保存
        session.pop('auth_code', None)
        session.pop('auth_email', None)
        return jsonify({"success": True, "message": "認証成功"})
    else:
        return jsonify({"success": False, "message": "認証コードが違います"}), 401

# データベースの初期化
with app.app_context():
    db.create_all()
    # 仮ユーザーが存在しなければ追加
    if not User.query.filter_by(email="test@example.com").first():
        user = User(email="test@example.com", password="test123")
        db.session.add(user)
        db.session.commit()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000) 