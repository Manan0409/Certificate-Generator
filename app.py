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

# Load environment variables from .env file if it exists
if os.path.exists('.env'):
    load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'development-secret-key')

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

# Create necessary directories with proper error handling
try:
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    os.makedirs(CERTIFICATE_FOLDER, exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_FOLDER, 'fonts'), exist_ok=True)
    # Set permissions
    os.chmod(UPLOAD_FOLDER, 0o777)
    os.chmod(CERTIFICATE_FOLDER, 0o777)
    os.chmod(os.path.join(UPLOAD_FOLDER, 'fonts'), 0o777)
except Exception as e:
    print(f"Error creating directories: {e}")

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['CERTIFICATE_FOLDER'] = CERTIFICATE_FOLDER

# Helper function to check allowed file extensions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Improved get_system_font_path function
def get_system_font_path(font_name):
    try:
        # First check if it's in our uploaded fonts directory
        custom_font_path = os.path.join(app.config['UPLOAD_FOLDER'], 'fonts', f"{font_name}.ttf")
        if os.path.exists(custom_font_path):
            return custom_font_path
            
        # Then try common system font locations
        common_font_paths = [
            # Linux
            f"/usr/share/fonts/truetype/{font_name}.ttf",
            f"/usr/share/fonts/TTF/{font_name}.ttf",
            # Windows (in container)
            f"/app/uploads/fonts/{font_name}.ttf",
            # Default fonts
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/liberation/LiberationSans-Regular.ttf"
        ]
        
        for path in common_font_paths:
            if os.path.exists(path):
                return path
                
        # Last resort: use matplotlib's font manager
        font_path = font_manager.findfont(font_name)
        return font_path
    except Exception as e:
        print(f"Font error: {e}")
        # Fallback to a default font that should be in the container
        default_fonts = [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/liberation/LiberationSans-Regular.ttf",
            "/app/uploads/fonts/arial.ttf"
        ]
        for font in default_fonts:
            if os.path.exists(font):
                return font
        
        # If all else fails, return the first font we can find
        try:
            font_dirs = font_manager.findSystemFonts()
            if font_dirs:
                return font_dirs[0]
        except:
            pass
            
        return None

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
        
        # Prepare drawing object
        draw = ImageDraw.Draw(template)
        
        # Define font
        font = ImageFont.truetype(font_path, font_size)
        
        # Add the name to the certificate template
        draw.text(text_position, name, font=font, fill=text_color)
        
        # Save to BytesIO object instead of file
        img_io = io.BytesIO()
        template.save(img_io, 'PNG')
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
            
          # Continuing the app.py file:

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
        
        # Create verification link
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

# Routes
@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

# Add health check endpoint for Render
@app.route('/healthz', methods=['GET'])
def health_check():
    return "OK", 200

# Add debug endpoint
@app.route('/debug', methods=['GET'])
def debug():
    import sys
    debug_info = {
        'python_version': sys.version,
        'environment_vars': {k: v for k, v in os.environ.items() if not k.lower().startswith('secret') and not k.lower().startswith('mail_password')},
        'directories': os.listdir('.'),
        'uploads_exists': os.path.exists('uploads'),
        'certificates_exists': os.path.exists('certificates'),
        'fonts_dir': os.listdir('uploads/fonts') if os.path.exists('uploads/fonts') else [],
        'mail_configured': bool(app.config['MAIL_USERNAME'] and app.config['MAIL_PASSWORD']),
        'template_dir': os.listdir('templates') if os.path.exists('templates') else []
    }
    return jsonify(debug_info)

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

@app.route('/adjust', methods=['GET'])
def adjust():
    # Check if required session variables exist
    if not all(key in session for key in ['template_path', 'excel_path', 'font_path']):
        flash('Missing required files. Please upload again.')
        return redirect(url_for('index'))
    
    # Get preview data
    try:
        data = pd.read_excel(session['excel_path'])
        if 'Name' not in data.columns:
            flash('Excel file must contain a "Name" column')
            return redirect(url_for('index'))
        
        # Get the first name for preview
        preview_name = data['Name'].iloc[0] if not data.empty else "Sample Name"
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        flash('Error reading Excel file. Please upload again.')
        return redirect(url_for('index'))
    
    return render_template(
        'adjust.html', 
        preview_name=preview_name,
        text_position_x=session.get('text_position_x', 760),
        text_position_y=session.get('text_position_y', 538),
        font_size=session.get('font_size', 53),
        text_color=session.get('text_color', "#444444")
    )

@app.route('/get_preview', methods=['GET'])
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
    
    # Generate preview
    text_position = (text_position_x, text_position_y)
    preview_io = generate_preview(
        session['template_path'],
        preview_name,
        session['font_path'],
        text_position,
        font_size,
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
    
    # Check if certificates were generated
    if not certificate_paths:
        flash('Error generating certificates. Please try again.')
        return redirect(url_for('index'))
    
    # Send emails if requested
    send_emails = request.form.get('send_emails') == 'on'
    if send_emails:
        email_success_count = 0
        for recipient in email_data:
            if send_certificate_email(recipient, event_name):
                email_success_count += 1
        
        flash(f'Successfully generated {len(certificate_paths)} certificates and sent {email_success_count} emails.')
    else:
        flash(f'Successfully generated {len(certificate_paths)} certificates. Emails were not sent.')
    
    return redirect(url_for('index'))

@app.route('/view_certificate/<certificate_id>')
def view_certificate(certificate_id):
    # Find the certificate file with this ID
    certificate_file = None
    for filename in os.listdir(app.config['CERTIFICATE_FOLDER']):
        if certificate_id in filename:
            certificate_file = filename
            break
    
    if not certificate_file:
        flash('Certificate not found.')
        return redirect(url_for('index'))
    
    certificate_path = os.path.join(app.config['CERTIFICATE_FOLDER'], certificate_file)
    
    # Extract name from filename
    name = certificate_file.split('_')[0]
    
    return render_template('view_certificate.html', certificate_file=certificate_file, name=name)

@app.route('/certificates/<filename>')
def get_certificate(filename):
    return send_file(os.path.join(app.config['CERTIFICATE_FOLDER'], filename))

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Use PORT environment variable for compatibility with Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
