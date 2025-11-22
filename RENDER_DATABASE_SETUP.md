# Render Database Setup Instructions

## CRITICAL ISSUE IDENTIFIED

Your production server is currently using **SQLite** instead of **PostgreSQL** because the `DATABASE_URL` environment variable is not set on Render.

This explains why:
- Call data shows temporarily in the frontend
- After logout/login, the call history disappears
- No data persists across server restarts

## How to Fix

### Step 1: Create PostgreSQL Database on Render

1. Go to your Render Dashboard: https://dashboard.render.com/
2. Click on "New +" button
3. Select "PostgreSQL"
4. Configure the database:
   - **Name**: `ofdautocall-db` (or any name you prefer)
   - **Database**: `ofdautocall` (default is fine)
   - **User**: `ofdautocall` (default is fine)
   - **Region**: Same region as your web service (for faster connection)
   - **PostgreSQL Version**: 16 (latest)
   - **Instance Type**: Free (or paid if you need more)
5. Click "Create Database"
6. Wait 2-3 minutes for the database to be created

### Step 2: Connect Database to Web Service

1. Go to your web service: "ofdautocall" (or your service name)
2. Click on "Environment" tab
3. Scroll down to "Environment Variables"
4. Click "Add Environment Variable"
5. Add the following:
   - **Key**: `DATABASE_URL`
   - **Value**: Go to your PostgreSQL database page, copy the "Internal Database URL"
6. Click "Save Changes"

**NOTE**: Render usually auto-connects the database when created, so `DATABASE_URL` might already be there. If it's there, verify it's not empty.

### Step 3: Verify Environment Variables

While you're in the Environment tab, verify these VAPI variables are also set:

- `VAPI_PRIVATE_KEY` - Should contain your VAPI private key
- `VAPI_PHONE_NUMBER_ID` - Should contain your VAPI phone number ID
- `VAPI_ASSISTANT_ID` - Should contain your VAPI assistant ID

If any are missing, add them now.

### Step 4: Deploy with New Configuration

After adding/verifying `DATABASE_URL`:

1. The service will automatically redeploy
2. OR manually trigger a deploy: Settings → "Manual Deploy" → Deploy latest commit
3. Wait for deployment to complete (2-3 minutes)

### Step 5: Check Build Logs

After deployment completes:

1. Go to your web service → "Logs" tab
2. Look for these messages in the build logs:

```
========================================
Render Build Script Starting...
========================================

✅ DATABASE_URL is set: postgresql://...
```

3. Look for these messages in the runtime logs:

```
======================================
Database Configuration Check:
======================================
✅ DATABASE_URL is set: postgresql://...
✅ Using production database: django.db.backends.postgresql
======================================
```

If you see "❌ DATABASE_URL is NOT set", then step 2 didn't work correctly.

### Step 6: Test the Application

1. Login to your frontend: https://ofdautocall.netlify.app/
2. Navigate to OFD tab
3. Click "Call All Now"
4. After call completes, logout
5. Login again
6. Check if call history is still there

If call history persists after logout/login, the database is configured correctly!

## Troubleshooting

### Database URL is set but still using SQLite

1. Check if DATABASE_URL is actually set correctly (not empty)
2. Verify the format: `postgresql://user:password@host:port/database`
3. Make sure you copied the "Internal Database URL" not "External Database URL"
4. Redeploy the service after setting DATABASE_URL

### Migrations not running

If you see errors about missing tables:

1. Go to web service → Shell tab
2. Run: `python manage.py migrate`
3. This will manually create all database tables

### Data was lost

If you already had data in SQLite and it's now gone:

- SQLite data cannot be recovered once you switch to PostgreSQL
- This is expected behavior
- All new data will now persist in PostgreSQL

## Alternative: Manual Database URL Setup

If auto-connection doesn't work, manually construct the DATABASE_URL:

1. Go to PostgreSQL database page
2. Copy these values:
   - Host
   - Port
   - Database
   - Username
   - Password
3. Construct URL: `postgresql://[username]:[password]@[host]:[port]/[database]`
4. Example: `postgresql://ofdautocall:s3cr3tP@ssw0rd@dpg-abc123.oregon-postgres.render.com:5432/ofdautocall`
5. Add this as `DATABASE_URL` environment variable

## After Database is Fixed

Once the database is working:

1. The call history will persist across restarts
2. User accounts will persist
3. All order data will be saved properly
4. The "Refresh Call Status" button will work correctly

## Need Help?

If you're still having issues:

1. Check Render logs for error messages
2. Verify all environment variables are set correctly
3. Ensure PostgreSQL database is running (check database dashboard)
4. Try redeploying the service
