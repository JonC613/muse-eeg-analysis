# Google Drive Setup Troubleshooting Guide

## Issue: "Access blocked: Muse MM Importer has not completed the Google verification process"

This happens because Google requires apps to go through verification to access user data. For personal use, you can bypass this.

---

## Solution: Configure for Personal Use (Testing Mode)

### Step 1: OAuth Consent Screen Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select your project: **"Muse Mind Monitor Importer"**
3. Navigate to: **APIs & Services → OAuth consent screen**

4. **User Type:**
   - Select: **External** (not Internal)
   - Click **Create**

5. **App Information:**
   - App name: `Muse Mind Monitor Importer`
   - User support email: Your email
   - Developer contact: Your email
   - Click **Save and Continue**

6. **Scopes:**
   - Click **Add or Remove Scopes**
   - Find and select: `../auth/drive.readonly`
   - Click **Update**
   - Click **Save and Continue**

7. **Test Users (CRITICAL):**
   - Click **+ Add Users**
   - Enter YOUR Google email (the one you'll use to authorize)
   - Click **Add**
   - Click **Save and Continue**

8. **Summary:**
   - Review settings
   - Click **Back to Dashboard**

9. **Publishing Status:**
   - You should see: **Testing** (this is correct!)
   - Do NOT publish the app (not needed for personal use)

---

### Step 2: Re-create OAuth Credentials

Your current credentials may be tied to the old consent screen setup.

1. **Delete Old Credentials:**
   - Go to: **APIs & Services → Credentials**
   - Find your OAuth 2.0 Client ID
   - Click trash icon to delete it

2. **Create New OAuth Client ID:**
   - Click **+ Create Credentials**
   - Select **OAuth client ID**
   - Application type: **Desktop app**
   - Name: `Mind Monitor Desktop Client`
   - Click **Create**

3. **Download New Credentials:**
   - Click **Download JSON** button
   - Save as `gdrive_credentials.json`
   - Move to: `c:\dev\musepython\`
   - **Replace** the old file

4. **Delete Old Token:**
   ```powershell
   Remove-Item c:\dev\musepython\gdrive_token.json -ErrorAction SilentlyContinue
   ```

---

### Step 3: First Authentication (with Test User)

1. **Run the importer:**
   ```powershell
   python gdrive_mindmonitor_importer.py
   ```

2. **Browser Opens:**
   - Sign in with the Google account you added as **Test User**
   - You'll see: **"Google hasn't verified this app"**
   - Click **Advanced** (bottom left)
   - Click **Go to Muse Mind Monitor Importer (unsafe)**
   - This is safe - it's YOUR app in testing mode

3. **Grant Permissions:**
   - Review requested permissions
   - Click **Continue**
   - Should see: "Authentication successful!"

4. **Token Saved:**
   - `gdrive_token.json` created
   - Future runs won't need browser authentication

---

## Alternative: Manual File Import (Simpler)

If Google Drive setup is too complex, use manual import instead:

### Option A: Share Link Import

1. **In Mind Monitor:**
   - Export CSV
   - Upload to Google Drive manually
   - Get shareable link

2. **Download to PC:**
   - Open link in browser
   - Download CSV
   - Save to: `c:\dev\musepython\recordings\manual\`

3. **Import:**
   ```powershell
   python import_mindmonitor_manual.py
   ```

### Option B: Direct USB/Cloud Transfer

1. **Export from Mind Monitor**
2. **Transfer via:**
   - Email to yourself
   - OneDrive/Dropbox
   - USB cable to PC
   - AirDrop (Mac) / Nearby Share (Windows)

3. **Save to:** `c:\dev\musepython\recordings\manual\`
4. **Import:** Run `analyze_latest.bat`

---

## Testing Google Drive Setup

### Quick Test Script

```powershell
# Test Google Drive authentication
python -c "from gdrive_mindmonitor_importer import GoogleDriveImporter; importer = GoogleDriveImporter(); print('Authentication successful!' if importer.service else 'Failed')"
```

**Expected Output:**
```
Authenticating with Google Drive...
✓ Successfully authenticated!
Authentication successful!
```

**If Failed:**
- Check `gdrive_credentials.json` exists
- Verify test user added to OAuth consent screen
- Delete `gdrive_token.json` and try again

---

## Common Errors & Fixes

### Error: "No module named 'google'"
**Fix:**
```powershell
pip install google-auth google-auth-oauthlib google-auth-httplib2 google-api-python-client
```

### Error: "credentials.json not found"
**Fix:**
1. Download OAuth credentials from Cloud Console
2. Rename to `gdrive_credentials.json` (not `credentials.json`)
3. Place in `c:\dev\musepython\`

### Error: "invalid_grant" or "Token has been expired"
**Fix:**
```powershell
Remove-Item gdrive_token.json
python gdrive_mindmonitor_importer.py  # Re-authenticate
```

### Error: "Access blocked" (after following guide)
**Fix:**
1. Verify YOUR email is in Test Users list
2. Use the SAME Google account to authenticate
3. Wait 5 minutes for changes to propagate
4. Try again

### Error: "redirect_uri_mismatch"
**Fix:**
1. OAuth credentials must be type: **Desktop app**
2. NOT "Web application" or "Mobile app"
3. Re-create credentials as Desktop app

---

## Checking Your Setup

### 1. Verify Files Exist
```powershell
Get-ChildItem c:\dev\musepython\gdrive_*.json
```

**Should show:**
- `gdrive_credentials.json` (OAuth client credentials)
- `gdrive_token.json` (after first auth - may not exist yet)

### 2. Verify OAuth Consent Screen
- Go to: [OAuth Consent Screen](https://console.cloud.google.com/apis/credentials/consent)
- Should show:
  - User Type: **External**
  - Publishing Status: **Testing**
  - Test Users: **Your email listed**

### 3. Verify Google Drive API Enabled
```powershell
# Check in Cloud Console
# APIs & Services → Enabled APIs & services
# Should see: "Google Drive API"
```

---

## Recommendation: Skip Google Drive (for now)

**Manual import is faster and simpler:**

1. Export CSV from Mind Monitor
2. Copy to `recordings\manual\`
3. Run `analyze_latest.bat`
4. Done!

**Advantages:**
- ✓ No OAuth setup needed
- ✓ No Google Cloud account required
- ✓ Works offline
- ✓ Faster workflow
- ✓ No API rate limits

**Only use Google Drive if:**
- You want automatic cloud backup
- You record on multiple devices
- You need remote access to data

---

## Success Checklist

When Google Drive setup works correctly:

1. Run: `python gdrive_mindmonitor_importer.py`
2. See: List of Mind Monitor CSV files from your Drive
3. Select file number or "all"
4. Files auto-download and convert
5. Saved to: `recordings\YYYY-MM-DD\`

**If this works, you're done!**

---

## Getting Help

If still having issues:

1. **Check Python version:**
   ```powershell
   python --version  # Should be 3.8+
   ```

2. **Check Google API packages:**
   ```powershell
   pip show google-api-python-client google-auth
   ```

3. **Check Cloud Console:**
   - Project name correct?
   - Google Drive API enabled?
   - OAuth consent screen configured?
   - Test user added?

4. **Try manual import instead:**
   - Much simpler
   - Works identically
   - Recommended for most users

---

## Summary

**For Personal Use:**
- OAuth consent screen in **Testing** mode (not published)
- Add YOUR email as Test User
- Use same email to authenticate
- Click "Advanced → Go to app (unsafe)" when prompted

**Simpler Alternative:**
- Use manual import via `recordings\manual\` folder
- Run `analyze_latest.bat` for one-click analysis
- Same results, less complexity

**Both methods work with your optimized Mind Monitor workflow!**
