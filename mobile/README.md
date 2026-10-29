# HRMS mobile voice-call demo

This is a native Expo/React Native client for the existing HRMS LiveKit voice
agent. It does not create a second agent and does not depend on WhatsApp or Meta
business verification.

## Run it

From this directory:

```bash
cd mobile
npm install
```

Set the URL of the running Next.js server:

```bash
# Android emulator
export EXPO_PUBLIC_API_BASE_URL=http://10.0.2.2:3001

# Physical phone: use the computer's LAN address instead
# export EXPO_PUBLIC_API_BASE_URL=http://192.168.x.x:3001
```

Install a native development build; Expo Go cannot load the required WebRTC
native module:

```bash
npx expo run:android
# or
npx expo run:ios
```

Then start the Metro server:

```bash
npm start
```

Tap **Sign in and start call**, complete the existing AgentLabs sign-in page,
allow the microphone, and speak English or Kannada. The app uses a one-time
server handoff; it does not store or receive the HRMS browser cookie.

The mobile app requests a short-lived token from:

```text
POST /api/mobile/token
```

The endpoint redeems the one-time code issued by HRMS Core and embeds the
encrypted HRMS session in the LiveKit participant attributes for the existing
agent. Configure `EXPO_PUBLIC_HRMS_CORE_URL` to a Core URL reachable by the
phone, and set the same `HRMS_MOBILE_HANDOFF_SECRET` in the Next.js app and
HRMS Core.
