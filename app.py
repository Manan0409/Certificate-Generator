import os
import io
import uuid
import smtplib
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from flask import Flask, render_template, request, redirect, url_for, flash, send_file, jsonify, session
from flask_mail import Mail, Message
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
from matplotlib import font_manager
from functools import lru_cache
# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

app.secret_key = os.getenv('SECRET_KEY', 'development-secret-key')
app.config['SERVER_NAME'] = os.getenv('SERVER_NAME', 'localhost:5000')

# With this:
if os.getenv('FLASK_ENV') == 'production':
    # For production environment (Render.com)
    app.config['PREFERRED_URL_SCHEME'] = 'https'
else:
    # For local development
    app.config['PREFERRED_URL_SCHEME'] = 'http'

# Configure Flask-Mail
app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.getenv('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')
app.config['MAIL_USE_SSL'] = False  # Add this line explicitly
mail = Mail(app)

# Configure upload folder
UPLOAD_FOLDER = 'uploads'
CERTIFICATE_FOLDER = 'certificates'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'xlsx', 'xls', 'ttf', 'otf'}

# Add this after ALLOWED_EXTENSIONS definition
PREDEFINED_FONTS = [
    ('arial', 'Arial'),
    ('arialbd', 'Arial Bold'),
    ('times', 'Times New Roman'),
    ('timesbd', 'Times New Roman Bold'),
    ('verdana', 'Verdana'),
    ('verdanab', 'Verdana Bold'),
    ('comic', 'Comic Sans MS'),
    ('comicbd', 'Comic Sans MS Bold'),
]


# Create necessary directories
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(CERTIFICATE_FOLDER, exist_ok=True)
os.makedirs(os.path.join(UPLOAD_FOLDER, 'fonts'), exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CERTIFICATE_FOLDER'] = CERTIFICATE_FOLDER

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Certificate generation function
def generate_certificate(template_path, output_path, name, font_path, text_position, font_size, text_color="#444444"):
    try:
        # Open the certificate template image
        template = Image.open(template_path)
        
        # Prepare drawing object
        draw = ImageDraw.Draw(template)
        
        # Define font
        font = ImageFont.truetype(font_path, font_size)
        
        # Add the name to the certificate template
        draw.text(text_position, name, font=font, fill=text_color)
        
        # Save the new certificate image
        template.save(output_path)
        print(f"Certificate saved to {output_path}")
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

# Generate preview image
def generate_preview(template_path, name, font_path, text_position, font_size, text_color="#444444"):
    try:
        # Open the certificate template image
        template = Image.open(template_path)
        
        # Resize for preview (smaller image for faster transfer)
        preview_width = 800  # Adjust this value as needed
        ratio = preview_width / template.width
        preview_height = int(template.height * ratio)
        template = template.resize((preview_width, preview_height))
        
        # Adjust text position based on resize ratio
        adjusted_position = (int(text_position[0] * ratio), int(text_position[1] * ratio))
        
        # Prepare drawing object
        draw = ImageDraw.Draw(template)
        
        # Define font with adjusted size
        adjusted_font_size = int(font_size * ratio)
        font = ImageFont.truetype(font_path, adjusted_font_size)
        
        # Add the name to the certificate template
        draw.text(adjusted_position, name, font=font, fill=text_color)
        
        # Save to BytesIO object with compression
        img_io = io.BytesIO()
        template.save(img_io, 'PNG', optimize=True, quality=85)
        img_io.seek(0)
        return img_io
    except Exception as e:
        print(f"Error generating preview: {e}")
        return None

# Batch generate certificates and return list of generated certificate paths
def batch_generate_certificates(template_path, excel_file, output_dir, font_path, text_position, font_size, text_color="#444444"):
    certificate_paths = []
    email_data = []
    
    # Load names from the Excel file
    try:
        data = pd.read_excel(excel_file)
        
        # Validate required columns
        if 'Name' not in data.columns or 'Email' not in data.columns:
            raise ValueError("Excel file must contain 'Name' and 'Email' columns")
        
        # Generate certificates for each name
        for index, row in data.iterrows():
            name = row['Name']
            email = row['Email']
            
            # Generate a unique ID for this certificate
            certificate_id = str(uuid.uuid4())
            
            # Create filename with the unique ID
            filename = f"{secure_filename(name)}_{certificate_id}.png"
            output_path = os.path.join(output_dir, filename)
            
            # Generate the certificate
            success = generate_certificate(
                template_path, 
                output_path, 
                name, 
                font_path, 
                text_position, 
                font_size,
                text_color
            )
            
            if success:
                certificate_paths.append(output_path)
                email_data.append({
                    'name': name,
                    'email': email,
                    'certificate_path': output_path,
                    'certificate_id': certificate_id
                })
    
    except Exception as e:
        print(f"Error in batch generation: {e}")
        return [], []

    return certificate_paths, email_data

# Send email with certificate link
def send_certificate_email(recipient_data, event_name="Fundamental of Web Development"):
    try:
        name = recipient_data['name']
        email = recipient_data['email']
        certificate_id = recipient_data['certificate_id']
        
        # Create verification link with absolute URL
        if os.getenv('RENDER_EXTERNAL_URL'):
            # When on Render
            verification_link = f"{os.getenv('RENDER_EXTERNAL_URL')}/view_certificate/{certificate_id}"
        else:
            # Local development
            verification_link = url_for('view_certificate', certificate_id=certificate_id, _external=True)
        
        # Create email
        msg = Message(
            subject=f"Your Certificate for {event_name}",
            recipients=[email]
        )
        
        # Email HTML content
        msg.html = render_template(
            'email_template.html',
            name=name,
            event_name=event_name,
            verification_link=verification_link
        )
        
        # Send the email
        mail.send(msg)
        print(f"Email sent to {email}")
        return True
    
    except Exception as e:
        print(f"Error sending email to {email}: {e}")
        return False

# Add this new function
def get_system_font_path(font_name):
    try:
        font_path = font_manager.findfont(font_name)
        return font_path
    except:
        return None

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'template' not in request.files or 'excel_file' not in request.files:
        flash('Missing template or excel file')
        return redirect(request.url)
    
    template_file = request.files['template']
    excel_file = request.files['excel_file']
    font_file = request.files.get('font_file')  # Use get() to handle missing file
    predefined_font = request.form.get('predefined_font')
    
    # Check if template and excel files are selected
    if template_file.filename == '' or excel_file.filename == '':
        flash('No selected template or excel file')
        return redirect(request.url)
    
    # Check template and excel file extensions
    if not (allowed_file(template_file.filename) and allowed_file(excel_file.filename)):
        flash('Invalid template or excel file type')
        return redirect(request.url)
    
    # Save template and excel files
    template_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(template_file.filename))
    excel_path = os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(excel_file.filename))
    
    template_file.save(template_path)
    excel_file.save(excel_path)
    
    # Handle font selection (either predefined or uploaded)
    font_path = None
    
    if predefined_font and predefined_font.strip():
        # Use predefined font
        font_path = get_system_font_path(predefined_font)
        if not font_path:
            flash('Selected predefined font not found')
            return redirect(request.url)
    elif font_file and font_file.filename:
        # Use uploaded font file
        if not allowed_file(font_file.filename):
            flash('Invalid font file type')
            return redirect(request.url)
        
        font_path = os.path.join(app.config['UPLOAD_FOLDER'], 'fonts', secure_filename(font_file.filename))
        font_file.save(font_path)
    else:
        # No font selected
        flash('Please select a font file or choose a predefined font')
        return redirect(request.url)
    
    # Store paths in session
    session['template_path'] = template_path
    session['excel_path'] = excel_path
    session['font_path'] = font_path
    
    # Default text position and font size
    session['text_position_x'] = 760
    session['text_position_y'] = 538
    session['font_size'] = 53
    session['text_color'] = "#444444"
    
    return redirect(url_for('adjust'))

@app.route('/adjust')
def adjust():
    # Check if required session variables exist
    if not all(key in session for key in ['template_path', 'excel_path', 'font_path']):
        flash('Missing required files. Please upload again.')
        return redirect(url_for('index'))
    
    # Get preview data
    data = pd.read_excel(session['excel_path'])
    if 'Name' not in data.columns:
        flash('Excel file must contain a "Name" column')
        return redirect(url_for('index'))
    
    # Get the first name for preview
    preview_name = data['Name'].iloc[0] if not data.empty else "Sample Name"
    
    return render_template(
        'adjust.html', 
        preview_name=preview_name,
        text_position_x=session.get('text_position_x', 760),
        text_position_y=session.get('text_position_y', 538),
        font_size=session.get('font_size', 53),
        text_color=session.get('text_color', "#444444")
    )

@lru_cache(maxsize=32)
def cached_preview(template_path, name, x, y, font_size, font_path, text_color):
    text_position = (x, y)
    return generate_preview(
        template_path,
        name,
        font_path,
        text_position,
        font_size,
        text_color
    )

@app.route('/get_preview')
def get_preview():
    # Get parameters from request
    text_position_x = int(request.args.get('x', 760))
    text_position_y = int(request.args.get('y', 538))
    font_size = int(request.args.get('font_size', 53))
    preview_name = request.args.get('name', 'Sample Name')
    text_color = request.args.get('text_color', "#444444")
    
    # Update session
    session['text_position_x'] = text_position_x
    session['text_position_y'] = text_position_y
    session['font_size'] = font_size
    session['text_color'] = text_color
    
    # Use cached preview
    preview_io = cached_preview(
        session['template_path'],
        preview_name,
        text_position_x,
        text_position_y,
        font_size,
        session['font_path'],
        text_color
    )
    
    if preview_io:
        return send_file(preview_io, mimetype='image/png')
    else:
        return "Error generating preview", 500

@app.route('/generate', methods=['POST'])
def generate():
    # Check if required session variables exist
    if not all(key in session for key in ['template_path', 'excel_path', 'font_path', 
                                         'text_position_x', 'text_position_y', 'font_size']):
        flash('Missing required files or settings. Please start over.')
        return redirect(url_for('index'))
    
    # Get parameters
    template_path = session['template_path']
    excel_path = session['excel_path']
    font_path = session['font_path']
    text_position = (session['text_position_x'], session['text_position_y'])
    font_size = session['font_size']
    text_color = session.get('text_color', "#444444")
    event_name = request.form.get('event_name', 'Fundamental of Web Development held in GDG On Campus AIT')
    
    # Generate certificates
    certificate_paths, email_data = batch_generate_certificates(
        template_path,
        excel_path,
        app.config['CERTIFICATE_FOLDER'],
        font_path,
        text_position,
        font_size,
        text_color
    )
    
    if not certificate_paths:
        flash('Error generating certificates')
        return redirect(url_for('index'))
    
    # Store certificate data in session
    session['email_data'] = email_data
    session['event_name'] = event_name
    
    return redirect(url_for('send_emails'))

@app.route('/send_emails')
def send_emails():
    # Check if email data exists in session
    if 'email_data' not in session or not session['email_data']:
        flash('No certificates to send')
        return redirect(url_for('index'))
    
    email_data = session['email_data']
    event_name = session.get('event_name', 'Fundamental of Web Development held in GDG On Campus AIT')
    
    # Send emails
    success_count = 0
    for recipient in email_data:
        if send_certificate_email(recipient, event_name):
            success_count += 1
    
    # Clear session data
    for key in ['template_path', 'excel_path', 'font_path', 'text_position_x', 
                'text_position_y', 'font_size', 'email_data', 'event_name']:
        if key in session:
            session.pop(key)
    
    flash(f'Successfully sent {success_count} out of {len(email_data)} emails')
    return redirect(url_for('index'))

@app.route('/view_certificate/<certificate_id>')
def view_certificate(certificate_id):
    # Find the certificate file
    certificate_files = os.listdir(app.config['CERTIFICATE_FOLDER'])
    certificate_file = None
    
    for filename in certificate_files:
        if certificate_id in filename:
            certificate_file = filename
            break
    
    if not certificate_file:
        return "Certificate not found", 404
    
    # Extract name from filename
    name = certificate_file.split('_')[0]
    
    # Get certificate path
    certificate_path = os.path.join(app.config['CERTIFICATE_FOLDER'], certificate_file)
    
    # Generate download URL
    download_url = url_for('download_certificate', certificate_id=certificate_id)
    
    return render_template(
        'view_certificate.html',
        name=name,
        certificate_id=certificate_id,
        certificate_path=url_for('serve_certificate', certificate_id=certificate_id),
        download_url=download_url
    )

@app.route('/serve_certificate/<certificate_id>')
def serve_certificate(certificate_id):
    # Find the certificate file
    certificate_files = os.listdir(app.config['CERTIFICATE_FOLDER'])
    certificate_file = None
    
    for filename in certificate_files:
        if certificate_id in filename:
            certificate_file = filename
            break
    
    if not certificate_file:
        return "Certificate not found", 404
    
    # Return the certificate file
    return send_file(os.path.join(app.config['CERTIFICATE_FOLDER'], certificate_file))

@app.route('/download_certificate/<certificate_id>')
def download_certificate(certificate_id):
    # Find the certificate file
    certificate_files = os.listdir(app.config['CERTIFICATE_FOLDER'])
    certificate_file = None
    
    for filename in certificate_files:
        if certificate_id in filename:
            certificate_file = filename
            break
    
    if not certificate_file:
        return "Certificate not found", 404
    
    # Get name from filename
    name = certificate_file.split('_')[0]
    
    # Return the certificate file as a download
    return send_file(
        os.path.join(app.config['CERTIFICATE_FOLDER'], certificate_file),
        as_attachment=True,
        download_name=f"{name}_certificate.png"
    )

if __name__ == '__main__':
    app.run(debug=True)
