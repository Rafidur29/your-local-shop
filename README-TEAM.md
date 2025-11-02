🛒 Your Local Shop – Frontend

Frontend implementation for **Your Local Shop** (React + TypeScript).
This project handles the client-side flow — catalogue, product details, cart, checkout, and order confirmation — using mock data for now.

---

## 🚀 Quick Start

### 1️⃣ Clone the repository
```bash
git clone https://github.com/Rafidur29/your-local-shop-frontend.git
cd your-local-shop-frontend
2️⃣ Install dependencies
bash
Copy code
npm install
3️⃣ Run the development server
bash
Copy code
npm start
Then open: http://localhost:3000

⚙️ Project Structure
pgsql
Copy code
src/
├─ api/          → mock API adapters (Catalogue, Inventory)
├─ components/   → NavBar, ProductCard
├─ pages/        → Home, Catalogue, PDP, Cart, Checkout, Confirmation
├─ stores/       → Zustand cart store (persistent)
├─ types/        → shared interfaces
├─ App.tsx       → routes
└─ index.tsx     → entry point
public/
└─ mock/
   ├─ products.json
   └─ inventory.json
🌐 Environment Variables
Create .env.development in project root:

ini
Copy code
REACT_APP_API_BASE=http://localhost:8080
REACT_APP_USE_MOCK=true
REACT_APP_API_BASE → backend endpoint (for integration later)

REACT_APP_USE_MOCK → toggle between mock and real API

🔗 Integration Notes (for backend team)
Frontend currently fetches mock data from /public/mock/

Replace mock fetches in:

src/api/catalogue.ts

src/api/inventory.ts

with actual REST endpoints when backend is ready.

Example:

ts
Copy code
const API = process.env.REACT_APP_API_BASE;
await fetch(`${API}/catalogue`);
🧩 State Management
Uses Zustand for global cart state

Cart auto-saves to localStorage

Supports add, remove, update quantity, and total functions

🧾 Routes Overview
Route	Purpose
/	Home
/catalogue	Product list
/product/:sku	Product detail
/cart	Shopping cart
/checkout	Checkout form
/confirmation	Order summary

🔧 Build for production
bash
Copy code
npm run build
🧑‍💻 Maintainer
Frontend Developer: Rafid ur Rahman (Rafidur29)
Repo: https://github.com/Rafidur29/your-local-shop-frontend
