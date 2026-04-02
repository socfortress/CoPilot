---
title: Single Sign-On (SSO)
description: Configure SSO with Azure Entra ID, Google, or Cloudflare Access so users can log in via their identity provider.
---

**Menu:** Users → Single Sign-On (SSO) Configuration

**Best for:** Admin

CoPilot supports three SSO providers out of the box. Once configured, users see **Sign in with …** buttons on the login page alongside the standard username/password form.

| Provider | Protocol | How it works |
|---|---|---|
| **Azure Entra ID** | OAuth 2.0 / OIDC | User is redirected to Microsoft, then back to CoPilot with an authorization code. |
| **Google** | OAuth 2.0 / OIDC | Same redirect flow via Google accounts. |
| **Cloudflare Access** | JWT assertion | Cloudflare sits in front of CoPilot and injects a signed header; no redirect needed from the user's perspective. |

---

## How SSO login works

```
┌──────────┐      ┌───────────────────┐      ┌──────────────┐
│  Browser  │─────▶│  Identity Provider │─────▶│   CoPilot    │
│  (login   │      │  (Azure / Google / │      │   backend    │
│   page)   │◀─────│   Cloudflare)      │◀─────│              │
└──────────┘      └───────────────────┘      └──────────────┘

1. User clicks an SSO button on the login page.
2. Browser redirects to the identity provider.
3. User authenticates with their corporate credentials.
4. Provider redirects back to CoPilot with a signed token.
5. CoPilot verifies the token, checks the email allowlist,
   auto-provisions a local account if needed, and issues a session.
```

> **Auto-provisioning:** The first time an allowed email logs in via SSO, CoPilot automatically creates a local user account with the role you assigned in the allowlist. No manual user creation is required.

---

## Prerequisites

- Your CoPilot instance must be reachable at a stable URL (HTTPS recommended).
- You need **admin** access in CoPilot.
- You need admin access to the identity provider you want to configure (Azure portal, Google Cloud Console, or Cloudflare Zero Trust dashboard).

---

## Step 1 — Enable SSO globally

1. Go to **Users** in the top navigation.
2. Scroll to the **Single Sign-On (SSO) Configuration** card.
3. Toggle **Enable SSO** to on.

> This toggle controls whether SSO login buttons appear on the login page. You can enable the global toggle and then selectively enable individual providers.

---

## Step 2 — Configure a provider

### Azure Entra ID

<Steps>

<Step title="Register an application in Azure">
  Go to [portal.azure.com](https://portal.azure.com) → **Azure Active Directory** → **App registrations** → **New registration**.

  - **Name:** e.g. `CoPilot SSO`
  - **Supported account types:** *Accounts in this organizational directory only*
  - Click **Register**.
</Step>

<Step title="Copy IDs">
  From the app's **Overview** page:
  - Copy the **Application (client) ID** → you will paste this as **Client ID** in CoPilot.
  - Copy the **Directory (tenant) ID** → you will paste this as **Tenant ID** in CoPilot.
</Step>

<Step title="Create a client secret">
  Go to **Certificates & secrets** → **New client secret**. Copy the **Value** (not the Secret ID) → you will paste this as **Client Secret** in CoPilot.
</Step>

<Step title="Set the redirect URI">
  Go to **Authentication** → **Add a platform** → **Web**. Set the redirect URI to:

  ```
  https://<your-copilot-domain>/api/auth/sso/azure/callback
  ```

  > **Tip:** In CoPilot, the **Auto-fill** button next to the Redirect URI field will populate this automatically based on your current domain.
</Step>

<Step title="Add the email claim">
  Go to **Token configuration** → **Add optional claim** → select **ID** token type → check **email** → **Add**.
</Step>

<Step title="Fill in CoPilot">
  Back in CoPilot under the **Azure Entra ID** section:
  1. Toggle **Enable Azure SSO** to on.
  2. Paste the **Tenant ID**, **Client ID**, and **Client Secret**.
  3. Confirm the **Redirect URI** matches what you set in Azure.
  4. Click **Save SSO Settings**.
</Step>

</Steps>

---

### Google

<Steps>

<Step title="Create OAuth credentials">
  Go to [Google Cloud Console](https://console.cloud.google.com) → **APIs & Services** → **Credentials** → **Create Credentials** → **OAuth client ID**.

  - **Application type:** Web application
  - **Authorized redirect URIs:** add:

  ```
  https://<your-copilot-domain>/api/auth/sso/google/callback
  ```
</Step>

<Step title="Copy credentials">
  Copy the **Client ID** and **Client Secret** shown after creation.
</Step>

<Step title="Enable People API">
  In the Cloud Console go to **APIs & Services** → **Library** → search for **People API** → **Enable**. This is required for CoPilot to retrieve the user's email and profile.
</Step>

<Step title="Fill in CoPilot">
  Under the **Google (OAuth2 / OIDC)** section:
  1. Toggle **Enable Google SSO** to on.
  2. Paste the **Client ID** and **Client Secret**.
  3. Confirm the **Redirect URI**.
  4. Click **Save SSO Settings**.
</Step>

</Steps>

---

### Cloudflare Access

Cloudflare Access works differently from the other providers. Instead of redirecting the user, Cloudflare sits **in front** of CoPilot as a reverse proxy and injects a cryptographically signed JWT header (`Cf-Access-Jwt-Assertion`) into every request. CoPilot verifies this header — it is impossible to forge without Cloudflare's private key.

<Steps>

<Step title="Create a Cloudflare Access application">
  In the **Cloudflare Zero Trust** dashboard go to **Access** → **Applications** → **Add an application** → **Self-hosted**.

  - Set the domain to your CoPilot URL (e.g. `copilot.example.com`).
  - Connect your identity provider (e.g. Entra ID, Google, GitHub) under **Identity providers**.
</Step>

<Step title="Copy the Application Audience">
  After creating the app open it → **Overview** → copy the **Application Audience (AUD) Tag**.
</Step>

<Step title="Copy your Team Domain">
  Go to **Settings** → **Custom Pages** and copy your team domain (e.g. `myteam.cloudflareaccess.com`).
</Step>

<Step title="Fill in CoPilot">
  Under the **Cloudflare Access (JWT Assertion)** section:
  1. Toggle **Enable Cloudflare Access** to on.
  2. Paste the **Team Domain** and **Application Audience (AUD)**.
  3. Click **Save SSO Settings**.
</Step>

</Steps>

> With Cloudflare Access there is no client secret — authentication is handled entirely by the signed JWT header.

---

## Step 3 — Manage the email allowlist

SSO users can only log in if their email address is in the **SSO Allowed Emails** list. This prevents unauthorized accounts in your identity provider from accessing CoPilot.

1. Scroll to the **SSO Allowed Emails** card (below the SSO configuration card).
2. Click **Add Email**.
3. Enter the user's email address and select a **role**:
   - **Admin** — full platform access
   - **Analyst** (default) — standard operator access
4. Click **Add Email**.

| Column | Description |
|---|---|
| **Email** | The email address permitted to log in via SSO. |
| **Role** | The CoPilot role assigned on first login. |
| **Added** | Timestamp of when the entry was created. |

To remove an email, click the delete button in the row.

> **Important:** Only emails in this list can log in via SSO. If a user's email is not listed, they will be denied access even if they authenticate successfully with the identity provider.

---

## How SSO interacts with 2FA

If a user has [two-factor authentication](/user/ui/two-factor-authentication) enabled on their CoPilot account, SSO login will still require the second factor:

1. User authenticates via the identity provider.
2. CoPilot verifies the SSO token and finds that the user has 2FA enabled.
3. The user is prompted for their TOTP code (or a backup code) before the session is created.

This means SSO and 2FA are **complementary** — SSO simplifies *how* users authenticate with their identity, while 2FA adds a second verification step.

---

## Environment variables

| Variable | Purpose | Default |
|---|---|---|
| `SSO_STATE_SECRET` | HMAC key used to sign OAuth2 state tokens (prevents CSRF). | Falls back to `JWT_SECRET` |

> The state token is stateless — it encodes a timestamp and is signed with HMAC-SHA256. It expires after 10 minutes.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| SSO buttons don't appear on the login page | Global SSO toggle is off, or no individual provider is enabled. | Enable SSO globally **and** enable at least one provider. |
| "Email not in allowed list" after SSO login | The user's email is not in the SSO Allowed Emails list. | Add the email address to the allowlist. |
| Azure callback fails with "invalid redirect URI" | Redirect URI in Azure app registration doesn't match CoPilot. | Copy the redirect URI from CoPilot (use **Auto-fill**) and paste it exactly into Azure. |
| Google callback fails | People API not enabled or redirect URI mismatch. | Enable the People API in Google Cloud Console and verify the redirect URI. |
| Cloudflare "authentication failed" | CoPilot is not behind Cloudflare Access, or the AUD/team domain is wrong. | Ensure traffic goes through Cloudflare Access and double-check the AUD tag and team domain. |
