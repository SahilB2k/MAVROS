# Alternative Installation Methods for Flask

## Issue
You're getting a "Permission denied" error when trying to install Flask via pip.

## Solutions (Try in order)

### Solution 1: Use --user flag
```bash
pip install --user flask flask-cors
```

### Solution 2: Upgrade pip first
```bash
python -m pip install --upgrade pip
pip install flask flask-cors
```

### Solution 3: Use python -m pip
```bash
python -m pip install flask flask-cors
```

### Solution 4: Disable antivirus temporarily
Your antivirus might be blocking pip. Temporarily disable it and try:
```bash
pip install flask flask-cors
```

### Solution 5: Use a different mirror
```bash
pip install --index-url https://pypi.org/simple/ flask flask-cors
```

### Solution 6: Download wheels manually
1. Download from: https://pypi.org/project/Flask/#files
2. Download from: https://pypi.org/project/Flask-CORS/#files
3. Install locally:
```bash
pip install Flask-3.0.0-py3-none-any.whl
pip install Flask_Cors-4.0.0-py2.py3-none-any.whl
```

### Solution 7: Run as Administrator
Right-click PowerShell → "Run as Administrator", then:
```bash
cd C:\projects\MAVROS
.\myvenv\Scripts\activate
pip install flask flask-cors
```

## Alternative: Use Standalone Server (No Flask needed)

If Flask installation continues to fail, you can use Python's built-in HTTP server with a simple CGI script. I can create this for you if needed.

## Recommended Next Step
Try **Solution 1** first (--user flag), then **Solution 7** (Run as Admin).
