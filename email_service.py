import smtplib
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
import os
import time
from datetime import datetime
from models import EmailCampaign, EmailLog
from app import db

def extract_placeholders(template):
    """Extract placeholders in the format <Placeholder> from template"""
    all_phs = re.findall(r'<([^<>]+)>', template)
    unique_phs = list(dict.fromkeys(all_phs))
    return all_phs, unique_phs

def is_valid_email(email):
    """Validate email format"""
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, str(email)) is not None

def validate_csv_data(df, placeholders):
    """Validate CSV data and return valid/invalid rows"""
    def row_missing_fields(row, placeholders):
        missing = []
        if not is_valid_email(row['Email']):
            missing.append('Email (Invalid)')
        for ph in placeholders:
            if ph in row and (pd.isna(row[ph]) or str(row[ph]).strip() == ''):
                missing.append(ph)
        return missing

    df['MissingFields'] = df.apply(lambda row: row_missing_fields(row, placeholders), axis=1)
    df_valid = df[df['MissingFields'].apply(lambda x: len(x) == 0)]
    df_invalid = df[df['MissingFields'].apply(lambda x: len(x) > 0)]
    
    return df_valid, df_invalid

def send_test_email(template, placeholders, sample_data, subject, test_email, smtp_config):
    """Send a test email with sample data"""
    try:
        # Replace placeholders with sample data
        body = template
        for ph in placeholders:
            if ph in sample_data:
                body = body.replace(f"<{ph}>", str(sample_data[ph]))
        
        server = smtplib.SMTP(smtp_config['server'], smtp_config['port'])
        server.starttls()
        server.login(smtp_config['email'], smtp_config['password'])
        
        msg = MIMEMultipart()
        msg['From'] = smtp_config['email']
        msg['To'] = test_email
        msg['Subject'] = f"[TEST] {subject}"
        msg.attach(MIMEText(body, 'plain'))
        
        server.send_message(msg)
        server.quit()
        return True, "Test email sent successfully"
    except Exception as e:
        return False, str(e)

def send_bulk_emails(campaign_id, template, placeholders, df_valid, subject, mode, smtp_config):
    """Send bulk emails and update campaign status"""
    campaign = EmailCampaign.query.get(campaign_id)
    campaign.status = 'sending'
    campaign.total_emails = len(df_valid)
    db.session.commit()
    
    try:
        server = smtplib.SMTP(smtp_config['server'], smtp_config['port'])
        server.starttls()
        server.login(smtp_config['email'], smtp_config['password'])
        
        sent_count = 0
        failed_count = 0
        
        if mode == 'personalized':
            # Send personalized emails
            for _, row in df_valid.iterrows():
                learner = row.to_dict()
                email_addr = learner['Email']
                
                try:
                    body = template
                    for ph in placeholders:
                        body = body.replace(f"<{ph}>", str(learner[ph]))
                    
                    msg = MIMEMultipart()
                    msg['From'] = smtp_config['email']
                    msg['To'] = email_addr
                    msg['Subject'] = subject
                    msg.attach(MIMEText(body, 'plain'))
                    
                    server.send_message(msg)
                    sent_count += 1
                    
                    # Log success
                    log = EmailLog(
                        campaign_id=campaign_id,
                        recipient_email=email_addr,
                        status='sent'
                    )
                    db.session.add(log)
                    
                except Exception as e:
                    failed_count += 1
                    
                    # Log failure
                    log = EmailLog(
                        campaign_id=campaign_id,
                        recipient_email=email_addr,
                        status='failed',
                        error_message=str(e)
                    )
                    db.session.add(log)
                
                # Update campaign progress
                campaign.sent_emails = sent_count
                campaign.failed_emails = failed_count
                db.session.commit()
                
                time.sleep(1)  # Rate limiting
        
        else:
            # Bulk BCC mode
            try:
                msg = MIMEMultipart()
                msg['From'] = smtp_config['email']
                msg['To'] = smtp_config['email']
                msg['Subject'] = subject
                msg.attach(MIMEText(template, 'plain'))
                
                bcc_list = df_valid['Email'].tolist()
                server.sendmail(smtp_config['email'], bcc_list, msg.as_string())
                
                sent_count = len(bcc_list)
                
                # Log success for all emails
                for email_addr in bcc_list:
                    log = EmailLog(
                        campaign_id=campaign_id,
                        recipient_email=email_addr,
                        status='sent'
                    )
                    db.session.add(log)
                
            except Exception as e:
                failed_count = len(df_valid)
                
                # Log failure for all emails
                for _, row in df_valid.iterrows():
                    log = EmailLog(
                        campaign_id=campaign_id,
                        recipient_email=row['Email'],
                        status='failed',
                        error_message=str(e)
                    )
                    db.session.add(log)
        
        server.quit()
        
        # Update final campaign status
        campaign.sent_emails = sent_count
        campaign.failed_emails = failed_count
        campaign.status = 'completed'
        campaign.completed_at = datetime.now()
        db.session.commit()
        
        return True, f"Campaign completed. Sent: {sent_count}, Failed: {failed_count}"
        
    except Exception as e:
        campaign.status = 'failed'
        db.session.commit()
        return False, str(e)

def generate_report(campaign_id):
    """Generate email campaign report"""
    campaign = EmailCampaign.query.get(campaign_id)
    logs = EmailLog.query.filter_by(campaign_id=campaign_id).all()
    
    report_data = {
        'campaign': campaign,
        'logs': logs,
        'summary': {
            'total': campaign.total_emails,
            'sent': campaign.sent_emails,
            'failed': campaign.failed_emails
        }
    }
    
    return report_data
