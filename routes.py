import os
import pandas as pd
import smtplib
import re
import time
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from werkzeug.utils import secure_filename
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app import app

def allowed_file(filename, allowed_extensions):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def is_valid_email(email):
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, str(email)) is not None

def extract_placeholders(template):
    all_phs = re.findall(r'<([^<>]+)>', template)
    unique_phs = list(dict.fromkeys(all_phs))
    return all_phs, unique_phs

@app.route('/')
def index():
    if 'email_configured' in session:
        return render_template('main.html')
    return render_template('login.html')

@app.route('/setup', methods=['POST'])
def setup_email():
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '').strip()
    
    if not email or not password:
        flash('Both email and password are required', 'error')
        return redirect(url_for('index'))
    
    if not is_valid_email(email):
        flash('Please enter a valid email address', 'error')
        return redirect(url_for('index'))
    
    # Verify email credentials by sending a test email
    try:
        # Test the email credentials
        server = smtplib.SMTP(app.config['SMTP_SERVER'], app.config['SMTP_PORT'])
        server.starttls()
        server.login(email, password)
        
        # Send verification email
        msg = MIMEMultipart()
        msg['From'] = email
        msg['To'] = 'omijgatap304@gmail.com'
        msg['Subject'] = 'Email Sender Verification - Login Successful'
        
        body = f"""
Hello,

This is a verification email to confirm that your email credentials are working correctly.

Your email account ({email}) has been successfully configured for the UpGrad Email Sender.

All future email campaigns will be sent from this email address: {email}

If you did not set up this email configuration, please ignore this message.

Best regards,
UpGrad Email Sender System
        """.strip()
        
        msg.attach(MIMEText(body, 'plain'))
        server.send_message(msg)
        server.quit()
        
        # Store email credentials in session only after successful verification
        session['sender_email'] = email
        session['sender_password'] = password
        session['email_configured'] = True
        
        flash(f'Email verified successfully! All emails will be sent from {email}', 'success')
        return redirect(url_for('index'))
        
    except smtplib.SMTPAuthenticationError:
        flash('Invalid email or app password. Please check your credentials and try again.', 'error')
        return redirect(url_for('index'))
    except smtplib.SMTPException as e:
        flash(f'Email server error: {str(e)}. Please check your email settings.', 'error')
        return redirect(url_for('index'))
    except Exception as e:
        flash(f'Failed to verify email credentials: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/history')
def history():
    if 'email_configured' not in session:
        return redirect(url_for('index'))
    
    # Get campaign history from session or create empty list
    campaigns = session.get('campaign_history', [])
    return render_template('history.html', campaigns=campaigns)

@app.route('/process_campaign', methods=['POST'])
def process_campaign():
    try:
        # Get form data
        subject = request.form.get('subject', '').strip()
        mode = request.form.get('mode', 'personalized')
        
        # Get template from form or file
        template = request.form.get('template', '').strip()
        template_file = request.files.get('template_file')
        
        if template_file and allowed_file(template_file.filename, ['txt', 'html']):
            template = template_file.read().decode('utf-8')
        
        if not subject or not template:
            flash('Subject and template are required', 'error')
            return redirect(url_for('index'))
        
        # Handle CSV file upload
        csv_file = request.files.get('csv_file')
        if not csv_file or not allowed_file(csv_file.filename, ['csv']):
            flash('Please upload a valid CSV file', 'error')
            return redirect(url_for('index'))
        
        # Save CSV file
        csv_filename = secure_filename(f"temp_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{csv_file.filename}")
        csv_path = os.path.join(app.config['UPLOAD_FOLDER'], csv_filename)
        csv_file.save(csv_path)
        
        # Process template and CSV
        all_placeholders, unique_placeholders = extract_placeholders(template)
        
        # Validate for bulk mode
        if mode == 'bulk' and len(unique_placeholders) > 0:
            flash('Template contains placeholders, but Bulk mode does not support them', 'error')
            return redirect(url_for('index'))
        
        # Read and validate CSV
        df = pd.read_csv(csv_path)
        
        if 'Email' not in df.columns:
            flash('CSV must contain an "Email" column', 'error')
            return redirect(url_for('index'))
        
        # Add missing placeholder columns
        for ph in unique_placeholders:
            if ph not in df.columns:
                df[ph] = ''
        
        # Validate data
        df['valid'] = df['Email'].apply(is_valid_email)
        df_valid = df[df['valid'] == True]
        df_invalid = df[df['valid'] == False]
        
        if len(df_valid) == 0:
            flash('No valid email addresses found in CSV', 'error')
            return redirect(url_for('index'))
        
        # Store in session for preview
        session['campaign_data'] = {
            'subject': subject,
            'template': template,
            'mode': mode,
            'csv_path': csv_path,
            'placeholders': unique_placeholders,
            'valid_count': len(df_valid),
            'invalid_count': len(df_invalid),
            'sample_data': df_valid.iloc[0].to_dict() if len(df_valid) > 0 else {}
        }
        
        return redirect(url_for('preview'))
        
    except Exception as e:
        flash(f'Error processing files: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/preview')
def preview():
    if 'campaign_data' not in session or 'email_configured' not in session:
        return redirect(url_for('index'))
    
    campaign_data = session['campaign_data']
    
    # Generate preview
    preview_text = campaign_data['template']
    if campaign_data['placeholders'] and campaign_data['sample_data']:
        for ph in campaign_data['placeholders']:
            value = campaign_data['sample_data'].get(ph, f'<{ph}>')
            preview_text = preview_text.replace(f'<{ph}>', str(value))
    
    return render_template('preview.html', 
                         campaign_data=campaign_data,
                         preview_text=preview_text)

@app.route('/send_test', methods=['POST'])
def send_test():
    if 'email_configured' not in session:
        return jsonify({'success': False, 'message': 'Email not configured'})
    
    data = request.json or {}
    test_email = data.get('test_email', '').strip()
    subject = data.get('subject', '').strip()
    template = data.get('template', '').strip()
    csv_data = data.get('csv_data', [])  # First row data for testing
    
    if not test_email or not is_valid_email(test_email):
        return jsonify({'success': False, 'message': 'Invalid test email address'})
    
    if not subject or not template:
        return jsonify({'success': False, 'message': 'Subject and template are required'})
    
    try:
        # Process template with first row data if available
        test_body = template
        if csv_data:
            # Extract placeholders and replace with first row data
            import re
            placeholders = re.findall(r'<([^<>]+)>', template)
            for placeholder in placeholders:
                if placeholder in csv_data:
                    test_body = test_body.replace(f'<{placeholder}>', str(csv_data[placeholder]))
        
        # Send test email
        server = smtplib.SMTP(app.config['SMTP_SERVER'], app.config['SMTP_PORT'])
        server.starttls()
        server.login(session['sender_email'], session['sender_password'])
        
        msg = MIMEMultipart()
        msg['From'] = session['sender_email']
        msg['To'] = test_email
        msg['Subject'] = f"[TEST] {subject}"
        msg.attach(MIMEText(test_body, 'plain'))
        
        server.send_message(msg)
        server.quit()
        
        return jsonify({'success': True, 'message': 'Test email sent successfully!'})
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'Failed to send test email: {str(e)}'})

@app.route('/send_campaign', methods=['POST'])
def send_campaign():
    if 'campaign_data' not in session or 'email_configured' not in session:
        flash('Session expired', 'error')
        return redirect(url_for('index'))
    
    try:
        campaign_data = session['campaign_data']
        
        # Read CSV data
        df = pd.read_csv(campaign_data['csv_path'])
        df['valid'] = df['Email'].apply(is_valid_email)
        df_valid = df[df['valid'] == True]
        
        # Send emails
        server = smtplib.SMTP(app.config['SMTP_SERVER'], app.config['SMTP_PORT'])
        server.starttls()
        server.login(session['sender_email'], session['sender_password'])
        
        sent_count = 0
        failed_count = 0
        
        if campaign_data['mode'] == 'personalized':
            # Send personalized emails
            for _, row in df_valid.iterrows():
                try:
                    learner = row.to_dict()
                    email_addr = str(learner.get('Email', ''))
                    
                    body = campaign_data['template']
                    for ph in campaign_data['placeholders']:
                        body = body.replace(f'<{ph}>', str(learner.get(ph, '')))
                    
                    msg = MIMEMultipart()
                    msg['From'] = session['sender_email']
                    msg['To'] = email_addr
                    msg['Subject'] = campaign_data['subject']
                    msg.attach(MIMEText(body, 'plain'))
                    
                    server.send_message(msg)
                    sent_count += 1
                    
                except Exception as e:
                    failed_count += 1
                    print(f"Failed to send to {email_addr}: {e}")
                
                time.sleep(1)  # Rate limiting
        
        else:
            # Bulk BCC mode
            try:
                msg = MIMEMultipart()
                msg['From'] = session['sender_email']
                msg['To'] = session['sender_email']
                msg['Subject'] = campaign_data['subject']
                msg.attach(MIMEText(campaign_data['template'], 'plain'))
                
                bcc_list = df_valid['Email'].tolist()
                server.sendmail(session['sender_email'], bcc_list, msg.as_string())
                sent_count = len(bcc_list)
                
            except Exception as e:
                failed_count = len(df_valid)
                print(f"Bulk BCC failed: {e}")
        
        server.quit()
        
        # Save campaign to history
        import datetime
        campaign_result = {
            'subject': campaign_data['subject'],
            'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'total_recipients': len(df_valid),
            'sent_successfully': sent_count,
            'failed_to_send': failed_count,
            'success_rate': (sent_count / len(df_valid) * 100) if len(df_valid) > 0 else 0
        }
        
        # Add to session history
        campaign_history = session.get('campaign_history', [])
        campaign_history.insert(0, campaign_result)  # Add to beginning
        session['campaign_history'] = campaign_history[:10]  # Keep last 10 campaigns
        
        # Store results for completion page
        session['campaign_result'] = campaign_result
        
        return redirect(url_for('campaign_completed'))
        
    except Exception as e:
        flash(f'Error sending emails: {str(e)}', 'error')
        return redirect(url_for('preview'))

@app.route('/campaign_completed')
def campaign_completed():
    if 'campaign_result' not in session:
        return redirect(url_for('index'))
    
    result = session['campaign_result']
    return render_template('campaign_completed.html', result=result)