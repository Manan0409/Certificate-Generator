# Certificate-Generator
A web application for generating personalized certificates from a template and sending them via email. Perfect for event organizers, educators, and trainers who need to distribute certificates to multiple recipients.

Certificate Generator

Features
1.Upload Certificate Template: Use your own certificate design as a template
2.Batch Processing: Generate certificates for multiple recipients at once using Excel data
3.Text Customization: Adjust text position, font size, and color with real-time preview
4..Email Delivery: Automatically send certificates to recipients via email
5.Verification System: Each certificate has a unique verification ID and URL
6.Social Sharing: Recipients can share their certificates on LinkedIn, Facebook, and Twitter
7.Mobile Responsive: Works on all devices

Getting Started: 

# Prerequisites:
Python 3.8 or higher
SMTP server access for sending emails

# Installation:
Local Development
1.Clone the repository:
```bash
git clone https://github.com/yourusername/certificate-generator.git
cd certificate-generator
```

2.Create a virtual environment and activate it:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3.Install dependencies:
```bash
pip install -r requirements.txt
```


5. Run the application:
python app.py
Open your browser and navigate to 
```bash
http://localhost:5000
```
## Environment Variables

To run this project, you will need to add the following environment variables to your .env file

```bash
SECRET_KEY=your-secret-key
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=your-email@gmail.com
BASE_URL=http://localhost:5000
```


