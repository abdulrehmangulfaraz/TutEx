# 📚 TutEx – Your Premier Tutoring Platform in Karachi

  

TutEx is a full-featured web application built to connect students with verified tutors in **Karachi, Pakistan**. Developed for a professional client deployment, the platform simplifies the process of finding, managing, and paying for tuition through an intelligent and secure matchmaking system.

  

Deployed at: 🌐 [tutex.pk](https://tutex.pk)

  

---

  

## 📝 Project Overview

  

TutEx acts as a centralized hub for educational services, offering tailored features for **students**, **tutors**, and **administrators**. It includes:

  

- ✅ Area & subject-based tutor matching

- ✅ Dynamic fee calculation

- ✅ Tutor lead management

- ✅ OTP-secured user verification

- ✅ Powerful admin controls

  

---

  

## ✨ Core Features

  

### 🎓 Student Portal

- Multi-step form for registration

- Area, board, and subject selection

- Real-time fee estimation

- OTP-based email verification

- Automatic tutor matchmaking

  

### 📈 Dynamic Fee Calculation

- Area-based base fee

- Additional charges for board type

- Premium subjects add extra cost

- Total monthly tuition preview before submission

  

### 🧑‍🏫 Tutor Dashboard

- View and accept new tuition leads

- Track assigned students

- Visual analytics: Monthly income, active tuitions

- OTP-secured signup

  

### 🛠️ Admin Panel

- Approve/reject tutor requests

- Manage leads and tuition statuses

- View all registered users

- Real-time overview of platform activity

  

---

  

## 🔒 Account Security

  

TutEx ensures account authenticity through:

-  **OTP email verification**

-  **Hashed passwords using bcrypt**

-  **Token-based secure sessions**

  

---

  

## ⚙️ Tech Stack

| Category       | Technologies Used                                                       |
| -------------- | --------------------------------------------------------------------- |
| **Framework**  | FastAPI, Jinja2 Templates, Bootstrap 5                               |
| **Backend**    | Python, SQLAlchemy ORM, Passlib, aiosmtplib                          |
| **Database**   | PostgreSQL (`psycopg2`)                                               |
| **Form Handling** | python-multipart, email-validator                                   |
| **Security**   | itsdangerous, python-jose, bcrypt                                     |
| **Other Libraries** | uvicorn, slowapi, aiofiles, requests, Chart.js, Swiper.js, AOS.js |


  

---

  

## 🗂️ Project Structure

  
  

```

  

tutex/

├── backend/

│ ├── admin.py # Create admin user

│ ├── database.py # Database configuration

│ ├── init_db.py # DB table initializer

│ ├── main.py # FastAPI app

│ └── models.py # ORM models

├── frontend/

│ ├── static/

│ │ ├── css/

│ │ │ └── style.css

│ │ ├── images/

│ │ └── js/

│ │ └── script.js

│ └── templates/

│ ├── base.html, login.html, home.html, student.html, ...

│ └── tutor_dashboard.html, admin.html, etc.

├── .env # Sensitive credentials (not tracked)

├── .gitignore

├── requirements.txt # Dependencies

└── README.md

  

```

  

---

  

## 🚀 Getting Started

  

To run TutEx locally:

  

### 1. Clone the Repository

  

```bash

git  clone  https://github.com/yourusername/tutex.git

cd  tutex

  

```

  

### 2. Install Dependencies

  

```bash

pip  install  -r  requirements.txt

  

```

  

### 3. Configure Environment Variables

  

Create a `.env` file in the root:

  

```

DB_USER=your_db_user

DB_PASSWORD=your_db_password

DB_HOST=localhost

DB_PORT=5432

DB_NAME=tutex_db

  

EMAIL_USER=your_email@gmail.com

EMAIL_PASSWORD=your_email_password

  

```

  

### 4. Initialize the Database

  

```bash

python  backend/init_db.py

  

```

  

### 5. Run the Application

  

```bash

uvicorn  backend.main:app  --reload

  

```

  

Access it on: [http://127.0.0.1:8000](http://127.0.0.1:8000/)

  

----------

  

## 🌐 Live Deployment

  

The production version is hosted on:

  

**🔗 [https://tutex.pk](https://tutex.pk/)**

  

----------

  

## 👨‍💻 Author

  

**Abdulrehman Gulfaraz**

📧 Email: [abdulrehmangulfaraz1@gmail.com](mailto:abdulrehmangulfaraz1@gmail.com)

🌐 GitHub: [@abdulrehmangulfaraz](https://github.com/abdulrehmangulfaraz)

🔗 LinkedIn: [Abdulrehman Gulfaraz](https://www.linkedin.com/in/abdulrehman-gulfaraz)

  

----------

  

## 📄 License

  

This project was developed as a **client-commissioned solution** and is **not open-source**. For business or licensing inquiries, please see [License](/LICENSE).

  

----------

  

## ❤️ Special Thanks

  

- To the client for trusting in this development.


  

----------

  

> “Developed with precision, built with purpose – TutEx bridges the gap between learning and teaching.”