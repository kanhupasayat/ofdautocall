# InTransit - Order Tracking System

A full-stack application to track iThink Logistics orders with Django REST Framework backend and React Vite frontend.

## Features

### Ready To Dispatch Orders
- View all orders ready to dispatch today
- Display order count
- Show complete order details including customer info, weight, COD amount
- Last scan information

### In Transit Orders
- View all orders currently in transit
- Display estimated delivery dates
- **Red alert/tag for overdue deliveries** (orders past their estimated delivery date)
- Complete scan history
- Count of total and delayed orders

## Project Structure

```
Intransit/
├── backend/          # Django REST Framework API
│   ├── config/       # Django settings and configuration
│   ├── orders/       # Orders app with API endpoints
│   ├── manage.py
│   └── requirements.txt
│
└── frontend/         # React Vite application
    ├── src/
    │   ├── components/
    │   │   ├── OrderTracker.jsx
    │   │   ├── ReadyToDispatch.jsx
    │   │   └── InTransit.jsx
    │   ├── App.jsx
    │   └── main.jsx
    └── package.json
```

## Setup Instructions

### 🔐 Environment Variables Setup (IMPORTANT!)

**⚠️ NEVER commit .env files to git! They contain sensitive API keys.**

#### Backend Environment Variables:

1. Copy the example file:
```bash
cd backend
cp .env.example .env
```

2. Edit `.env` and add your real API keys:
```bash
# Get these from your iThink Logistics account
ITHINK_ACCESS_TOKEN=your_actual_token_here
ITHINK_SECRET_KEY=your_actual_secret_here

# Get these from your VAPI.ai account
VAPI_PRIVATE_KEY=your_vapi_private_key
VAPI_PHONE_NUMBER_ID=your_phone_number_id
VAPI_ASSISTANT_ID=your_assistant_id
```

#### Frontend Environment Variables:

1. Copy the example file:
```bash
cd frontend
cp .env.example .env
```

2. Edit `.env` with your backend URL:
```bash
# For local development
VITE_API_BASE_URL=http://localhost:8000/api

# For production (Render)
# VITE_API_BASE_URL=https://your-backend.onrender.com/api
```

---

### Backend Setup (Django)

1. Navigate to backend directory:
```bash
cd backend
```

2. Create and activate virtual environment:
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
source venv/bin/activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create `.env` file in backend directory:
```bash
copy .env.example .env
```

5. Update `.env` with your iThink API credentials:
```bash
# Get these from https://my.ithinklogistics.com
ITHINK_ACCESS_TOKEN=your_access_token_here
ITHINK_SECRET_KEY=your_secret_key_here
ITHINK_PLATFORM_ID=2

# VAPI credentials from https://dashboard.vapi.ai
VAPI_PRIVATE_KEY=your_vapi_private_key_here
VAPI_PHONE_NUMBER_ID=your_phone_number_id_here
VAPI_ASSISTANT_ID=your_assistant_id_here
```

6. Run migrations:
```bash
python manage.py migrate
```

7. Start Django development server:
```bash
python manage.py runserver
```

Backend will run on `http://localhost:8000`

### Frontend Setup (React + Vite)

1. Navigate to frontend directory:
```bash
cd frontend
```

2. Install dependencies:
```bash
npm install
```

3. Start development server:
```bash
npm run dev
```

Frontend will run on `http://localhost:3000`

## API Endpoints

### Backend API

- **POST** `/api/orders/ready-to-dispatch/`
  - Get orders ready to dispatch
  - Request body: `{"awb_numbers": ["AWB1", "AWB2"]}`

- **POST** `/api/orders/in-transit/`
  - Get in-transit orders with delivery dates
  - Request body: `{"awb_numbers": ["AWB1", "AWB2"]}`

- **POST** `/api/orders/track/`
  - Generic order tracking
  - Request body: `{"awb_numbers": ["AWB1", "AWB2"]}`

## Usage

1. Start both backend and frontend servers
2. Open browser and navigate to `http://localhost:3000`
3. Enter AWB numbers (comma-separated) in the text area
4. Click "Track Orders"
5. Switch between "Ready To Dispatch" and "In Transit" tabs
6. View order details, delivery dates, and scan history
7. Delayed orders are highlighted with red borders and "OVERDUE" tags

## iThink API Integration

The application uses iThink Logistics API v3 for order tracking:
- **API URL**: `https://api.ithinklogistics.com/api_v3/order/track.json`
- **Authentication**: access_token and secret_key
- **Maximum**: 10 AWB numbers per request

### Order Statuses

**Ready To Dispatch:**
- Manifested
- Not Picked
- REV Manifest
- REV Out for Pick Up

**In Transit:**
- Picked Up
- In Transit
- Reached At Destination
- Out For Delivery
- REV Picked Up
- REV In Transit
- REV Out For Delivery

## Technologies Used

### Backend
- Django 4.2.7
- Django REST Framework 3.14.0
- django-cors-headers
- requests
- python-dotenv

### Frontend
- React 18
- Vite
- Axios
- CSS3 (with custom styling)

## Features Highlights

1. **Real-time Tracking**: Fetch live data from iThink API
2. **Responsive Design**: Works on desktop and mobile devices
3. **Color-coded Status**: Visual indicators for different order statuses
4. **Delay Detection**: Automatically highlights overdue deliveries in red
5. **Scan History**: View complete tracking history for each order
6. **Clean UI**: Modern, gradient-based design with smooth transitions

## Development

- Backend runs on port 8000
- Frontend runs on port 3000
- CORS enabled for local development
- Proxy configured in Vite for API calls

## Notes

- Ensure both backend and frontend are running simultaneously
- Backend must be running before frontend can fetch data
- AWB numbers must be valid iThink Logistics tracking numbers
- Maximum 10 AWB numbers can be tracked per request
