#!/usr/bin/env python3
"""Subject-aware static reframe: crop a horizontal video to a target aspect ratio,
keeping the dominant subject (face / person) horizontally centred in the crop window.

Strategy (KISS): sample frames -> find the median subject x-centre -> emit ONE
ffmpeg crop offset (constant pan). This avoids per-frame jitter and needs no
per-frame keyframe path. For a moving virtual camera (dynamic pan+zoom) use one of
the AI tools referenced in SKILL.md instead.

Detector fallback chain: mediapipe face -> OpenCV DNN face -> Haar cascade -> centre.
Only numpy + opencv-python are hard deps; ffmpeg comes from imageio-ffmpeg.
"""
import argparse, subprocess, sys, statistics

def ffmpeg_bin():
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        return "ffmpeg"

def probe_dims(path):
    """Return (width, height) using ffmpeg stderr parsing (no ffprobe needed)."""
    out = subprocess.run([ffmpeg_bin(), "-hide_banner", "-i", path],
                         stderr=subprocess.PIPE, stdout=subprocess.DEVNULL, text=True).stderr
    import re
    m = re.search(r",\s*(\d{2,5})x(\d{2,5})", out)
    if not m:
        sys.exit("could not read video dimensions")
    return int(m.group(1)), int(m.group(2))

def sample_frames(path, n):
    """Yield n evenly-spaced frames as BGR numpy arrays via ffmpeg pipe."""
    import numpy as np
    w, h = probe_dims(path)
    # grab n frames spread across the file using the thumbnail-free select trick
    cmd = [ffmpeg_bin(), "-hide_banner", "-loglevel", "error", "-i", path,
           "-vf", f"fps=1", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    frame_bytes = w * h * 3
    frames = []
    while True:
        buf = proc.stdout.read(frame_bytes)
        if len(buf) < frame_bytes:
            break
        frames.append(np.frombuffer(buf, np.uint8).reshape(h, w, 3))
    proc.wait()
    if not frames:
        return []
    step = max(1, len(frames) // n)
    return frames[::step][:n]

def subject_centre_x(frames, vid_w):
    """Return median subject centre x in pixels, or vid_w/2 if nothing detected."""
    centres = []
    # 1) mediapipe
    try:
        import mediapipe as mp
        det = mp.solutions.face_detection.FaceDetection(model_selection=1, min_detection_confidence=0.5)
        for f in frames:
            import cv2
            res = det.process(cv2.cvtColor(f, cv2.COLOR_BGR2RGB))
            if res.detections:
                d = max(res.detections, key=lambda d: d.location_data.relative_bounding_box.width)
                bb = d.location_data.relative_bounding_box
                centres.append((bb.xmin + bb.width / 2) * vid_w)
        if centres:
            return statistics.median(centres)
    except Exception:
        pass
    # 2) OpenCV Haar cascade (bundled with opencv-python)
    try:
        import cv2
        cascade = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        for f in frames:
            gray = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
            faces = cascade.detectMultiScale(gray, 1.1, 5, minSize=(40, 40))
            if len(faces):
                x, y, w, h = max(faces, key=lambda r: r[2])
                centres.append(x + w / 2)
        if centres:
            return statistics.median(centres)
    except Exception:
        pass
    return vid_w / 2

def main():
    ap = argparse.ArgumentParser(description="Subject-aware static reframe to a target aspect ratio")
    ap.add_argument("input")
    ap.add_argument("output")
    ap.add_argument("--ar", default="9:16", help="target aspect ratio, e.g. 9:16, 1:1, 4:5")
    ap.add_argument("--samples", type=int, default=30, help="frames to sample for detection")
    ap.add_argument("--crf", default="18")
    args = ap.parse_args()

    aw, ah = (int(x) for x in args.ar.split(":"))
    vid_w, vid_h = probe_dims(args.input)

    # crop window sized to fit inside source, matching target AR, full height when possible
    crop_w = min(vid_w, int(round(vid_h * aw / ah)))
    crop_h = min(vid_h, int(round(crop_w * ah / aw)))
    crop_w -= crop_w % 2
    crop_h -= crop_h % 2

    frames = sample_frames(args.input, args.samples)
    cx = subject_centre_x(frames, vid_w)

    x = int(round(cx - crop_w / 2))
    x = max(0, min(x, vid_w - crop_w))   # clamp inside frame
    y = max(0, (vid_h - crop_h) // 2)

    vf = f"crop={crop_w}:{crop_h}:{x}:{y}"
    cmd = [ffmpeg_bin(), "-hide_banner", "-y", "-i", args.input,
           "-vf", vf, "-c:v", "libx264", "-crf", args.crf, "-preset", "medium",
           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", args.output]
    print(f"source {vid_w}x{vid_h} -> crop {crop_w}x{crop_h} @ x={x} (subject cx={cx:.0f})", file=sys.stderr)
    sys.exit(subprocess.run(cmd).returncode)

if __name__ == "__main__":
    main()
