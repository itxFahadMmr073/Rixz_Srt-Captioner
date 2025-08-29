from flask import Flask, render_template, request, make_response
import re
from datetime import timedelta

app = Flask(__name__)

# ---------- Helpers ----------
def to_timestamp(ms: int) -> str:
    """Return SRT timestamp (HH:MM:SS,mmm) from milliseconds."""
    t = timedelta(milliseconds=ms)
    total_seconds = int(t.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    millis = int(ms % 1000)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"

def split_text(text: str, mode: str = "auto") -> list[str]:
    """
    Split the script into chunks:
    - 'newlines': split on line breaks (one subtitle per line)
    - 'sentences': split on sentences using punctuation
    - 'auto': if there are many newlines, use them; else use sentences
    """
    cleaned = re.sub(r"[ \t]+", " ", text.strip())
    if mode == "newlines" or (mode == "auto" and "\n" in cleaned and cleaned.count("\n") >= 2):
        return [p.strip() for p in cleaned.splitlines() if p.strip()]

    # sentence split
    parts = re.split(r"(?<=[.!?])\s+", cleaned)
    return [p.strip() for p in parts if p.strip()]

def generate_srt(chunks: list[str], duration_sec: float = 2.5, gap_ms: int = 200, start_ms: int = 0) -> str:
    """Generate SRT content from chunks and timing options."""
    srt_lines = []
    curr_ms = max(0, int(start_ms))
    dur_ms = max(500, int(duration_sec * 1000))  # at least 0.5s
    gap_ms = max(0, int(gap_ms))

    for i, text in enumerate(chunks, start=1):
        start = curr_ms
        end = start + dur_ms
        srt_lines.append(str(i))
        srt_lines.append(f"{to_timestamp(start)} --> {to_timestamp(end)}")
        srt_lines.append(text)
        srt_lines.append("")
        curr_ms = end + gap_ms

    return "\n".join(srt_lines).strip() + "\n"

# ---------- Routes ----------
@app.route("/", methods=["GET"])
def index():
    return render_template("index.html")

@app.route("/generate", methods=["POST"])
def generate():
    text = request.form.get("script", "").strip()
    split_mode = request.form.get("split_mode", "auto")
    duration = float(request.form.get("duration", "2.5"))
    gap = int(request.form.get("gap", "200"))
    start = int(request.form.get("start", "0"))
    filename = request.form.get("filename", "subtitles.srt").strip() or "subtitles.srt"

    if not text:
        return render_template("index.html", error="Please paste your script first.")

    chunks = split_text(text, split_mode)
    srt_text = generate_srt(chunks, duration, gap, start)
    return render_template(
        "index.html",
        srt_text=srt_text,
        script=text,
        split_mode=split_mode,
        duration=duration,
        gap=gap,
        start=start,
        filename=filename,
        success=f"Generated {len(chunks)} subtitle cues."
    )

@app.route("/download", methods=["POST"])
def download():
    srt_text = request.form.get("srt_text", "")
    filename = request.form.get("filename", "subtitles.srt").strip() or "subtitles.srt"
    resp = make_response(srt_text)
    resp.headers["Content-Type"] = "text/plain; charset=utf-8"
    resp.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return resp

# ---------- Run ----------
if __name__ == "__main__":
    app.run(debug=True)
