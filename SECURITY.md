# Security Guidelines

## 🔐 Protecting Sensitive Information

### What NOT to commit to GitHub:

❌ **NEVER commit these files:**
- `.env` files (contain API keys and secrets)
- `db.sqlite3` (contains sensitive database data)
- Any file with real API keys, passwords, or tokens

### What IS safe to commit:

✅ **Safe to commit:**
- `.env.example` (template with placeholder values)
- Source code without hardcoded credentials
- Configuration files with environment variable references

---

## 🛡️ API Keys & Secrets

### iThink Logistics:
- **Access Token:** Keep private, regenerate if exposed
- **Secret Key:** Never share publicly

### VAPI.ai:
- **Private Key:** Used for API authentication
- **Assistant ID:** Safe to share within team
- **Phone Number ID:** Safe to share within team

---

## 🚨 What to do if API keys are exposed:

1. **Immediately regenerate keys** from provider dashboards:
   - iThink: https://my.ithinklogistics.com
   - VAPI: https://dashboard.vapi.ai

2. **Update .env files** with new keys

3. **Redeploy application** with new keys

4. **Do NOT commit new keys** to git

---

## 📝 Environment Variables for Render Deployment:

When deploying to Render, add these environment variables in the dashboard:

```
ITHINK_ACCESS_TOKEN=<your_token>
ITHINK_SECRET_KEY=<your_secret>
VAPI_PRIVATE_KEY=<your_private_key>
VAPI_PHONE_NUMBER_ID=<your_phone_id>
VAPI_ASSISTANT_ID=<your_assistant_id>
ALLOWED_HOSTS=your-app.onrender.com
DEBUG=False
```

**NEVER add these in the code or commit them!**

---

## 🔒 Best Practices:

1. ✅ Always use environment variables for secrets
2. ✅ Keep `.env` in `.gitignore`
3. ✅ Use different keys for dev/production
4. ✅ Rotate API keys regularly
5. ✅ Never share `.env` files via chat/email
6. ✅ Review commits before pushing

---

## 📞 Contact

If you accidentally committed sensitive data:
1. Remove it from git history immediately
2. Regenerate all exposed keys
3. Force push cleaned repository
