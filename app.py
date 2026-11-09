import os
import subprocess
import uuid
import zipfile

from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, abort
from werkzeug.utils import secure_filename

app = Flask(__name__)

app.config["MAX_CONTENT_LENGTH"] = 500 * 1024 * 1024

DATA_DIR = Path(os.environ.get("DATA_DIR", "/tmp/photoframe"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED = {
    ".mp4", ".mov", ".mkv",
    ".avi", ".webm", ".3gp"
}


def job_dir(job_id):
    try:
        uuid.UUID(job_id)
    except Exception:
        abort(404)

    folder = DATA_DIR / job_id

    if not folder.exists():
        abort(404)

    return folder


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/api/extract", methods=["POST"])
def extract():

    uploaded = request.files.get("video")

    if not uploaded or not uploaded.filename:
        return jsonify(error="Please choose a video file."), 400

    suffix = Path(
        secure_filename(uploaded.filename)
    ).suffix.lower()

    if suffix not in ALLOWED:
        return jsonify(error="Unsupported video format."), 400

    try:
        interval = float(
            request.form.get("interval", "1")
        )
    except ValueError:
        return jsonify(error="Invalid frame interval."), 400

    if not 0.2 <= interval <= 60:
        return jsonify(error="Interval must be between 0.2 and 60 seconds."), 400

    job_id = str(uuid.uuid4())

    folder = DATA_DIR / job_id
    frames_dir = folder / "frames"

    frames_dir.mkdir(parents=True)

    source = folder / ("source" + suffix)

    uploaded.save(source)

    fps = 1.0 / interval

    output_pattern = str(
        frames_dir / "frame_%05d.jpg"
    )

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel", "error",
        "-i", str(source),
        "-vf", f"fps={fps:.8f}",
        "-q:v", "2",
        output_pattern
    ]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=900
        )
    except subprocess.TimeoutExpired:
        return jsonify(error="Video processing timed out. Try a shorter video."), 408
    finally:
        source.unlink(missing_ok=True)

    if result.returncode != 0:
        return jsonify(
            error="Could not process this video. Try another video."
        ), 422

    extracted = sorted(
        frames_dir.glob("frame_*.jpg")
    )

    if not extracted:
        return jsonify(
            error="No frames were extracted."
        ), 422

    frames = []

    for index, path in enumerate(extracted):

        frames.append({
            "name": path.name,
            "url": f"/media/{job_id}/{path.name}",
            "time": round(index * interval, 3)
        })

    return jsonify(
        job_id=job_id,
        frames=frames,
        count=len(frames)
    )


@app.route("/media/<job_id>/<filename>")
def media(job_id, filename):

    if not filename.startswith("frame_") or not filename.endswith(".jpg"):
        abort(404)

    path = job_dir(job_id) / "frames" / filename

    if not path.is_file():
        abort(404)

    return send_file(
        path,
        mimetype="image/jpeg",
        conditional=True
    )


@app.route("/api/download", methods=["POST"])
def download():

    data = request.get_json(silent=True) or {}

    job_id = str(data.get("job_id", ""))
    names = data.get("frames", [])

    folder = job_dir(job_id) / "frames"

    valid = []

    for name in names:

        if (
            isinstance(name, str)
            and name.startswith("frame_")
            and name.endswith(".jpg")
        ):

            path = folder / name

            if path.is_file():
                valid.append(path)

    if not valid:
        return jsonify(
            error="Select at least one frame."
        ), 400

    zip_path = job_dir(job_id) / "selected_photos.zip"

    with zipfile.ZipFile(
        zip_path,
        "w",
        zipfile.ZIP_DEFLATED
    ) as archive:

        for path in valid:
            archive.write(
                path,
                arcname=path.name
            )

    return send_file(
        zip_path,
        as_attachment=True,
        download_name="PhotoFrame_Images.zip"
    )


@app.errorhandler(413)
def too_large(error):
    return jsonify(
        error="Video is too large. Maximum upload size is 500 MB."
    ), 413


if __name__ == "__main__":

    app.run(
        host="0.0.0.0",
        port=int(os.environ.get("PORT", 10000))
    )
