# ProctorX – upgraded online examination portal

## Included features
- Student dashboard with sidebar navigation: My Dashboard, Upcoming Exams, Exam History, Result History, Profile and Log out.
- Login/signup flow backed by the existing MySQL database.
- Randomized short-answer and long-answer exam sets.
- Exam submission history and short-answer result history saved to `exam_submissions.json`.
- Browser voice assistance: reads the current question and supports spoken next, previous and repeat commands (Chrome/Edge support required).
- Full-screen request when an exam starts, with three warnings for leaving/minimizing the page or exiting full-screen. On the third warning, the exam is submitted automatically.
- Existing webcam/AI proctoring stream retained.

## Apply to your project
1. Make a backup of your current project folder.
2. Extract this ZIP.
3. Copy the extracted files into the INNER project folder (the folder containing `server.py`), replacing files when prompted.
4. Keep your existing `.env`, `.venv311`, MySQL database, and model weights. They are intentionally not included.
5. Never upload `.env`, database credentials, virtual environments, or model secrets to GitHub.

## VS Code PowerShell run commands
Open the INNER project folder in VS Code, then run:

```powershell
# If your venv is one folder above the project folder:
& ..\.venv311\Scripts\Activate.ps1

# If your venv is inside the project folder instead:
# .\.venv311\Scripts\Activate.ps1

python server.py
```

Open `http://127.0.0.1:5000` in Chrome or Edge. Allow camera and microphone permissions when prompted.

## Notes and limitations
- Browser fullscreen and visibility events are deterrents, not tamper-proof proctoring. Browsers/operating systems can restrict fullscreen behavior; students can still use another device. Do not treat a warning count as conclusive proof of cheating.
- Voice commands use the browser Web Speech API and may require an internet connection or supported browser. The microphone is activated only after the student clicks Voice help.
- The database helper currently uses plain-text passwords. This is unsuitable for public deployment; migrate to salted password hashing before production.
- `exam_submissions.json` is a local development history store. Use a database table for multi-user production hosting.
- The descriptive exam result correctly remains pending instructor evaluation.
- Set a strong `FLASK_SECRET_KEY` in `.env` or the process environment before deployment.
