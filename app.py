import os
import uuid
import base64
import requests
import random  # <-- Added for dynamic random suggestions
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv

# GOOGLE GENAI
from google import genai

# =========================
# LOAD ENVIRONMENT
# =========================
load_dotenv()

# =========================
# FLASK APP CONFIG
# =========================
app = Flask("X10THINK")
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'pixel_secret_key_2026')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///x10think.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = os.path.join(os.getcwd(), 'static', 'temp')

# Ensure temp directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

db = SQLAlchemy(app)

# =========================
# API CLIENTS SETUP
# =========================
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "AIzaSyDuKAQ3D4DIG3Tpj8WsKDVh4ti0120YURk")
client = genai.Client(api_key=GEMINI_API_KEY)

# =========================
# DATABASE MODELS
# =========================
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

# =========================
# ROUTES
# =========================
@app.route('/')
def home():
    if 'user_id' in session:
        if session.get('is_admin'):
            return redirect(url_for('admin'))
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            flash('Username already exists!', 'danger')
            return redirect(url_for('register'))

        hashed_password = generate_password_hash(password)
        new_user = User(username=username, password=hashed_password, is_admin=False)
        
        db.session.add(new_user)
        db.session.commit()

        flash('Account created successfully!', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['username'] = user.username
            session['is_admin'] = user.is_admin
            
            if user.is_admin:
                flash('Welcome Admin! Accessing Admin Panel...', 'success')
                return redirect(url_for('admin'))
            else:
                flash('Login successful!', 'success')
                return redirect(url_for('dashboard'))

        flash('Invalid credentials!', 'danger')

    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user = db.session.get(User, session['user_id'])
    user_images = GeneratedImage.query.filter_by(user_id=user.id).order_by(GeneratedImage.created_at.desc()).all()

    # 🌟 DYNAMIC SUGGESTIONS POOL (Har bar alag-alag dikhane ke liye)
    all_suggestions = [
        {"icon": "⚔️", "label": "Cyberpunk Warrior", "text": "Cyberpunk warrior holding a neon sword, realistic look, 8k resolution, cinematic lighting"},
        {"icon": "🐼", "label": "Panda Astronaut", "text": "Cute baby panda astronaut sitting on the moon, hyper-detailed, cinematic lighting"},
        {"icon": "🎮", "label": "Gaming Room", "text": "Hyper-realistic gaming setup room with RGB lights, futuristic PC, 4k resolution"},
        {"icon": "🌳", "label": "Magic Forest", "text": "Mystical ancient tree inside an enchanted glowing forest, 3d render, fantasy style"},
        {"icon": "🚗", "label": "Futuristic Car", "text": "A sleek flying sports car over a cyberpunk neon city, photorealistic, 8k"},
        {"icon": "🦁", "label": "Neon Lion", "text": "A majestic lion made of glowing cosmic neon energy lines, dark background, abstract art"},
        {"icon": "🚀", "label": "Mars City", "text": "A futuristic human colony on Mars with glass domes, sci-fi concept art, sharp focus"},
        {"icon": "🏰", "label": "Floating Castle", "text": "A medieval majestic castle floating on a giant rock in the clouds, anime style, highly detailed"},
        {"icon": "🐱", "label": "Samurai Cat", "text": "An adorable cat dressed in detailed samurai armor, holding a tiny katana, cinematic shot"},
        {"icon": "🧜", "label": "Lost Atlantis", "text": "Underwater ancient city of Atlantis with glowing sea creatures, coral reefs, mystical atmosphere"},
        {"icon": "🦅", "label": "Phoenix Bird", "text": "A majestic phoenix bird rising from golden and blue flames, highly detailed fantasy digital painting"},
        {"icon": "🌌", "label": "Cosmic Portal", "text": "A glowing cosmic portal in the middle of a desert leading to another galaxy, starry sky, 8k"}
    ]
    
    # Har refresh par randomly 4 select karega
    random_suggestions = random.sample(all_suggestions, 4) if len(all_suggestions) >= 4 else all_suggestions

    return render_template('dashboard.html', user=user, user_images=user_images, suggestions=random_suggestions)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if 'user_id' not in session or not session.get('is_admin'):
        return "Access Denied: You do not have Admin privileges.", 403

    if request.method == 'POST':
        points = request.form.get('points')
        if points:
            code = "X10-" + str(uuid.uuid4())[:8].upper()
            new_code = RechargeCode(code=code, point_value=int(points))
            db.session.add(new_code)
            db.session.commit()
            flash(f'Recharge Code {code} Created!', 'success')

    codes = RechargeCode.query.all()
    users = User.query.all()
    return render_template('admin.html', codes=codes, users=users)

@app.route('/generate', methods=['POST'])
def generate():
    if 'user_id' not in session: 
        return redirect(url_for('login'))
        
    user = db.session.get(User, session['user_id'])
    if user.points <= 0:
        flash('Not enough points!', 'danger')
        return redirect(url_for('dashboard'))
        
    raw_prompt = request.form.get('prompt')
    if not raw_prompt: 
        return redirect(url_for('dashboard'))
    
    final_prompt = raw_prompt
    try:
        booster_instruction = (
            f"You are a professional prompt engineering expert for AI images. "
            f"The user wants to generate an image based on: '{raw_prompt}'. "
            f"Expand this into a highly detailed, stunning, cinematic visual description. "
            f"Add professional terms like 'hyper-realistic, photorealistic, 8k resolution, detailed lighting, sharp focus'. "
            f"Give me ONLY the final expanded prompt in plain English text without any markdown or quotes."
        )
        
        gemini_response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=booster_instruction
        )
        if gemini_response and gemini_response.text:
            final_prompt = gemini_response.text.strip()
        
    except Exception as gemini_err:
        print(f"⚠️ Gemini Booster Server Busy: Using raw prompt. Details: {str(gemini_err)}")
        final_prompt = raw_prompt

    try:
        flux_url = f"https://image.pollinations.ai/prompt/{final_prompt}?model=flux&enhance=true&width=1024&height=1024"
        flux_response = requests.get(flux_url)
        
        if flux_response.status_code != 200:
            flash('Generation pipeline busy. Try again.', 'danger')
            return redirect(url_for('dashboard'))
            
        base_image_bytes = flux_response.content
        final_image_data = base64.b64encode(base_image_bytes).decode('utf-8')
        
        new_image = GeneratedImage(prompt=raw_prompt, image_data=final_image_data, user_id=user.id)
        user.points -= 1
        db.session.add(new_image)
        db.session.commit()
        flash('Image Generated Successfully!', 'success')
        
    except Exception as e:
        print(f"Pipeline Exception: {str(e)}")
        flash('Server response timeout. Please try again.', 'danger')
        
    return redirect(url_for('dashboard'))

@app.route('/redeem', methods=['POST'])
def redeem():
    if 'user_id' not in session: return redirect(url_for('login'))
    user = db.session.get(User, session['user_id'])
    input_code = request.form.get('code', '').strip()
    db_code = RechargeCode.query.filter_by(code=input_code, is_used=False).first()
    if db_code:
        user.points += db_code.point_value
        db_code.is_used = True
        db.session.commit()
        flash('Points added!', 'success')
    else:
        flash('Invalid Code!', 'danger')
    return redirect(url_for('dashboard'))

@app.route('/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({"reply": "Please log in first to chat."}), 401

    data = request.get_json()
    user_message = data.get('message', '').strip()

    if not user_message:
        return jsonify({"reply": "Message cannot be empty."})

    try:
        system_instruction = (
            "You are the official AI Assistant of 'X10THINK', a website developed by the user. "
            "On this website, users can generate AI images on the left side of the dashboard using the 'Create New Image' prompt box. "
            "Each image generation costs 1 point. Users can check their balance in the Top Bar and redeem recharge codes (format X10-XXXX) "
            "using the 'Redeem Points' box on the right. Always reply strictly as the X10THINK assistant in a friendly manner. Use Hinglish or English."
        )

        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=user_message,
            config={"system_instruction": system_instruction}
        )
        
        bot_reply = response.text if response.text else "I couldn't process that statement."
        return jsonify({"reply": bot_reply})

    except Exception as e:
        print(f"Gemini API Error details: {str(e)}")
        return jsonify({"reply": "Sorry, real-time communication interface is down right now."})

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('logout'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        
        old_admin = User.query.filter_by(username='admin').first()
        if old_admin:
            GeneratedImage.query.filter_by(user_id=old_admin.id).delete()
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
        print("DATABASE SYNCHRONIZED: LOGS CLEANED WITH DYNAMIC REFRESH OPTIONS")

    app.run(debug=True)
