---
title: Two-Factor Authentication (2FA)
description: Enable TOTP-based two-factor authentication on your CoPilot account using an authenticator app.
---

**Menu:** Profile → Security tab → Two-Factor Authentication

**Best for:** All users

Two-factor authentication (2FA) adds a second verification step every time you log in. After entering your password (or completing SSO), you must also provide a 6-digit code from an authenticator app on your phone or computer.

CoPilot uses the **TOTP** (Time-based One-Time Password) standard, which is supported by all major authenticator apps:

- [Google Authenticator](https://support.google.com/accounts/answer/1066447)
- [Microsoft Authenticator](https://www.microsoft.com/en-us/security/mobile-authenticator-app)
- [Authy](https://authy.com/)
- [1Password](https://1password.com/)
- Any TOTP-compatible app

---

## Enable 2FA on your account

<Steps>

<Step title="Open your profile">
  Click your username or avatar in the top-right corner and select **Profile**, then switch to the **Security** tab.
</Step>

<Step title="Start setup">
  Click **Enable Two-Factor Authentication**. CoPilot generates a unique secret and displays a QR code.
</Step>

<Step title="Scan the QR code">
  Open your authenticator app and scan the QR code displayed on screen.

  > **Can't scan?** Click **Show manual entry key** to reveal the secret as a text string. Enter it manually in your authenticator app.

  <Warning>
    Make sure your device clock is accurate. TOTP codes are time-sensitive and allow only a **±30 second** tolerance window. If your clock is off, codes will be rejected.
  </Warning>
</Step>

<Step title="Verify the code">
  Enter the 6-digit code currently shown in your authenticator app and click **Verify & Enable**.

  This confirms that your app is configured correctly and activates 2FA on your account.
</Step>

<Step title="Save your backup codes">
  After verification, CoPilot displays **8 one-time backup codes**. These are your emergency access method if you lose your authenticator device.

  - Click **Copy all** to copy the codes to your clipboard.
  - Click **Download .txt** to save them as a text file.
  - Store them somewhere safe (e.g. a password manager or a printed sheet in a secure location).

  <Warning>
    Backup codes are shown **only once** during setup. If you lose them and lose access to your authenticator app, you will be locked out of your account.
  </Warning>
</Step>

</Steps>

---

## Log in with 2FA

Once 2FA is enabled, the login flow changes:

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│  Enter       │────▶│  Enter       │────▶│  Session     │
│  username &  │     │  6-digit     │     │  created     │
│  password    │     │  TOTP code   │     │              │
└──────────────┘     └──────────────┘     └──────────────┘
```

1. Enter your username and password as usual, then click **Sign in**.
2. CoPilot recognizes that your account has 2FA enabled and shows a verification form.
3. Open your authenticator app and enter the current 6-digit code, then click **Verify**.
4. You are logged in.

> **SSO + 2FA:** If you sign in via SSO (Azure, Google, or Cloudflare Access), you will still be prompted for the TOTP code after the identity provider authenticates you.

---

## Use a backup code

If you cannot access your authenticator app (lost phone, new device, etc.), you can use one of your backup codes instead:

1. On the 2FA verification screen, click **Use a backup code instead**.
2. Enter one of your saved backup codes (e.g. `ABCD1234EF`).
3. Click **Use backup code**.

Each backup code can only be used **once**. After use, it is permanently invalidated.

---

## Regenerate backup codes

If you have used some of your backup codes or suspect they have been compromised:

1. Go to **Profile** → **Security** tab.
2. Click **Regenerate backup codes**.
3. Enter your current 6-digit TOTP code to confirm your identity.
4. CoPilot generates 8 **new** backup codes. All previous codes are invalidated immediately.
5. Save the new codes (copy or download).

---

## Disable 2FA

1. Go to **Profile** → **Security** tab.
2. Click **Disable 2FA**.
3. Confirm by entering your current TOTP code **or** a backup code.
4. 2FA is removed from your account. Future logins will only require a password.

---

## Brute-force protection

CoPilot enforces rate limiting on 2FA verification:

- After **5 failed attempts**, your account is locked out of 2FA verification for **15 minutes**.
- This applies to both TOTP code entry and backup code entry.
- The lockout resets automatically after the timeout or on a successful verification.

---

## FAQ

<AccordionGroup>

<Accordion title="What happens if I lose my phone?">
  Use one of your backup codes to log in, then either regenerate new backup codes or disable 2FA and set it up again with your new device.
</Accordion>

<Accordion title="Can an admin disable 2FA for a user?">
  Currently, each user manages their own 2FA. If a user is locked out with no backup codes, an admin can reset their account through the database.
</Accordion>

<Accordion title="Does 2FA apply to API access?">
  2FA is enforced during interactive login only. API tokens issued after a successful login (including 2FA) remain valid for their normal lifetime.
</Accordion>

<Accordion title="Which authenticator app should I use?">
  Any TOTP-compatible app works. Popular choices include Google Authenticator, Microsoft Authenticator, Authy, and 1Password. They are all interchangeable — pick whichever you prefer.
</Accordion>

<Accordion title="My codes are always rejected">
  Check that your device clock is accurate. TOTP codes depend on precise time synchronization (within ±30 seconds). On mobile, enable automatic time in your device settings.
</Accordion>

</AccordionGroup>

---

## Environment variables (admin reference)

| Variable | Purpose | Default |
|---|---|---|
| `TOTP_ENCRYPTION_KEY` | Fernet key used to encrypt TOTP secrets at rest in the database. | Derived from `JWT_SECRET` |

<Warning>
  Once users have enrolled in 2FA, **do not change** `TOTP_ENCRYPTION_KEY`. Changing it will make all existing TOTP secrets unreadable, locking enrolled users out of 2FA verification.
</Warning>
