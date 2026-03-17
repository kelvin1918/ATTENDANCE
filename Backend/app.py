from flask import Flask, render_template, request, jsonify, send_file
import os
import json
from datetime import datetime
from reportlab.pdfgen import canvas

app = Flask(__name__)

DATA_FILE = "dashboard_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE) as f:
            return json.load(f)
    return {"classes": [], "history": [], "schedule": []}

def save_data(data):
    with open(DATA_FILE, "w") as f:
        json.dump(data, f)

@app.route("/")
def dashboard():
    return render_template("dashboard.html")

@app.route("/classes")
def classes():
    return render_template("classes.html")

@app.route("/history")
def history():
    return render_template("history.html")

@app.route("/api/classes", methods=["GET","POST"])
def manage_classes():
    data = load_data()

    if request.method == "POST":
        new_class = request.json
        data["classes"].append(new_class)
        save_data(data)
        return jsonify({"status":"created"})

    return jsonify(data["classes"])

@app.route("/api/schedule", methods=["GET","POST"])
def schedule():
    data = load_data()

    if request.method == "POST":
        sched = request.json
        data["schedule"].append(sched)
        save_data(data)
        return jsonify({"status":"added"})

    return jsonify(data["schedule"])


@app.route("/api/history")
def attendance_history():
    data = load_data()
    return jsonify(data["history"])

@app.route("/scan")
def scan_faces():

    import cv2
    import face_recognition

    video = cv2.VideoCapture(0)

    while True:

        ret, frame = video.read()

        faces = face_recognition.face_locations(frame)

        # match faces
        # update attendance

    return jsonify({"status":"completed"})


def generate_pdf(data):

    file="attendance.pdf"

    c=canvas.Canvas(file)

    y=750

    for student in data:
        c.drawString(100,y,student["name"])
        y-=20

    c.save()

    return file

@app.route("/download/<id>")
def download_pdf(id):

    file = generate_pdf(...)

    return send_file(file, as_attachment=True)


if __name__ == "__main__":
    app.run(debug=True)