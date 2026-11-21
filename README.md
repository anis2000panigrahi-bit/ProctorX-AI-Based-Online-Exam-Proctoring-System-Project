# ProctorX – AI-Based Online Exam Proctoring System

An intelligent online examination platform designed to conduct secure, reliable, and transparent online assessments using Artificial Intelligence and Computer Vision.

ProctorX combines an examination portal with AI-powered monitoring features to help detect suspicious activities during online examinations. It provides a structured examination environment, automated MCQ evaluation, descriptive answer submission, and activity monitoring.

---

## About the Project

**ProctorX** is an AI-based online examination and proctoring system developed to improve the security and integrity of online assessments.

The system monitors candidates during examinations using computer vision and audio-based detection techniques. It identifies potentially suspicious activities and maintains activity records that can be reviewed after the examination.

The platform also provides separate examination patterns for objective and descriptive assessments, along with examination timers, result management, and student account functionality.

---

## Key Features

### 1. Online Examination System
- Student registration and login.
- Secure examination dashboard.
- Short Answer and Long Answer examination patterns.
- Randomized multiple-choice questions.
- Descriptive answer submission.
- Examination countdown timer.
- Automatic submission when the timer expires.

### 2. AI-Based Proctoring
- Face Detection using Dlib.
- Eye Gaze Detection.
- Mouth Tracking.
- Blink Detection.
- Head Pose Estimation.
- Object Detection using YOLO.
- Audio Activity Detection.

### 3. Examination Monitoring
- Real-time candidate monitoring.
- Suspicious activity detection.
- Examination violation tracking.
- Activity logging.
- Examination history management.

### 4. Student Dashboard
- Student profile management.
- Examination history.
- Result information.
- Account password management.
- Examination status monitoring.

---

## Technologies Used

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Frontend | HTML, CSS, JavaScript |
| Backend | Flask |
| Computer Vision | OpenCV, Dlib |
| Object Detection | YOLO |
| Audio Processing | PyAudio, Winsound |
| Database | MySQL |
| Development Tools | VS Code, Git, GitHub |

---

## Project Structure

```text
ProctorX/
│
├── static/
│   ├── css/
│   ├── js/
│   ├── images/
│   └── style.css
│
├── templates/
│   ├── index.html
│   ├── login.html
│   ├── dashboard.html
│   └── quiz.html
│
├── config/
│   └── database configuration
│
├── exam_data.py
├── server.py
├── main.py
├── requirements.txt
├── .gitignore
├── README.md
└── activity.txt
```

*Note: The structure above is illustrative. Actual folders and files may differ depending on your project version.*

---

## Installation and Setup

### Step 1: Clone the Repository

```bash
git clone https://github.com/anis2000panigrahi-bit/ProctorX.git
```

### Step 2: Open the Project Folder

```bash
cd ProctorX
```

### Step 3: Create a Virtual Environment

```bash
python -m venv .venv
```

### Step 4: Activate the Virtual Environment

For Windows PowerShell:

```powershell
.venv\Scripts\Activate.ps1
```

### Step 5: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 6: Configure Environment Variables

Create a `.env` file in the project directory and add your required configuration:

```env
FLASK_SECRET_KEY=your_secret_key
DB_HOST=localhost
DB_USER=root
DB_PASSWORD=your_database_password
DB_NAME=your_database_name
```

Use your own database credentials and any required API keys.

**Important:** Never upload your actual `.env` file, passwords, API keys, or private credentials to GitHub.

### Step 7: Configure the Database

- Install and start MySQL.
- Create the required database.
- Configure the database connection settings.
- Ensure the required tables are available.

### Step 8: Run the Application

```bash
python server.py
```

Open your browser and visit:

```text
http://127.0.0.1:5000/
```

---

## How to Use

1. Open the ProctorX application.
2. Register a new student account or log in.
3. Access the examination dashboard.
4. Select the required examination pattern.
5. Read the examination instructions.
6. Start the examination.
7. Complete the questions within the given time.
8. Submit the examination.
9. Review the available result and examination history.

---

## Activity Monitoring

During an examination, the proctoring system monitors candidate activity using supported computer vision and audio detection modules.

Detected activities can be recorded in an activity log for further review.

The monitoring system is intended to assist examination supervision. Automated detections should be reviewed carefully and should not be treated as definitive proof of misconduct.

---

## Future Enhancements

- Integration of advanced AI-based suspicious activity detection.
- Improved face recognition and candidate verification.
- Enhanced examination analytics.
- Advanced student performance reports.
- Cloud-based examination deployment.
- Improved real-time monitoring dashboard.

---

## Developer

**Anis Kumar Panigrahi**

B.Tech – Computer Science and Engineering

Gandhi Engineering College, Bhubaneswar, Odisha, India.

### Connect With Me

- **LinkedIn:** https://www.linkedin.com/in/aniskumarpanigrahi/
- **GitHub:** https://github.com/anis2000panigrahi-bit
- **Instagram:** https://www.instagram.com/anis_panigrahi.2545/

---

## Acknowledgement

This project is based on and developed with reference to existing work in AI-based online examination proctoring.

Original project credits and applicable third-party licenses are acknowledged and should be retained according to their respective licensing requirements.

---

## License

Please refer to the original project's license and applicable third-party licenses before redistributing or modifying this project.

---

⭐ If you find this project interesting, consider giving the repository a star!