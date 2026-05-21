======================================================
 BatStateU Attendance Monitoring System
 Local Station — Setup & Distribution Guide
======================================================

WHAT IS THIS?
─────────────
This folder is the Local Station for the IoT-Based
Attendance Monitoring System Using Facial Biometrics.
It runs entirely on your PC — no internet needed for
the camera. It connects to the cloud only to sync
attendance records and student data.


FOLDER CONTENTS
───────────────
AttendanceStation.exe   ← The server (do not rename)
launch.bat              ← Double-click this to start
local.html              ← The kiosk web interface
.env                    ← Your credentials (you must create this)
faces/                  ← Student face images (auto-created)
uploads/                ← Signatures and photos (auto-created)


FIRST-TIME SETUP (do this once per PC)
────────────────────────────────────────
1. Create a file named exactly:   .env
   (no filename before the dot — just .env)

   Paste this inside and fill in your real values:

   DB_HOST=your-neon-host.neon.tech
   DB_PORT=5432
   DB_NAME=your_db_name
   DB_USER=your_db_user
   DB_PASSWORD=your_db_password

   CLOUDINARY_CLOUD_NAME=your_cloud_name
   CLOUDINARY_API_KEY=your_api_key
   CLOUDINARY_API_SECRET=your_api_secret

2. Double-click launch.bat to start the system.
   A terminal window opens (keep it open).
   Your browser opens automatically at http://127.0.0.1:5000

3. Log in with your instructor credentials.

4. On first login, student face images will sync
   automatically from Cloudinary (~1-2 min depending
   on number of students and internet speed).


EVERY DAY USE
─────────────
1. Double-click launch.bat
2. Browser opens automatically — log in
3. Select your class → Start Camera
4. Students are detected and attendance is saved
5. Close the terminal window to stop the server


IMPORTANT NOTES
───────────────
• Keep the terminal window open while using the system.
  Closing it stops the server.

• The faces/ folder is specific to this PC.
  If you use a different PC, log in and the system
  will automatically download face images from the cloud.

• The .env file contains sensitive credentials.
  Do NOT share it or upload it to GitHub.

• The InsightFace model (~300MB) is bundled inside
  the EXE. It does not need to download anything
  on first run.

• Camera sources supported:
    - Webcam (Built-in)  → works out of the box
    - IP Camera (RTSP)   → enter the RTSP URL in the app


BUILDING FROM SOURCE (developers only)
────────────────────────────────────────
Requirements:
  pip install pyinstaller insightface onnxruntime
  pip install flask flask-cors werkzeug cloudinary
  pip install psycopg2-binary python-dotenv reportlab
  pip install opencv-python numpy requests

Build command (run inside the project folder):
  pyinstaller local_app.spec

Output: dist/AttendanceStation/
Copy .env, local.html, and login.html into that folder.


TROUBLESHOOTING
───────────────
"Port already in use"
  → Another instance is running. Open Task Manager,
    find AttendanceStation.exe and end it, then relaunch.

"Cannot connect to database"
  → Check your .env credentials and internet connection.

"Camera not found"
  → Try selecting a different source in the dropdown.
    For RTSP, verify the camera IP and URL format.

"Face not detected"
  → Ensure the student is registered with face photos.
    Check the student list for F✓ badge.
    Ensure good lighting facing the camera.

======================================================
