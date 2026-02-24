# AutoAdvisor Frontend

## Overview
The AutoAdvisor Frontend is a Django-based web application designed to provide users with an interactive interface for managing their academic advising needs. This project integrates various technologies to deliver a seamless user experience.

## Project Structure
```
autoadvisor-frontend/
├── manage.py
├── Pipfile
├── requirements.txt
├── package.json
├── .env
├── .gitignore
├── autoadvisor_frontend/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── ui/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── models.py
│   ├── views.py
│   ├── urls.py
│   ├── templates/
│   │   └── ui/
│   │       └── index.html
│   └── static/
│       └── ui/
│           ├── css/
│           │   └── styles.css
│           └── js/
│               └── app.js
├── templates/
│   └── base.html
├── static/
│   ├── css/
│   └── js/
└── README.md
```

## Setup Instructions

1. **Clone the Repository**
   ```
   git clone <repository-url>
   cd autoadvisor-frontend
   ```

2. **Install Dependencies**
   - Using Pipenv:
     ```
     pipenv install
     ```
   - Or using requirements.txt:
     ```
     pip install -r requirements.txt
     ```

3. **Environment Variables**
   - Create a `.env` file in the root directory and add your environment variables, such as:
     ```
     SECRET_KEY='your_secret_key'
     DEBUG=True
     ```

4. **Run Migrations**
   ```
   python manage.py migrate
   ```

5. **Start the Development Server**
   ```
   python manage.py runserver
   ```

## Usage
- Access the application by navigating to `http://127.0.0.1:8000/` in your web browser.
- The UI is built using Django templates and static files, allowing for dynamic content rendering.

## Contributing
Contributions are welcome! Please submit a pull request or open an issue for any enhancements or bug fixes.

## License
This project is licensed under the MIT License. See the LICENSE file for details.