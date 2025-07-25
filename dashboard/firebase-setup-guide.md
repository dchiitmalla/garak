# Firebase Authentication Setup Guide

This guide provides step-by-step instructions for setting up Firebase authentication for the Garak Dashboard.

## Prerequisites

- Google account
- Access to [Firebase Console](https://console.firebase.google.com)

## Step 1: Create Firebase Project

1. Go to [Firebase Console](https://console.firebase.google.com)
2. Click **"Create a project"** or **"Add project"**
3. Enter a project name (e.g., "garak-dashboard")
4. Choose whether to enable Google Analytics (optional)
5. Click **"Create project"**
6. Wait for the project to be created and click **"Continue"**

## Step 2: Enable Authentication

1. In your Firebase project, click **"Authentication"** in the left sidebar
2. Click **"Get started"** if this is your first time
3. Go to the **"Sign-in method"** tab
4. Enable the following providers:
   - **Email/Password**: Click → Toggle to enable → Save
   - **Google**: Click → Enable → Choose support email → Save

## Step 3: Register Web App

1. Go to **Project Settings** (gear icon in left sidebar)
2. Go to the **"General"** tab
3. Scroll down to **"Your apps"** section
4. Click **"Add app"** → Select **"Web"** (</> icon)
5. Enter an app nickname (e.g., "Garak Dashboard")
6. **Do not check** "Also set up Firebase Hosting"
7. Click **"Register app"**
8. **Copy the Firebase configuration object** - you'll need these values:
   ```javascript
   const firebaseConfig = {
     apiKey: "your-api-key",
     authDomain: "your-project-id.firebaseapp.com",
     projectId: "your-project-id",
     storageBucket: "your-project-id.appspot.com",
     messagingSenderId: "123456789012",
     appId: "your-app-id"
   };
   ```
9. Click **"Continue to console"**

## Step 4: Generate Service Account Key

1. Go to **Project Settings** → **"Service accounts"** tab
2. Click **"Generate new private key"**
3. Click **"Generate key"** in the confirmation dialog
4. A JSON file will be downloaded - **save this file securely**
5. Rename the file to `firebase-sa.json`
6. Place it in your dashboard directory (same level as `app.py`)

## Step 5: Configure Environment Variables

Create a `.env` file in your dashboard directory or set environment variables:

```bash
# Firebase Configuration (from Step 3)
export FIREBASE_API_KEY="your-api-key-from-config"
export FIREBASE_AUTH_DOMAIN="your-project-id.firebaseapp.com"
export FIREBASE_PROJECT_ID="your-project-id"
export FIREBASE_STORAGE_BUCKET="your-project-id.appspot.com"
export FIREBASE_MESSAGING_SENDER_ID="your-messaging-sender-id"
export FIREBASE_APP_ID="your-app-id"

# Service Account File Path (from Step 4)
export FIREBASE_CREDENTIALS="./firebase-sa.json"

# Ensure authentication is enabled
export DISABLE_AUTH="false"
```

## Step 6: Test Authentication

1. Start your dashboard application:
   ```bash
   cd dashboard
   python app.py
   ```

2. Navigate to `http://localhost:8000`

3. You should be redirected to the login page

4. Test both authentication methods:
   - **Email/Password**: Create an account through Firebase Console or use the login form
   - **Google Sign-in**: Click the Google button

5. Check the `/auth/status` endpoint for configuration status:
   ```bash
   curl http://localhost:8000/auth/status
   ```

## Step 7: Add Users (Optional)

### Option 1: Through Firebase Console
1. Go to **Authentication** → **"Users"** tab
2. Click **"Add user"**
3. Enter email and password
4. Click **"Add user"**

### Option 2: Let users self-register
Users can create accounts using the login page's email/password form or Google sign-in.

## Troubleshooting

### Common Issues

**"Configuration error: Missing Firebase configuration"**
- Check that all `FIREBASE_*` environment variables are set
- Verify values match your Firebase project configuration

**"Could not find Firebase service account file"**
- Ensure `firebase-sa.json` is in the correct location
- Check `FIREBASE_CREDENTIALS` environment variable points to the right path
- Verify the file is valid JSON

**"Firebase initialization error"**
- Check network connectivity
- Verify API key is correct and hasn't been restricted
- Ensure project ID matches between environment variables and service account file

**"Authentication required" when accessing dashboard**
- Make sure you're logged in
- Check browser developer console for JavaScript errors
- Verify Firebase configuration in the login page source

### Debug Steps

1. **Check application logs** for detailed error messages
2. **Visit `/auth/status`** endpoint to see system status
3. **Enable debug mode**: Set `DEBUG=true` environment variable
4. **Browser developer tools**: Check console for JavaScript errors
5. **Firebase Console**: Check Authentication logs for sign-in attempts

## Security Considerations

### Development vs Production

**Development**:
- Can use `DISABLE_AUTH=true` to bypass authentication
- Service account file can be in project directory
- Debug mode enabled

**Production**:
- Never use `DISABLE_AUTH=true`
- Store service account key securely (not in source control)
- Use environment variables for all configuration
- Enable proper CORS settings
- Consider Firebase security rules

### Authorized Domains

For production deployment, add your domain to Firebase:
1. Go to **Authentication** → **"Settings"** tab
2. Scroll to **"Authorized domains"**
3. Add your production domain (e.g., `yourdomain.com`)

### API Key Restrictions

Consider restricting your Firebase API key:
1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Select your Firebase project
3. Go to **APIs & Services** → **"Credentials"**
4. Click on your API key
5. Add application restrictions and API restrictions as needed

## Environment Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `FIREBASE_API_KEY` | Firebase API key | `AIzaSyXXXXXXXXXXXXXXXXXXXXX` |
| `FIREBASE_AUTH_DOMAIN` | Authentication domain | `my-project.firebaseapp.com` |
| `FIREBASE_PROJECT_ID` | Firebase project ID | `my-project-123456` |
| `FIREBASE_STORAGE_BUCKET` | Storage bucket | `my-project.appspot.com` |
| `FIREBASE_MESSAGING_SENDER_ID` | Messaging sender ID | `123456789012` |
| `FIREBASE_APP_ID` | Firebase app ID | `1:123456789012:web:abcdef` |
| `FIREBASE_CREDENTIALS` | Path to service account file | `./firebase-sa.json` |
| `DISABLE_AUTH` | Disable authentication | `false` (or `true` for dev) |

## Next Steps

After successful setup:
1. Test user registration and login
2. Configure user roles if needed
3. Set up proper backup for your Firebase project
4. Consider implementing additional security measures
5. Monitor authentication logs in Firebase Console

For additional help, refer to the [Firebase Documentation](https://firebase.google.com/docs/auth) or check the dashboard's `/auth/status` endpoint for real-time configuration status.