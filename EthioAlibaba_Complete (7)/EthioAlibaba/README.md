# EthioAlibaba — Complete Project

Order from Alibaba with Telebirr. Website + Flask API + Telegram bot + SQLite.

---

## Folder structure (correct order)

```
EthioAlibaba/                    ← THIS is the main folder
│
├── INSTALL.bat                  ← 1. Double-click first (install packages)
├── START.bat                    ← 2. Double-click to start website
├── START_BOT.bat                ← 3. (Optional) Double-click for Telegram bot
│
├── app.py                       ← Main server
├── bot_polling.py               ← Telegram admin bot
├── requirements.txt             ← Python packages list
├── README.md                    ← This file
│
├── templates/
│   ├── index.html               ← Homepage
│   └── register.html            ← Login / Register page
│
└── static/                      ← (empty for now)
```

Database `ethioalibaba.db` is created automatically when you first run START.bat.

---

## How to run on Windows (easy way)

### Step 1 — Extract the zip
Extract `EthioAlibaba_Complete.zip` to a place you remember, for example:
- `C:\Users\LENOVO\Desktop\EthioAlibaba`
- or `C:\EthioAlibaba`

### Step 2 — Install packages (only once)
Open the `EthioAlibaba` folder → **double-click `INSTALL.bat`**

### Step 3 — Start the website
**Double-click `START.bat`**

Then open Chrome/Edge:
- Homepage → http://127.0.0.1:5000
- Login/Register → http://127.0.0.1:5000/register

### Step 4 — Telegram bot (optional)
Open another window → **double-click `START_BOT.bat`**

---

## If double-click does not work — use CMD

1. Open the `EthioAlibaba` folder in File Explorer
2. Click the address bar → type `cmd` → press Enter
   (CMD opens **inside** the correct folder)
3. Run these commands one by one:

```cmd
python -m pip install -r requirements.txt
python app.py
```

If `python` is not found, try:

```cmd
py -m pip install -r requirements.txt
py app.py
```

---

## Common errors you saw and how to fix

| Error | Meaning | Fix |
|-------|---------|-----|
| `The system cannot find the path specified` | You are not inside the EthioAlibaba folder | Open the folder first, then open CMD there (or use the .bat files) |
| `'pip' is not recognized` | Use `python -m pip` instead of just `pip` | Run: `python -m pip install -r requirements.txt` |
| `can't open file app.py` | CMD is in wrong folder (e.g. C:\Users\LENOVO) | You must be inside EthioAlibaba folder |

---

## Telegram commands (after START_BOT.bat)

- `/start` — welcome
- `/orders` — last 10 orders
- `/track ETHXXXX` — view one order
- `/status ETHXXXX Processing` — update status
- `/help`

---

## Notes

- Change `SECRET_KEY` in `app.py` before putting the site online.
- Telegram token is already set. For production use environment variables.
- Exchange rate, shipping prices, Telebirr number are inside `app.py`.
