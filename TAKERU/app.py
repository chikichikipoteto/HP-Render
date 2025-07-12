from flask import Flask, send_from_directory, request, jsonify, render_template_string
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os

app = Flask(__name__, static_folder="TAKERU")
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

@app.route("/")
def index():
    return send_from_directory(app.static_folder, "index.html")

@app.route("/<path:path>")
def static_files(path):
    return send_from_directory(app.static_folder, path)

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

# データベースの初期化
with app.app_context():
    db.create_all()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000) 