# HRMS Voice Agent Demo

Role-aware voice assistance for an HRMS portal, with LiveKit voice sessions, Kannada/English speech providers, WhatsApp integration, and a companion mobile voice-call app.

## What is included

- Next.js HRMS portal with employee and HR experiences
- LiveKit token exchange that keeps the HRMS session cookie server-side
- Python voice worker with role-scoped tools and HRMS backend integration
- Optional WhatsApp text/audio bridge using Sarvam speech services
- React Native mobile voice-call client

## Local setup

```bash
npm install
cp .env.example .env.local
npm run dev
```

For the Python voice worker, install the packages in `agent/requirements.txt` and run:

```bash
npm run agent:dev
```

Never commit `.env.local`, access tokens, service-account files, or authenticated HRMS session cookies. Configure provider credentials only in ignored environment files.

## Verification

```bash
npm run test:all
npm run typecheck
npm run build
```

This repository is a demo/integration reference. Production deployments should add provider-specific secret management, webhook verification, rate limits, and operational monitoring.
