# Render - Quick Verification Steps

## After Deployment Completes

### Step 1: Check Build Logs (Automatically)

Deployment ke baad build logs me ye dikhaega:

```bash
Running migrations...
Operations to perform:
  Apply all migrations: admin, auth, contenttypes, orders, sessions
Running migrations:
  No migrations to apply.  # ✅ Good - migrations already applied
  # OR
  Applying orders.0001_initial... OK
  Applying orders.0002_order... OK
  Applying orders.0003_callhistory_is_successful... OK
  # etc.

Verifying database tables...
orders
 [X] 0001_initial
 [X] 0002_order
 [X] 0003_callhistory_is_successful_callhistory_needs_retry_and_more
 [X] 0004_callhistory_recording_url_callhistory_transcript
 [X] 0005_remove_callhistory_recording_url_and_more
```

**[X] = Applied** - Matlab CallHistory table create ho gaya!

---

### Step 2: Check Runtime Logs (Automatically)

Server start hone ke baad runtime logs me ye dikhaega:

```
======================================================================
Database Configuration Check:
======================================================================
✅ DATABASE_URL is set: postgresql://...
✅ Using production database: django.db.backends.postgresql
======================================================================

======================================================================
VAPI Credentials Check:
======================================================================
✅ VAPI_PRIVATE_KEY: sk_live_ab...
✅ VAPI_PHONE_NUMBER_ID: pn_12345...
✅ VAPI_ASSISTANT_ID: ast_67890...
======================================================================
```

**Agar ye dikha = Sab theek hai!** ✅

**Agar ye dikha = Problem hai!** ❌
```
❌ DATABASE_URL is NOT set!
⚠️ WARNING: Using SQLite database
```

---

### Step 3: Manual Verification (Optional)

**Render Shell** me ye command run karo:

```bash
python manage.py check_database
```

**Output Example**:
```
======================================================================
DATABASE DIAGNOSTIC CHECK
======================================================================

📊 Database Configuration:
   Engine: django.db.backends.postgresql
   Name: ofdautocall
   Host: dpg-xyz.oregon-postgres.render.com
   ✅ Using production database

----------------------------------------------------------------------

📋 Database Tables:
   ✅ orders_callhistory
   ✅ orders_order

----------------------------------------------------------------------

📞 CallHistory Records: 15

📊 Latest Call:
   AWB: AWB123456
   Phone: +919876543210
   Status: completed
   Ended Reason: hangup
   Success: True
   Created: 2025-11-22 14:30:00

📈 Calls by Ended Reason:
   hangup: 10
   voicemail: 3
   assistant-error: 2

📅 Today's Calls: 15

----------------------------------------------------------------------

📦 Order Records: 250
   OFD: 180
   Undelivered: 70

======================================================================
DIAGNOSTIC CHECK COMPLETE
======================================================================
```

---

### Step 4: Test Call Flow

1. **Login** karo frontend me
2. **OFD tab** pe jao
3. **Call All Now** button click karo
4. **Ek call** complete hone do
5. **Logout** karo
6. **Login** karo wapas
7. **Check karo** - Call history dikha?

**Agar dikha = Database working!** ✅
**Agar nahi dikha = Shell me check_database command run karo**

---

## Common Issues & Solutions

### Issue 1: "No such table: auth_user"
**Fix**: Run migrations manually in Shell:
```bash
python manage.py migrate
```

### Issue 2: "DATABASE_URL is NOT set"
**Fix**:
1. Go to PostgreSQL database page on Render
2. Copy "Internal Database URL"
3. Go to Web Service → Environment
4. Add variable: `DATABASE_URL` = `postgresql://...`
5. Save and redeploy

### Issue 3: "CallHistory not found"
**Fix**: Check if migrations applied:
```bash
python manage.py showmigrations orders
```
All should have [X] mark.

---

## Summary

**Automatic checks (after deployment)**:
- ✅ Build logs → Migration status
- ✅ Runtime logs → Database type
- ✅ Runtime logs → VAPI credentials

**Manual checks (if needed)**:
- 🔧 Shell → `python manage.py check_database`
- 🔧 Shell → `python manage.py migrate`

**Test**:
- 📞 Make a call → Logout → Login → Check history persists
