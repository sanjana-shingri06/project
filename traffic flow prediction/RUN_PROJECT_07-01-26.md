# 🚀 Traffic Flow Prediction - Project Startup Guide

## Your Project Location
```
C:\Users\sanja\Desktop\traffic flow prediction\
```

## Quick Start (3 Steps)

### Step 1: Activate Virtual Environment
```powershell
cd 'C:\Users\sanja\Desktop\traffic flow prediction'
venv\Scripts\activate
```

### Step 2: Install Dependencies
```powershell
pip install -r .\requirements.txt
```

### Step 3: Run the App
```powershell
python app.py
```

## Expected Output
```
⚠️ Model failed to load at startup...
Starting Socket.IO app (attempting to bind 0.0.0.0:5000)...
(XXXX) wsgi starting up on http://0.0.0.0:5000
```

## Access Your Project

| Feature | URL |
|---------|-----|
| **Home Page** | http://127.0.0.1:5000/ |
| **Real-Time Map** | http://127.0.0.1:5000/map |
| **Dashboard** | http://127.0.0.1:5000/dashboard |
| **Predict Traffic** | http://127.0.0.1:5000/predict |
| **Manual Input** | http://127.0.0.1:5000/manual_input |

## Features Enabled

✅ **Real-Time Traffic Map** - Live alerts with Socket.IO
✅ **Post New Alerts** - POST to `/alerts` endpoint
✅ **Traffic Dashboard** - Historical analysis
✅ **Traffic Prediction** - ML-based forecasting (requires model training)
✅ **File Upload** - CSV batch processing

## Test Real-Time Alerts

Open 2 browser tabs:
- **Tab 1**: http://127.0.0.1:5000/map
- **Tab 2 (PowerShell)**: Create a test alert

```powershell
curl -X POST http://127.0.0.1:5000/alerts `
  -Header "Content-Type: application/json" `
  -Body '{"road":"Main Street","severity":"high"}'
```

The map in Tab 1 will update instantly! 🎉

## Enable ML Predictions (Optional)

If predictions aren't working:
```powershell
python traffic_analysis.py
```

Then restart the app.

## Folder Structure
```
C:\Users\sanja\Desktop\traffic flow prediction\
├── app.py                    ← Main Flask app
├── requirements.txt          ← Dependencies
├── traffic_analysis.py       ← ML model training
├── templates/                ← HTML templates
│   ├── map.html
│   ├── index.html
│   ├── dashboard.html
│   ├── predict.html
│   └── ...
├── static/                   ← CSS, JS, images
│   ├── css/
│   ├── js/
│   └── plots/
├── data/                     ← Traffic data
├── uploads/                  ← User uploads
├── traffic.db               ← SQLite database (auto-created)
└── venv/                    ← Python environment
```

## Troubleshooting

**Server won't start?**
- Check if port 5000 is in use: `netstat -ano | findstr :5000`
- Change port in `app.py` line ~330 if needed

**Model not loading?**
- This is OK — map and alerts still work
- Run `python traffic_analysis.py` to train the model

**Templates/Static not found?**
- Make sure you run `python app.py` from the **project root**
- Don't run from nested folders

---

**Your project is ready to go!** Open http://127.0.0.1:5000/ in your browser. 🎉
