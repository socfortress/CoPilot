# Customer Portal

**Menu:** User menu → Customer Portal

**Best for:** Admin/Engineer + customer-facing workflows

![Customer Portal](../../assets/ui/customer-portal.png)

## Branding: global defaults + per-customer overrides

This page sets the **global default** branding (title, logo, brand color) for the
Customer Portal. It is what the portal login page always shows — no customer is
known before authentication — and what every customer sees unless overridden.

A single customer can override it: **Customers → &lt;customer&gt; → Portal Branding**.

- **Inherit** (default) — the customer uses the global settings above.
- **Custom** — set a customer-specific title, logo and/or brand color. Any field
  left empty keeps inheriting the global value, so you can override just the logo
  and keep the global title.

Switching back to **Inherit**, or using **Remove override**, returns the customer
to the global defaults; the portal picks the change up on the customer's next
sign-in (branding is resolved once per session).

The resolved branding also themes that customer's branded PDF reports (the
"Customer portal" branding option when generating an Incident Management report).

!!! note "Multi-customer portal users"
    A portal user scoped to more than one customer sees the **global** branding,
    since no single customer's override applies unambiguously. Overrides apply to
    users scoped to exactly one customer.
