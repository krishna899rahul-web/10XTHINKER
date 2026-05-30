import os
import uuid
import base64
import requests
import random 
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from google import genai

# LOAD ENVIRONMENT
load_dotenv()

# FLASK APP CONFIG
app = Flask("X10THINK")
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'pixel_secret_key_2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///x10think.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# API CLIENTS SETUP
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDuKAQ3D4DIG3Tpj8WsKDVh4ti0120YURk")
client = genai.Client(api_key=GEMINI_API_KEY)

# DATABASE MODELS
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    points = db.Column(db.Integer, default=20)
    is_admin = db.Column(db.Boolean, default=False)
    images = db.relationship('GeneratedImage', backref='owner', lazy=True)

class GeneratedImage(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    prompt = db.Column(db.Text, nullable=False)
    image_data = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class RechargeCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(30), unique=True, nullable=False)
    point_value = db.Column(db.Integer, nullable=False)
    is_used = db.Column(db.Boolean, default=False)

# ROUTES (Same as yours)
@app.route('/')
def home():
    if 'user_id' in session:
        return redirect(url_for('admin')) if session.get('is_admin') else redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))
        new_user = User(username=username, password=generate_password_hash(password))
        db.session.add(new_user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password, request.form.get('password')):
            session.update({'user_id': user.id, 'username': user.username, 'is_admin': user.is_admin})
            return redirect(url_for('admin' if user.is_admin else 'dashboard'))
        flash('Invalid credentials!', 'danger')
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    images = GeneratedImage.query.filter_by(user_id=user.id).order_by(GeneratedImage.created_at.desc()).all()
    return render_template('dashboard.html', user=user, user_images=images)

# --- VERCEL-SAFE DATABASE INIT ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        # Admin reset logic sirf tabhi chalega jab aap local terminal se run karenge
        old_admin = User.query.filter_by(username='admin').first()
        if old_admin:
            db.session.delete(old_admin)
            db.session.commit()
            
        admin_user = User(
            username='admin',
            password=generate_password_hash('admin786'),
            is_admin=True,
            points=9999
        )
        db.session.add(admin_user)
        db.session.commit()
        print("DATABASE SYNCHRONIZED SUCCESSFULLY")
    
    app.run(debug=True)
