# UpGrad Email Sender

## Overview

UpGrad Email Sender is a Flask-based web application designed for educational institutions to manage and execute email campaigns. The system allows users to send either personalized emails with dynamic placeholders or bulk BCC emails to learners. The application features a dashboard for campaign management, file upload capabilities for email templates and recipient data, real-time progress tracking, and comprehensive reporting.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture

The application uses a traditional server-side rendered approach with Flask templates and Bootstrap for the user interface. The frontend consists of several key templates including a landing page, dashboard, campaign creation form, preview system, and reporting interface. JavaScript enhancements are provided through a main.js file that handles Bootstrap components, form validation, file uploads, and user experience improvements.

### Backend Architecture

The backend is built with Flask and follows a modular structure:

- **Main Application (`app.py`)**: Initializes Flask, configures database connections, sets up file upload handling, and manages SMTP email configuration
- **Routing (`routes.py`)**: Handles all HTTP endpoints including campaign creation, file uploads, preview functionality, and status tracking
- **Authentication (`replit_auth.py`)**: Implements Replit-based OAuth authentication with custom session storage and login management
- **Models (`models.py`)**: Defines database schema using SQLAlchemy with support for users, OAuth tokens, email campaigns, and email logs
- **Email Service (`email_service.py`)**: Manages email operations including template processing, placeholder extraction, email validation, and SMTP communication

### Data Storage Solutions

The application uses SQLAlchemy ORM with support for multiple database backends through environment configuration. The database schema includes:

- **Users table**: Stores user profiles with Replit authentication integration
- **OAuth table**: Manages authentication tokens and browser sessions
- **EmailCampaign table**: Tracks campaign metadata, status, and statistics
- **EmailLog table**: Records individual email delivery attempts and results

File storage is handled through a local uploads directory with configurable size limits and secure filename handling.

### Authentication and Authorization

Authentication is implemented using Replit's OAuth system with Flask-Dance integration. The system includes:

- **OAuth2 flow**: Handles user authentication through Replit's identity provider
- **Session management**: Maintains user sessions with browser-specific token storage
- **Access control**: Protects routes with login requirements and user-specific data filtering
- **Profile management**: Stores user profile information from OAuth provider

## External Dependencies

### Third-party Services

- **Replit Authentication**: OAuth2 provider for user authentication and identity management
- **SMTP Email Service**: Uses Office 365 SMTP server (smtp.office365.com:587) for email delivery
- **Bootstrap CDN**: Frontend framework for responsive design and UI components
- **Font Awesome CDN**: Icon library for user interface elements

### Python Libraries

- **Flask**: Core web framework with SQLAlchemy integration
- **Flask-Login**: User session management
- **Flask-Dance**: OAuth authentication handling
- **Pandas**: CSV data processing and validation
- **Werkzeug**: WSGI utilities and secure file handling
- **JWT**: Token processing for authentication

### Infrastructure Requirements

- **Database**: Configurable through DATABASE_URL environment variable
- **File System**: Local storage for email templates and CSV uploads
- **Environment Variables**: SESSION_SECRET, DATABASE_URL, SENDER_EMAIL, SENDER_PASSWORD
- **Network**: Outbound SMTP access for email delivery