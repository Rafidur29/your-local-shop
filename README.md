# Your Local Shop

This repository contains both the frontend (React) and backend (FastAPI - Sith Scope) components of the project.

---

## 🖥️ Frontend (React)

This project was bootstrapped with [Create React App](https://github.com/facebook/create-react-app).

### Available Scripts

In the project directory, you can run:

#### `npm start`
Runs the app in development mode.  
Open [http://localhost:3000](http://localhost:3000) to view it in your browser.

#### `npm test`
Launches the test runner in interactive watch mode.

#### `npm run build`
Builds the app for production to the `build/` folder.

#### `npm run eject`
Copies all configuration files for full customization (one-way operation).

For more info, see the [Create React App documentation](https://facebook.github.io/create-react-app/docs/getting-started).

---

## ⚙️ Backend (FastAPI - Sith Scope)

### Quick start
```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload