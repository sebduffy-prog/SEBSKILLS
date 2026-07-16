---
name: mobile-app-scaffold
category: mobile
description: >
  Verb-first: scaffold a real React Native app with Expo, then build, submit,
  update, and push-notify it via EAS — the only path in this library to a
  shippable iOS/Android deliverable. Trigger when the user says "mobile app",
  "React Native", "Expo", "EAS build", "iOS/Android app", "TestFlight", "App
  Store / Play Store submit", "push notifications", "OTA update", or wants a
  phone-installable prototype from a brief. Gives exact create-expo-app, eas
  build/submit/update commands, eas.json profiles, and expo-notifications code —
  grounded against real Expo/EAS docs, not fabricated.
when_to_use:
  - Turning an idea or brief into an installable iOS/Android app prototype
  - Setting up EAS Build to produce a real .ipa / .aab / .apk in the cloud (no local Xcode/Android Studio toolchain)
  - Submitting a built app to TestFlight, the App Store, or Google Play via eas submit
  - Shipping over-the-air JS/asset updates to an already-installed app with eas update
  - Wiring Expo push notifications (token capture + send via the Expo push API)
  - Producing a client-demo build a stakeholder can install on their own phone
when_not_to_use:
  - Building a responsive website or web-only UI — use frontend-design
  - Deploying a Node/Next backend or API — use use-railway or the vercel tools
  - Pure static HTML/CSS artifacts or landing pages — use web-artifacts-builder
  - A bare React Native app without Expo tooling — this skill assumes the Expo/EAS managed workflow
keywords:
  - react-native
  - expo
  - eas
  - eas-build
  - eas-submit
  - eas-update
  - mobile
  - ios
  - android
  - testflight
  - app-store
  - play-store
  - push-notifications
  - expo-notifications
  - ota-update
  - scaffold
similar_to: []
inputs_needed: >
  Node 18+ and npm; a free Expo account (expo.dev) for EAS; for store submission
  an Apple Developer Program membership ($99/yr) and/or Google Play Console
  account ($25 one-time); no Xcode/Android Studio required (cloud builds).
produces: >
  A runnable Expo React Native project, an eas.json with build/submit profiles,
  cloud-built .ipa/.aab/.apk artifacts, optional store submissions, OTA update
  channels, and push-notification token capture + send code.
status: stable
owner: seb.duffy
updated: 2026-07-10
---

# Mobile App Scaffold (Expo + EAS)

Go from brief to a phone-installable iOS/Android app using Expo's managed
workflow and EAS (Expo Application Services) for cloud builds, store
submission, over-the-air updates, and push. No local Xcode or Android Studio
toolchain is required — EAS builds on Expo's servers.

## When to use

Reach for this whenever the deliverable must run on a real phone: a client demo
build, a TestFlight beta, or a full store submission. It is the only route in
SEBSKILLS to a native mobile artifact. For web UIs, use `frontend-design`; for
backends, `use-railway`.

## Prerequisites (honest)

- **Node.js 18 or newer** and npm (`node --version`). Expo SDK tracks recent Node LTS.
- **An Expo account** (free) — sign up at https://expo.dev. Needed for any `eas` command.
- **EAS CLI**: `npm install --global eas-cli` (or run ad-hoc with `npx eas-cli@latest`).
- **For iOS store/TestFlight**: an Apple Developer Program membership ($99/yr).
  EAS can manage signing credentials for you (generates certs/profiles).
- **For Google Play**: a Play Console account ($25 one-time) and a service-account JSON key.
- Cloud builds run on Expo's free tier with a monthly build quota; heavy use needs a paid plan.
- This machine (macOS, python3.9, no brew) can author the project and run the CLI,
  but the actual native compile happens in the cloud — that's the point.

## Recipe 1 — Scaffold the project

```sh
# Interactive template picker (recommended); creates a git repo + installs deps
npx create-expo-app@latest my-app
cd my-app

# Run it immediately in Expo Go on your phone or a simulator:
npx expo start
```

Templates worth knowing (pass with `--template`): `default` (file-based expo-router,
TypeScript), `blank`, `blank-typescript`, `tabs`. Example:

```sh
npx create-expo-app@latest my-app --template blank-typescript
```

Edit `app.json` (or `app.config.js`) — set `expo.name`, `expo.slug`, `expo.ios.bundleIdentifier`
(e.g. `com.vccp.myapp`) and `expo.android.package`. These are required before building.

## Recipe 2 — Configure EAS Build

```sh
eas login                 # authenticate; eas whoami to verify
eas build:configure       # creates eas.json and links/creates the EAS project id
```

`eas build:configure` writes a starter `eas.json`. A typical set of profiles:

```json
{
  "cli": { "version": ">= 12.0.0" },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "distribution": "internal",
      "android": { "buildType": "apk" }
    },
    "production": {
      "autoIncrement": true
    }
  },
  "submit": {
    "production": {}
  }
}
```

- `development` → a dev client build for fast iteration with a custom native runtime.
- `preview` → an **internal-distribution** build: an installable `.apk` (Android) or
  ad-hoc `.ipa` (iOS) a stakeholder can side-load without going through the stores.
  This is the go-to for client demos.
- `production` → store-ready `.aab` (Android App Bundle) / `.ipa`.

## Recipe 3 — Build in the cloud

```sh
# Client-demo installable build (fast, no store review):
eas build --profile preview --platform android
eas build --profile preview --platform ios

# Store-ready artifacts:
eas build --profile production --platform all
```

On the first iOS build EAS prompts to manage signing — accept "let EAS handle
credentials" unless the client insists on their own certs. On Android, choose
"Generate new keystore" (EAS stores it). Watch progress in the terminal or at
https://expo.dev/builds. When done you get a download URL for the artifact; the
Android `preview` `.apk` can be installed directly, iOS internal builds via a
registered-device link.

## Recipe 4 — Submit to the stores

```sh
# Uploads the latest matching build to App Store Connect / Play Console:
eas submit --profile production --platform ios
eas submit --profile production --platform android
```

iOS submission lands the build in App Store Connect / TestFlight (you still
promote it to a store listing in App Store Connect). Android needs a Google
service-account JSON referenced under `submit.production.android.serviceAccountKeyPath`
in `eas.json`.

## Recipe 5 — Over-the-air updates (no rebuild)

Ship JS/asset changes to installed apps without a new store review:

```sh
npx expo install expo-updates
eas update:configure                     # sets up channels + runtimeVersion
eas update --branch production --message "Fix copy on home screen"
```

OTA updates only cover JS/assets — any change to native modules or app config
still requires a full `eas build`. Match the update's `runtimeVersion` to the
installed build or it won't apply.

## Recipe 6 — Push notifications

Install the packages, capture a token, and send via the Expo push service.

```sh
npx expo install expo-notifications expo-device expo-constants
```

Client — request permission and get the Expo push token (verified API):

```ts
import * as Notifications from 'expo-notifications';
import * as Device from 'expo-device';
import Constants from 'expo-constants';

export async function registerForPushNotificationsAsync(): Promise<string | null> {
  if (!Device.isDevice) return null; // push needs a physical device

  const { status: existing } = await Notifications.getPermissionsAsync();
  let status = existing;
  if (existing !== 'granted') {
    status = (await Notifications.requestPermissionsAsync()).status;
  }
  if (status !== 'granted') return null;

  const projectId =
    Constants?.expoConfig?.extra?.eas?.projectId ??
    Constants?.easConfig?.projectId;

  const token = (
    await Notifications.getExpoPushTokenAsync({ projectId })
  ).data;
  return token; // e.g. ExponentPushToken[xxxxxxxx]
}
```

Server — send to the Expo push API (verified endpoint `https://exp.host/--/api/v2/push/send`):

```sh
curl -H "Content-Type: application/json" \
     -H "Accept-encoding: gzip, deflate" \
     -X POST https://exp.host/--/api/v2/push/send \
     -d '{
       "to": "ExponentPushToken[xxxxxxxx]",
       "sound": "default",
       "title": "Hello from EAS",
       "body": "Your build is ready.",
       "data": { "screen": "home" }
     }'
```

For production iOS push you must upload an APNs key and for Android a Firebase
(FCM v1) service-account credential — do this once with `eas credentials`.

## Verify

- `node --version` → 18+; `eas whoami` → prints your Expo username (auth OK).
- `npx expo start` opens the dev server and the app loads in Expo Go / simulator.
- `eas build:list` shows your builds and their status (finished / errored).
- A `preview` Android build yields a downloadable `.apk` that installs on a device.
- `eas update --branch preview` then reload the app → the change appears without a rebuild.
- Push: `getExpoPushTokenAsync` returns an `ExponentPushToken[...]`; the curl POST
  returns `{"data":{"status":"ok", ...}}` and the notification arrives.

## Pitfalls

- **Expo Go vs dev client**: Expo Go can't load custom native modules. Once you add
  a library with native code, build a `development` profile dev client instead.
- **Missing bundle id / package**: `eas build` fails if `ios.bundleIdentifier` or `android.package` are unset in app config. Set them before the first build.
- **Push tokens need a physical device** — simulators can't register; guard with `Device.isDevice`.
- **OTA won't fix native changes**: a new native dependency or app.json native config change
  requires a new `eas build`, not an `eas update`.
- **runtimeVersion mismatch** silently drops updates — keep build and update on the same runtime.
- **Build quota**: the free EAS tier has a monthly cloud-build limit; batch builds or upgrade.
- **iOS submission ≠ live**: `eas submit` only uploads to App Store Connect/TestFlight; you still submit for review and release manually there.
- **Don't commit credentials**: keystores, APNs keys, and Play service-account JSON stay out of git — let EAS store them or reference paths outside the repo.
