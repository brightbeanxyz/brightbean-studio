# Open-Source Social Media Management Platform - Feature Specification v2

## Product Positioning

An open-source, self-hostable social media management platform built for agencies and SMBs. The cloud-hosted version and the self-hosted version are identical - every feature is free, forever, with no per-seat, per-channel, or per-workspace limits. Monetization comes exclusively from optional paid support plans and consulting, not from feature gating.

**Core promise:** Everything Sendible, SocialPilot, and ContentStudio charge $100–300/month for - completely free, whether cloud-hosted or self-hosted.

**Supported platforms:** Facebook Pages, Instagram (posts, reels, stories, carousels), LinkedIn (profiles + company pages), TikTok, YouTube (videos + shorts), Pinterest, Threads, Bluesky, Google Business Profile, Mastodon.

**Not supported:** X/Twitter is explicitly excluded from the platform.

**Integration architecture:** All platform integrations use the official first-party APIs directly. No unified social media API providers (Ayrshare, Outstand, etc.) are used. Users provide their own platform API credentials for self-hosted deployments. The cloud version manages shared app credentials where platform terms allow.

---

## Information Architecture

```
Organization (Agency)
├── Workspace (Client A)
│   ├── Social Accounts (IG, FB, LinkedIn, TikTok, YouTube, Pinterest, Threads, Bluesky, GBP, Mastodon)
│   ├── Content Calendar
│   ├── Media Library
│   ├── Social Inbox
│   ├── Analytics
│   └── Team Members + Roles
├── Workspace (Client B)
│   └── ...
├── Global Settings
│   ├── White-Label Config
│   ├── Platform API Credentials
│   └── Organization-wide Roles
└── Reports (cross-workspace)
```

---
---

# FEATURE SPECIFICATIONS

Each feature below is written as a self-contained spec that can be handed to a developer independently. Features reference each other by ID (e.g., "F-1.1") where dependencies exist.

---
---

# 1. ORGANIZATION & WORKSPACE MANAGEMENT

---

## F-1.1 - Organization Management

### Purpose
An Organization is the top-level entity representing an agency, company, or individual user. It contains all workspaces, members, settings, and API credentials. Every user belongs to exactly one organization (multi-org support is out of scope for v1).

### User Stories
- As a new user, I sign up and an Organization is automatically created for me - I do not need to configure anything before I can start working.
- As an Org Owner, I can rename my organization, update its logo, and configure org-wide settings at any time from settings.
- As an Org Owner, I can delete my organization, which permanently removes all data after a confirmation period.

### Functional Requirements

**Creation:**
- When a user signs up (email/password or OAuth), an Organization is automatically created in the background with zero user input. No onboarding wizard, no name prompt, no logo upload - the user lands directly on an empty dashboard ready to create their first workspace.
- The auto-created organization uses sensible defaults: name is set to the user's name + "'s Organization" (e.g., "Jan's Organization"), no logo, timezone defaults to the user's browser-detected timezone.
- The user who signs up is automatically assigned the Owner role.
- All default settings (name, logo, timezone, branding) can be changed at any time from Organization Settings (accessible via sidebar → Settings → Organization).
- One organization is created per signup. There is no multi-org switching in v1.
- If the user was invited to an existing organization (via F-1.3 invitation flow), no new organization is created - they join the existing one.

**Settings (accessible to Owner and Admin roles):**
- Organization name (string, 2–100 characters).
- Organization logo (image upload, used in sidebar, reports, white-label). Accepts PNG, JPG, SVG. Max 2MB. Stored in the media storage backend.
- Default timezone (used as fallback for workspaces that don't set their own).
- Platform API credentials (see F-1.5).

**Deletion:**
- Only the Owner can initiate deletion.
- Deletion is a two-step process: (1) Owner clicks "Delete Organization," (2) system sends a confirmation email with a unique link that expires in 24 hours, (3) clicking the link schedules deletion after a 7-day grace period.
- After the grace period, all data is permanently deleted: workspaces, posts, media, analytics, members, OAuth tokens.
- The system sends email notifications to all Admins when deletion is initiated and when it completes.

**Deletion Cancellation (during grace period):**
- During the 7-day grace period, the Owner can cancel the scheduled deletion at any time.
- Cancellation is available from two places: (1) a prominent banner at the top of every page in the app reading "Your organization is scheduled for deletion on [date]. Cancel deletion?" with a "Cancel Deletion" button, and (2) a link in the deletion confirmation email that says "Changed your mind? Cancel deletion."
- Clicking "Cancel Deletion" immediately reverts the organization to normal state - the soft-delete timestamp is cleared, the banner disappears, and all functionality is restored.
- Cancellation does not require email re-confirmation - clicking the button is sufficient since the user is already authenticated as the Owner.
- After cancellation, the Owner can re-initiate deletion at any time, which restarts the full two-step process and a fresh 7-day grace period.
- If the grace period expires without cancellation, deletion is irreversible.

### Data Model
- `Organization`: id, name, logo_url, default_timezone, created_at, updated_at, deletion_requested_at (datetime, nullable - set when deletion is confirmed), deletion_scheduled_for (datetime, nullable - deletion_requested_at + 7 days), deleted_at (datetime, nullable - set when deletion is executed after grace period).

### Dependencies
- F-1.3 (Members & Roles) - for role-based access to settings.
- F-5.2 (White-Label) - logo is reused for white-label branding.
- F-1.5 (Platform API Credentials) - stored at org level.

### Acceptance Criteria
- A new user can sign up and land on an empty dashboard with a fully created organization in under 10 seconds - no onboarding steps, forms, or wizards block them.
- The auto-created organization has a sensible default name derived from the user's name and a timezone matching their browser.
- Org name and logo changes made later in settings reflect immediately across all views (sidebar, reports, white-label portal).
- Org deletion sends confirmation email within 30 seconds. The Owner can cancel deletion at any time during the 7-day grace period. All data is permanently removed after the grace period ends without cancellation.
- No orphaned data remains after deletion (verified by a cleanup audit job).

---

## F-1.2 - Workspace Management

### Purpose
A Workspace is an isolated environment for one client or brand. All content, social accounts, media, analytics, and inbox messages are scoped to a workspace. No data leaks between workspaces. Agencies create one workspace per client.

### User Stories
- As an agency Manager, I can create a new workspace for each client I onboard.
- As a workspace Owner, I can configure workspace-specific settings (timezone, brand colors, default hashtags).
- As an agency Admin, I can archive a workspace when a client churns without losing historical data.
- As a team member, I only see workspaces I've been invited to.

### Functional Requirements

**Creation:**
- Any Org Admin or Owner can create a workspace.
- Required fields: workspace name (2–100 characters).
- Optional fields: workspace icon/avatar (image, max 1MB), timezone (defaults to org timezone), description (text, max 500 characters).
- The creator is automatically added as the workspace Owner.

**Settings (accessible to workspace Owner and Manager):**
- Name, icon, description, timezone.
- Brand colors: primary color (hex), secondary color (hex). Used in reports and client portal.
- Default hashtags: a set of hashtags that are auto-suggested in the composer for this workspace. Stored as a list of strings.
- Default first comment template: text that auto-populates the first comment field in the composer.
- Approval workflow mode: none, optional, required_internal, required_internal_and_client (see F-2.2).

**Workspace Switcher:**
- The sidebar displays a list of all workspaces the current user has access to, sorted alphabetically with a search/filter input.
- Clicking a workspace loads its context: calendar, inbox, analytics, media library all scope to that workspace.
- A "pin" option allows users to pin frequently used workspaces to the top of the list.
- The last-used workspace is remembered and loaded on next login.

**Archiving:**
- Workspace Owner or Org Admin can archive a workspace.
- Archived workspaces are hidden from the sidebar by default but accessible via a "Show archived" toggle in workspace settings.
- All data is retained. Scheduled posts in an archived workspace are paused (not deleted). Publishing is disabled.
- Archived workspaces can be unarchived at any time, restoring full functionality.

**Deletion:**
- Only Org Owner or Org Admin can permanently delete a workspace.
- Deletion confirmation requires typing the workspace name.
- Deletion is immediate and permanent. All workspace data (posts, media, analytics, inbox messages, social account connections) is removed.
- Connected social accounts are disconnected (OAuth tokens revoked where platform supports it).

**Cross-Workspace Views (Organization Dashboard):**
- Org Admins and Owners can access an organization-level dashboard that aggregates data across workspaces.
- Views available: "All Pending Approvals" (queue of posts awaiting approval across all workspaces), "All Scheduled Posts" (calendar view across all workspaces, color-coded by workspace), "All Failed Posts" (posts that failed to publish across all workspaces).
- This dashboard is read-only - actions (approve, edit, retry) require navigating into the specific workspace.

### Data Model
- `Workspace`: id, organization_id, name, icon_url, description, timezone, primary_color, secondary_color, default_hashtags (json array), default_first_comment, approval_workflow_mode (enum), is_archived (boolean), created_at, updated_at.

### Dependencies
- F-1.1 (Organization) - workspaces belong to an organization.
- F-1.3 (Members & Roles) - workspace-level role assignments.
- F-2.2 (Approval Workflow) - workflow mode is configured per workspace.

### Acceptance Criteria
- Creating a workspace takes fewer than 3 clicks from the dashboard.
- Switching workspaces loads the new workspace's data within 1 second (perceived).
- Archiving a workspace immediately hides it from non-admin users and pauses all scheduled posts.
- Deleting a workspace removes all associated data; no foreign key violations or orphaned records.
- Cross-workspace dashboard loads within 3 seconds for organizations with up to 50 workspaces.

---

## F-1.3 - Members & Role-Based Access Control (RBAC)

### Purpose
Control who can do what at both the organization level and the workspace level. Two-layer RBAC ensures agencies can give team members and clients precisely the access they need.

### User Stories
- As an Org Owner, I can invite team members to my organization by email.
- As an Org Admin, I can assign members to specific workspaces with specific roles.
- As a workspace Manager, I can invite a client to my workspace with the Client role so they can approve posts.
- As a Contributor, I can create draft posts but cannot publish or approve anything.
- As an Org Admin, I can create custom roles with specific permission toggles.

### Functional Requirements

**Organization Roles (govern org-level actions):**

| Role | Manage members | Create/delete workspaces | View all workspaces | Configure white-label | Manage API credentials | Delete organization |
|------|---------------|------------------------|--------------------|--------------------|----------------------|-------------------|
| Owner | Yes | Yes | Yes | Yes | Yes | Yes |
| Admin | Yes | Yes | Yes | Yes | Yes | No |
| Member | No | No | Only assigned | No | No | No |

- There is exactly one Owner per organization. Ownership can be transferred to another Admin (two-step confirmation with email verification for both parties).
- Admins can invite new members, change member roles (except Owner), and remove members.
- Members have no org-level management powers; they only interact with workspaces they are assigned to.

**Workspace Roles (govern workspace-level actions):**

| Role | Create posts | Edit own posts | Edit others' posts | Approve posts | Publish directly | Manage social accounts | View analytics | Use inbox | Reply from inbox | Manage workspace settings |
|------|-------------|---------------|-------------------|--------------|-----------------|----------------------|---------------|-----------|-----------------|-------------------------|
| Owner | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes |
| Manager | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | Yes | No |
| Editor | Yes | Yes | Yes | No | Configurable | No | Yes | Yes | Yes | No |
| Contributor | Yes (drafts only) | Yes (own drafts) | No | No | No | No | Limited | No | No | No |
| Client | No | No | No | Yes | No | No | View only | No | No | No |
| Viewer | No | No | No | No | No | No | View only | No | No | No |

- "Configurable" for Editor direct publish means: the workspace Owner can toggle whether Editors can bypass the approval workflow and schedule/publish directly.
- "Limited" analytics for Contributor means: can see engagement metrics on their own posts only.

**Custom Roles:**
- Org Admins can create custom workspace roles by naming them and toggling each permission individually.
- Custom roles are available across all workspaces in the organization.
- Built-in roles (Owner, Manager, Editor, Contributor, Client, Viewer) cannot be modified or deleted.

**Invitation Flow:**
- Org Admin/Owner invites a user by email address.
- The system sends an invitation email with a signup/login link.
- If the invitee already has an account in the organization, they are added directly.
- If the invitee is new, they create an account and are automatically added to the organization.
- The invitation specifies: which workspace(s) to add them to, and which workspace role for each.
- Invitations expire after 7 days. Admins can resend or revoke pending invitations.
- Pending invitations are visible in a "Pending Invitations" list in org member settings.

**Client Invitation (special flow):**
- When inviting someone with the Client role, the invitation email uses a simplified onboarding flow.
- Clients can optionally access the platform via magic link (no password required) - see F-1.4.
- Client accounts are flagged as external and are hidden from internal team member lists by default (toggle to show).

**Member Removal:**
- Org Admins can remove a member from the organization entirely (removes from all workspaces).
- Workspace Owners/Managers can remove a member from their specific workspace only.
- Removing a member does not delete their authored content (posts, comments). Authorship is preserved as a display name.
- If a removed member is the only Manager of a workspace, removal is blocked until another Manager is assigned.

### Data Model
- `User`: id, email, name, avatar_url, password_hash, created_at.
- `OrgMembership`: id, user_id, organization_id, org_role (enum: owner, admin, member), invited_at, accepted_at.
- `WorkspaceMembership`: id, user_id, workspace_id, workspace_role (enum or foreign key to CustomRole), added_at.
- `CustomRole`: id, organization_id, name, permissions (json object mapping permission keys to booleans).
- `Invitation`: id, organization_id, email, workspace_assignments (json: [{workspace_id, role}]), invited_by, token, expires_at, accepted_at.

### Acceptance Criteria
- A user with only the Contributor role can create drafts but receives a "Permission denied" error if they attempt to schedule, publish, or approve.
- A Client role user sees only: the approval queue for their workspace, published post analytics, and report downloads. No sidebar navigation to calendar, composer, inbox, or settings.
- Custom roles correctly apply per-permission toggles; changing a permission on a custom role takes effect immediately for all users assigned that role.
- Removing the last Manager of a workspace is blocked with a clear error message.
- Invitation emails arrive within 60 seconds of sending.

---

## F-1.4 - Client Portal

### Purpose
Provide clients with a minimal, branded interface to review and approve content and view performance reports - without requiring them to learn the full platform or see other clients' data.

### User Stories
- As an agency Manager, I can send my client a magic link to review this week's scheduled posts.
- As a client, I can approve or reject posts with a comment explaining my feedback.
- As a client, I can view published post analytics for my brand.
- As a client, I can download reports my agency has shared with me.
- As a client, I do not need to create a password or remember login credentials.

### Functional Requirements

**Access Methods:**
- **Magic link (primary):** A unique, time-limited URL sent via email. Clicking it logs the client in automatically. No password needed. Magic links expire after 30 days but can be regenerated by the workspace Manager at any time.
- **Email + password (optional):** Clients can optionally set a password during onboarding for persistent access. Password login shows only their workspace(s).
- Magic link URLs contain a cryptographically secure token (minimum 32 bytes, URL-safe base64 encoded). Tokens are single-use for the initial login but create a session that lasts 30 days.

**Portal Views:**

*Approval Queue:*
- List of all posts with status "pending_client" in the client's workspace.
- Each post shows: scheduled date/time, target platform(s), caption text, attached media (images render inline, videos show thumbnail with play button), author name.
- Client can click a post to expand it into a detail view showing the full platform-specific preview (how it will look on Instagram, LinkedIn, etc.).
- Actions per post: "Approve" (green button), "Request Changes" (orange button, requires a comment), "Reject" (red button, requires a comment).
- Bulk actions: select multiple posts and approve all at once.
- Posts the client has already reviewed show a "Reviewed" badge with their action and comment.

*Published Content:*
- Chronological list of published posts for the client's workspace.
- Each post shows: published date, platform, caption snippet, engagement summary (likes, comments, shares, reach - numbers only, no charts).
- Clicking a post opens a detail view with full engagement metrics.

*Reports:*
- List of reports shared with this workspace (generated via F-4.3).
- Each report shows: title, date range, generated date.
- Actions: view in browser (rendered HTML), download as PDF.
- Shareable report links (F-4.3) also render in this portal view.

*Activity Log:*
- Chronological list of actions the client has taken: approvals, rejections, comments.
- Read-only. Helps the client track what they've already reviewed.

**Branding:**
- The portal displays the agency's white-label branding (logo, colors, custom domain) if configured via F-5.2.
- If no white-label is configured, the portal displays the platform's default branding.
- The platform name is never visible to the client if white-label is active.

**Restrictions:**
- Clients cannot: create or edit posts, change schedules, access the composer, access the full calendar, access the social inbox, access media library, see internal team comments, access other workspaces, access org settings.
- Clients can see external comments on posts (comments marked as "visible to client" by the team).

**Notifications:**
- When posts are submitted for client approval, the client receives an email with a magic link to the approval queue.
- Email subject line is configurable per workspace (default: "[Workspace Name] - Posts ready for your review").
- Email body shows the count of pending posts and a "Review now" button (magic link).
- Reminder emails are sent if posts remain pending for a configurable number of hours (default: 48 hours). Maximum 2 reminders per post batch.

### Data Model
- `MagicLinkToken`: id, user_id, workspace_id, token (string, unique, indexed), created_at, expires_at, last_used_at.
- Session management: standard session cookie with 30-day expiry after magic link authentication.
- Client portal pages are server-rendered views filtered by workspace_id and workspace_role = "client".

### Dependencies
- F-1.3 (RBAC) - Client role permissions.
- F-2.2 (Approval Workflow) - post approval/rejection actions.
- F-4.3 (Report Builder) - reports visible in portal.
- F-5.2 (White-Label) - branding applied to portal.
- F-7.1 (Notification System) - email delivery of magic links and reminders.

### Acceptance Criteria
- A client can go from receiving an email to reviewing their first post in under 15 seconds (magic link click → portal loads → approval queue visible).
- Approving a post updates the post status to "approved" within 1 second and triggers a notification to the workspace team.
- The portal renders correctly on mobile devices (responsive design, minimum 320px viewport width).
- If white-label is configured, zero references to the platform's own brand appear anywhere in the portal UI or emails.
- Magic link tokens cannot be reused after expiry; attempting to use an expired token redirects to a "Request a new link" page.

---

## F-1.5 - Platform API Credentials Management

### Purpose
Manage the API credentials (app IDs, app secrets, callback URLs) needed to connect to each social media platform's official API. For self-hosted deployments, users must provide their own developer app credentials. For the cloud version, shared app credentials are managed by the platform operator.

### User Stories
- As a self-hosted admin, I can enter my Facebook App ID and Secret so my instance can connect to the Facebook Graph API.
- As a self-hosted admin, I can see which platforms are configured and which are missing credentials.
- As a cloud user, I don't need to worry about API credentials - they're pre-configured.

### Functional Requirements

**Credential Configuration (self-hosted only):**
- Settings page under Organization → Platform Credentials.
- For each supported platform, display: platform name, platform icon, status (configured / not configured), fields for required credentials.

| Platform | Required Credentials |
|----------|---------------------|
| Facebook / Instagram | App ID, App Secret, (Facebook uses the same app for both) |
| LinkedIn | Client ID, Client Secret |
| TikTok | Client Key, Client Secret |
| YouTube | Client ID, Client Secret (Google Cloud OAuth) |
| Pinterest | App ID, App Secret |
| Threads | Same Facebook app (uses Instagram Graph API permissions) |
| Bluesky | No app credentials needed (uses AT Protocol with user's handle + app password) |
| Google Business Profile | Same Google Cloud OAuth app as YouTube (additional scopes) |
| Mastodon | Per-instance OAuth app registration (auto-created on first connect) |

- Credentials are entered once at the org level and shared across all workspaces.
- Credentials are stored encrypted at rest (AES-256-GCM, encryption key derived from a server-side secret, not stored in the database).
- A "Test Connection" button per platform attempts to initialize an OAuth flow and reports success or failure.
- Callback/redirect URIs are auto-generated and displayed for copy-pasting into the platform's developer console.

**Cloud version:**
- The credentials settings page is hidden from all users, including Org Owners. Users never see or interact with platform API credentials on the cloud version.
- Platform API credentials for the cloud version are configured by the platform developers exclusively via server-side environment variables. Each platform's credentials are stored as environment variables following this naming convention:
  - `PLATFORM_FACEBOOK_APP_ID` / `PLATFORM_FACEBOOK_APP_SECRET`
  - `PLATFORM_LINKEDIN_CLIENT_ID` / `PLATFORM_LINKEDIN_CLIENT_SECRET`
  - `PLATFORM_TIKTOK_CLIENT_KEY` / `PLATFORM_TIKTOK_CLIENT_SECRET`
  - `PLATFORM_GOOGLE_CLIENT_ID` / `PLATFORM_GOOGLE_CLIENT_SECRET` (shared by YouTube and Google Business Profile)
  - `PLATFORM_PINTEREST_APP_ID` / `PLATFORM_PINTEREST_APP_SECRET`
- On application startup, the system reads these environment variables and populates the `PlatformCredential` records for a special system-level "cloud" organization context. If an environment variable is missing or empty, that platform is marked as "Coming soon" in the social account connection flow.
- Developers must never commit these credentials to source control. In production, credentials are injected via the hosting platform's secrets management (e.g., Heroku config vars, AWS Secrets Manager, Docker secrets, Kubernetes secrets).
- Callback/redirect URIs for the cloud version are hardcoded to the cloud app's domain (e.g., `https://app.platform.com/auth/callback/{platform}`). Developers configure these URIs in each platform's developer console when setting up the shared app.
- If a platform's credentials need to be rotated, the developer updates the environment variable and restarts the application. Existing user OAuth tokens remain valid until they expire.

**Credential Rotation:**
- Admins can update credentials at any time. Existing OAuth tokens for connected accounts remain valid until they expire.
- If credentials are revoked or changed in a way that invalidates existing tokens, the system marks affected social accounts as "Needs reconnection" and notifies workspace Managers.

### Data Model
- `PlatformCredential`: id, organization_id, platform (enum), credentials (encrypted json), is_configured (boolean), tested_at, test_result (enum: success, failure, untested), created_at, updated_at.

### Dependencies
- F-2.4 (Publishing Engine) - uses these credentials for API calls.
- F-3.1 (Social Inbox) - uses these credentials for reading messages.
- F-4.1 (Analytics) - uses these credentials for fetching metrics.

### Acceptance Criteria
- Self-hosted: entering valid Facebook credentials and clicking "Test Connection" returns a success state within 10 seconds.
- Self-hosted: attempting to connect a social account for a platform with no configured credentials shows a clear error message directing the admin to the credentials page.
- Cloud: the credentials page is completely hidden from all users, including Org Owners.
- Credentials are never exposed in API responses, logs, or error messages. Only the last 4 characters of secrets are shown in the UI for identification.

---

## F-1.6 - Configurable Defaults & Platform Settings

### Purpose
Centralize all operational defaults into editable settings at the organization and workspace level. No behavioral values should be hardcoded in application code - every timing, threshold, limit, and default text referenced across features must be editable by the appropriate admin without a code change or redeployment.

### User Stories
- As an Org Owner, I can change the magic link expiry duration from 30 days to 14 days.
- As a workspace Manager, I can change the approval reminder interval from 24 hours to 12 hours for my fast-paced client.
- As a self-hosted admin, I can adjust background job intervals to match my server capacity.
- As a new user, all defaults are set to sensible values so I do not need to configure anything to start working.

### Functional Requirements

**Organization-Level Settings (accessible to Owner and Admin):**

Located at Organization → Settings → "Defaults."

| Setting | Default Value | Description |
|---------|--------------|-------------|
| Deletion grace period (days) | 7 | Number of days between deletion confirmation and permanent data removal. |
| Deletion confirmation link expiry (hours) | 24 | How long the email confirmation link for org deletion remains valid. |
| Invitation expiry (days) | 7 | How long a team member invitation link remains valid before it expires. |
| Magic link expiry (days) | 30 | How long a client portal magic link remains valid. |
| Session duration (days) | 30 | How long a user session lasts before requiring re-authentication (sliding window). |
| Login rate limit - max attempts | 5 | Number of failed login attempts allowed per email before temporary lockout. |
| Login rate limit - lockout duration (minutes) | 15 | Duration of the temporary lockout after exceeding max login attempts. |
| Email batching delay (minutes) | 5 | When multiple notification events occur within this window, they are batched into a single email. Set to 0 to disable batching (send immediately). |
| 2FA enforcement | Off | When enabled, all org members must set up two-factor authentication. |
| Stock media attribution | On | When enabled, a credit line is auto-appended to post captions when using Unsplash/Pexels images. |
| Publish log retention (days) | 90 | How long individual publish attempt logs are retained before cleanup. |
| Webhook delivery log retention (days) | 30 | How long webhook delivery logs are retained. |
| Audit log retention (days) | 365 | How long audit logs for destructive actions are retained. |

**Workspace-Level Settings (accessible to workspace Owner and Manager):**

Located at Workspace → Settings → "Defaults."

These override org-level defaults where applicable. If a workspace setting is left blank/unset, the org-level default is used (inheritance model).

| Setting | Default Value | Description |
|---------|--------------|-------------|
| **Approval & Reminders** | | |
| Internal review reminder interval (hours) | 24 | Hours after a post enters "pending_review" before a reminder is sent to reviewers. |
| Client approval reminder interval (hours) | 48 | Hours after a post enters "pending_client" before a reminder is sent to the client. |
| Maximum reminders per post per stage | 2 | After this many reminders, no more are sent - instead the workspace Manager is notified the post is stalled. |
| Stalled post escalation | On | When max reminders are exhausted, notify the workspace Manager that a post is stalled. |
| Approval email subject template | "[Workspace Name] - Posts ready for your review" | Customizable subject line for client approval request emails. Supports variables: `{workspace_name}`, `{post_count}`, `{date}`. |
| **Publishing** | | |
| First comment delay (seconds) | 5 | Delay between main post publication and first comment posting. Some platforms flag instant comments as spam. |
| Publish retry max attempts | 3 | Number of retry attempts before marking a platform post as failed. |
| Publish retry backoff schedule | 1min, 5min, 30min | Delay before each successive retry. Entered as a comma-separated list of durations. |
| **Scheduling** | | |
| Recurring post lookahead (days) | 90 | How far in advance the system pre-generates individual posts from recurring rules. |
| Queue empty slot warning (days) | 30 | Warn the user if a queue has no available posting slots within this many days. |
| **Inbox** | | |
| Inbox sync interval (minutes) | 5 | How often the system polls each connected account for new messages. Does not apply to platforms using webhooks. |
| Auto-resolve on reply | On | When a team member replies to an inbox message, automatically change its status to "resolved." |
| SLA target response time (minutes) | 120 | Target time for responding to inbox messages. Messages exceeding this show an "Overdue" badge. Set to 0 to disable SLA tracking. |
| **Analytics** | | |
| Optimal time calculation lookback (days) | 90 | Number of days of historical data used to calculate best posting times. |
| Optimal time minimum data threshold (posts) | 10 | Minimum number of posts in the lookback period before optimal time suggestions are shown. |
| Analytics high-frequency collection window (hours) | 48 | For posts published within this window, metrics are fetched hourly. After this window, collection switches to daily. |
| **Notifications** | | |
| Quiet hours start | (unset) | Start of quiet hours during which non-critical notifications are suppressed. Timezone-aware. Format: HH:MM. |
| Quiet hours end | (unset) | End of quiet hours. |
| Digest mode | Off | When enabled, email notifications are batched into a single daily digest instead of individual emails. |
| **Client Onboarding** | | |
| Client connection link expiry (days) | 7 | How long a client account-connection link (F-1.7) remains valid before it expires. |

**Self-Hosted-Only Settings (accessible to the server admin via environment variables or admin panel):**

These control infrastructure-level behavior and are not exposed to regular org/workspace settings.

| Setting | Default Value | Description |
|---------|--------------|-------------|
| Account health check interval (hours) | 6 | How often the system checks each connected social account's health via a lightweight API call. |
| Token refresh check interval (hours) | 1 | How often the system scans for OAuth tokens expiring soon. |
| Token refresh lookahead (hours) | 24 | Tokens expiring within this window are proactively refreshed. |
| Publishing poll interval (seconds) | 15 | How often the background worker checks for posts ready to publish. |
| Media pre-processing lookahead (minutes) | 60 | Media for posts scheduled within this window is pre-processed. |
| Max concurrent publish jobs | 10 | Maximum number of posts being published simultaneously. |
| Recurrence generation interval | Daily | How often the background job generates future instances of recurring posts. |
| Cleanup job schedule | Daily at 3:00 AM UTC | When the cleanup job runs to remove expired logs, tokens, and other ephemeral data. |

**Settings UI:**
- Organization settings and workspace settings each have a "Defaults" tab organized into collapsible sections matching the categories above.
- Each setting shows: label, current value, default value (greyed out if the current value matches the default), a brief description, and an input field appropriate to the data type (number input, text input, toggle, time picker).
- Workspace settings show an "Inherit from organization" toggle per setting. When enabled, the workspace uses the org-level value and the input field is disabled.
- Changes are saved immediately on blur or on an explicit "Save" button per section. A success toast confirms the save.
- A "Reset to defaults" button per section reverts all settings in that section to their default values.
- Changes take effect immediately for all future operations - they do not retroactively affect already-scheduled posts, already-sent reminders, or already-generated recurrences.

### Data Model
- `OrgSetting`: id, organization_id, key (string, unique per org), value (json), updated_at.
- `WorkspaceSetting`: id, workspace_id, key (string, unique per workspace), value (json, nullable - null means inherit from org), updated_at.
- Settings keys follow a namespaced convention: `approval.internal_reminder_hours`, `publishing.first_comment_delay_seconds`, `inbox.sync_interval_minutes`, etc.
- A helper function `get_setting(workspace_id, key)` returns the workspace-level value if set, otherwise falls back to the org-level value, otherwise falls back to the application-level default.

### Dependencies
- All features reference these settings instead of hardcoded values.
- F-1.1, F-1.2 (Org/Workspace) - settings belong to these entities.
- F-2.2 (Approval) - reminder intervals, max reminders.
- F-2.3 (Calendar) - recurrence lookahead, queue warnings.
- F-2.4 (Publishing Engine) - retry logic, first comment delay, poll interval.
- F-3.1 (Inbox) - sync interval, auto-resolve, SLA timer.
- F-4.1 (Analytics) - collection windows, optimal time thresholds.
- F-7.1 (Notifications) - batching delay, quiet hours, digest mode.
- F-1.4 (Client Portal) - magic link expiry, reminder intervals, email subject templates.
- F-5.1 (Auth) - session duration, login rate limits, 2FA enforcement.

### Acceptance Criteria
- Changing "Internal review reminder interval" from 24 to 12 hours in workspace settings causes the next reminder for a pending post in that workspace to fire after 12 hours (not 24).
- A workspace setting left as "Inherit from organization" correctly uses the org-level value. Changing the org-level value propagates to all inheriting workspaces.
- A workspace setting explicitly set to a custom value is not affected by changes to the org-level default.
- "Reset to defaults" reverts all settings in a section and the UI reflects the change immediately.
- Self-hosted admin can change the publishing poll interval via environment variable; the background worker picks up the new interval on next restart.
- The `get_setting()` function returns the correct value following the cascade: workspace override → org override → application default.

---

## F-1.7 - Client Onboarding Flow

### Purpose
Define the end-to-end process for onboarding a new client into the platform - from workspace creation through social account connection to first content review. This is the critical first experience for agencies and must be fast and frictionless.

### User Stories
- As a workspace Manager, I can onboard a new client in under 10 minutes: create a workspace, connect their accounts, invite them, and submit initial content for review.
- As a client, I receive a clear, branded email inviting me to review my first posts - without needing to understand the platform.
- As an agency admin, I can connect client social accounts on their behalf using access the client has granted to me (common agency practice).
- As a client, I can connect my own social accounts via a guided link my agency sends me, without accessing the full platform.

### Functional Requirements

**Step 1: Workspace Creation**
- Agency member (Admin or Owner) creates a new workspace (F-1.2) for the client.
- Minimum input: workspace name. All other settings (timezone, brand colors, approval workflow) can be configured later.
- After creation, the user lands inside the new workspace and is prompted with a "Get Started" checklist (see below).

**Step 2: Social Account Connection**

Two connection methods, depending on agency-client relationship:

*Method A - Agency connects accounts directly (most common):*
- The agency already has admin/editor access to the client's social media accounts (standard agency practice - client grants access through each platform's native permission system).
- The agency member clicks "Connect Account" in the workspace and completes the OAuth flow themselves, authenticating with their own Facebook/Instagram/LinkedIn/etc. credentials that have the necessary permissions on the client's pages/profiles.
- This is the standard flow described in F-2.5.

*Method B - Client connects their own accounts via invitation link:*
- For clients who prefer to connect their own accounts (privacy-conscious clients, or agencies that don't have admin access yet).
- The agency member clicks "Invite client to connect accounts" in workspace settings → Social Accounts.
- The system generates a single-purpose, time-limited URL (the "connection link"). This link is emailed to the client or copied to clipboard for sharing.
- The connection link opens a branded, minimal page (white-labeled if configured) that:
  1. Shows the agency name and workspace name ("Connect your accounts to [Agency Name]").
  2. Lists the supported platforms with "Connect" buttons.
  3. Guides the client through each platform's OAuth flow.
  4. After each successful connection, shows a green checkmark and the connected account name/avatar.
  5. Has a "Done" button that closes the page and notifies the agency team that accounts have been connected.
- The connection link does NOT grant the client access to the platform dashboard, composer, calendar, or any other features. It is solely for connecting social accounts.
- Connection link expiry: configurable, default 7 days (references F-1.6 settings - add `client_connection_link_expiry_days` to workspace settings).
- Connection link is single-use per account connection but remains active for connecting multiple accounts until it expires.
- The agency member can revoke or regenerate the connection link at any time.

**Step 3: Client Invitation (optional, parallel to Step 2)**
- The agency invites the client to the workspace with the "Client" role (F-1.3) so they can approve content later.
- This step is independent of account connection - a client can be invited before, during, or after accounts are connected.
- Invitation uses the standard flow (F-1.3) or magic link flow (F-1.4).

**Step 4: First Content Batch**
- After accounts are connected, the agency creates and schedules (or submits for approval) the first batch of posts.
- No special feature needed here - this uses the standard composer (F-2.1) and approval workflow (F-2.2).

**Get Started Checklist:**
- When a workspace is newly created and has not yet completed key setup steps, a "Get Started" checklist card is displayed prominently at the top of the workspace dashboard.
- Checklist items:

| Step | Completion Condition | Action Button |
|------|---------------------|---------------|
| Connect social accounts | At least 1 social account connected to this workspace | "Connect Accounts" → opens account connection flow |
| Invite your client | At least 1 member with Client role in this workspace | "Invite Client" → opens invitation form |
| Set approval workflow | Approval workflow mode has been explicitly set (not default) | "Configure" → opens workspace settings |
| Create your first post | At least 1 post created (any status) in this workspace | "Create Post" → opens composer |
| Set up posting schedule | At least 1 posting slot configured for any connected account | "Set Schedule" → opens posting slots config |

- Each completed step shows a checkmark. Incomplete steps show a circle outline with the action button.
- The checklist can be dismissed ("Don't show again") - it does not reappear once dismissed. Dismissal is stored per user per workspace.
- The checklist is purely informational and advisory - it does not block any functionality. Users can use any feature at any time regardless of checklist completion.

**Connection Link Page (detailed spec):**

*Layout:*
- Full-page, centered card layout. No sidebar, no navigation - this is a standalone page.
- Header: agency logo (from white-label, or platform logo if not configured), "Connect your social accounts" heading, workspace name subtitle.
- Body: grid of platform cards. Each card shows: platform icon, platform name, "Connect" button (or "Connected ✓" with account name/avatar after connection).
- Footer: "Need help? Contact [agency email from white-label settings, or platform support email]."

*Behavior:*
- Clicking "Connect" initiates the standard OAuth flow for that platform (F-2.5). The OAuth callback redirects back to this page.
- After connecting an account, the card updates to show the connected account name and avatar with a green checkmark.
- The client can connect multiple accounts across multiple platforms.
- A "Done - Notify [Agency Name]" button at the bottom sends an in-app + email notification to all workspace Managers listing which accounts were connected.

*Security:*
- The connection link token is cryptographically secure (32 bytes, URL-safe base64).
- The token is scoped to a specific workspace. It cannot be used to access any other workspace or organization data.
- The page does not expose any existing workspace data (no posts, no calendar, no analytics, no other connected accounts).
- Rate limiting: max 20 OAuth flow initiations per token per hour (prevents abuse).

### Data Model
- `ConnectionLink`: id, workspace_id, token (string, unique, indexed), created_by (user_id), expires_at (datetime), revoked_at (datetime, nullable), created_at.
- `ConnectionLinkUsage`: id, connection_link_id, social_account_id (FK - the account that was connected), connected_at (datetime).
- `OnboardingChecklist`: id, user_id, workspace_id, is_dismissed (boolean), dismissed_at (datetime, nullable).

### Dependencies
- F-1.2 (Workspace) - workspace creation.
- F-1.3 (RBAC) - client role invitation.
- F-1.4 (Client Portal) - client access after onboarding.
- F-1.6 (Configurable Defaults) - connection link expiry setting.
- F-2.5 (Social Account Connection) - OAuth flows.
- F-5.2 (White-Label) - branding on connection link page.
- F-7.1 (Notifications) - notification when client finishes connecting accounts.

### Acceptance Criteria
- A workspace Manager can generate a connection link and share it within 3 clicks.
- A client receiving the connection link can connect an Instagram Business account within 60 seconds (excluding time on Instagram's auth page).
- After the client connects accounts and clicks "Done," the workspace Manager receives a notification within 30 seconds listing the connected accounts.
- The connection link page shows zero platform data - no posts, no analytics, no other accounts. Only the connect buttons and connected account confirmations.
- An expired connection link shows a friendly "This link has expired - contact your agency" page.
- The "Get Started" checklist correctly reflects completion state: connecting an account immediately checks off "Connect social accounts."
- Dismissing the checklist persists - refreshing the page does not bring it back.

---
---

# 2. CONTENT CREATION & PUBLISHING

---

## F-2.1 - Post Composer

### Purpose
The central content creation interface. Users compose a single post and customize it per platform. The composer produces a Post entity that flows into the approval workflow and/or scheduling system.

### User Stories
- As an Editor, I can compose a post, select multiple target platforms, and see a live preview for each.
- As an Editor, I can customize the caption, media, and hashtags differently for each platform from the same composer.
- As an Editor, I can attach images, videos, and carousels to my post.
- As a Contributor, I can compose a draft but cannot schedule or publish it.
- As an Editor, I can use AI to generate caption variations, suggest hashtags, and rewrite my text for a different tone.
- As an Editor, I can save a post as a template for reuse.

### Functional Requirements

**Composer Layout:**
- The composer is a dedicated full page (route: `/workspace/{id}/compose`), not a modal or popover. Navigating to the composer replaces the current view entirely. The sidebar remains visible for workspace navigation, but the main content area is fully dedicated to the composer.
- A "back" button in the top-left of the composer returns the user to their previous view (calendar, draft list, etc.). If there are unsaved changes, a confirmation dialog appears.
- The composer page is divided into three panels:
- Left panel: platform selector (checkboxes for each connected account in the current workspace) and media upload area.
- Center panel: caption text editor with the following controls:
  - Rich text is not supported (social platforms use plain text). The editor is a plain text area with character count.
  - Character count shows limits per selected platform (e.g., LinkedIn: 3,000; Instagram: 2,200; Facebook: 63,206; Bluesky: 300; Mastodon: 500 or instance limit).
  - If the caption exceeds any selected platform's limit, that platform's counter turns red and a warning is shown.
  - Emoji picker accessible via a button or keyboard shortcut.
  - Hashtag auto-suggest: typing "#" opens a dropdown with workspace default hashtags (from F-1.2 settings) and recently used hashtags.
  - Mention auto-suggest: typing "@" opens a dropdown (populated from the connected account's recent interactions where platform API supports it; otherwise, free-text).
- Right panel: live preview for each selected platform. Previews render the post approximately as it would appear on the platform (caption truncation, media layout, profile picture, account name).

**Platform-Specific Customization:**
- By default, all platforms share the same caption and media.
- A "Customize for [platform]" toggle per platform allows overriding: caption text, media selection/ordering, hashtags, alt text per image, first comment text.
- Overrides are stored per PlatformPost (see F-2.4). The base post retains the "shared" version.
- Platforms that do not support a feature hide the relevant control (e.g., Pinterest does not support first comment - that field is hidden when Pinterest is the only selected platform).

**Media Attachment:**
- Media picker allows: upload from device, select from workspace media library (F-6.1), search stock media (Unsplash, Pexels, GIPHY - see F-5.3), open Canva (see F-5.3).
- Multiple media items can be attached. The composer detects the post type based on selection:
  - 1 image → Single image post.
  - 2–10 images → Carousel (on platforms that support it; otherwise, first image only with a warning).
  - 1 video → Video post / Reel / Short (depending on platform and duration).
  - Image + video mix → Carousel on supported platforms (Instagram, Facebook, LinkedIn); warning on others.
- Media ordering: drag-and-drop to reorder images/videos in a carousel.
- Per-image alt text field (accessibility).
- Media validation: the composer checks each attached media item against the target platform's requirements and shows warnings:
  - Image dimensions (minimum/maximum per platform).
  - Image file size (max per platform).
  - Video duration (e.g., Instagram Reel: 3–90 seconds; YouTube Short: up to 60 seconds; TikTok: up to 10 minutes).
  - Video file size.
  - Aspect ratio warnings (e.g., "This image is 16:9 but Instagram feed posts perform best at 4:5").
  - Number of items in a carousel (Instagram max: 20; LinkedIn max: 20; Facebook max: 10).

**Post Types:**
- Standard post (text + optional media).
- Reel / Short (vertical video, detected by aspect ratio and duration).
- Story (Instagram, Facebook - ephemeral, 24h).
- Carousel (multiple images/videos).
- Poll (LinkedIn only in v1).
- Article (LinkedIn only - long-form text with title).
- Video (YouTube - with title, description, tags, visibility, category fields).
- Pin (Pinterest - with board selection, link URL, title, description).

When a post type is selected, the composer adapts its fields:
- YouTube video shows: title (required, max 100 chars), description (max 5,000 chars), tags, visibility (public/unlisted/private), category dropdown, thumbnail upload.
- Pinterest pin shows: board selector (fetched from connected account), link URL, title, description.
- LinkedIn article shows: title, body (long-form text with basic formatting), cover image.

**First Comment:**
- A "First Comment" text field appears below the caption.
- Default text is pre-populated from workspace settings (F-1.2) if configured.
- The first comment is posted immediately after the main post is published (within the same publishing job).
- Supported on: Instagram, Facebook, LinkedIn, YouTube. Hidden for platforms that don't support it.

**Content Categories:**
- A dropdown to assign the post to a content category (e.g., "Educational," "Promotional," "Behind the scenes").
- Categories are defined per workspace (managed in workspace settings).
- Categories are used for: calendar filtering, analytics filtering, queue-based scheduling (F-2.3).
- A post can belong to zero or one category.

**Labels/Tags:**
- In addition to categories, posts can have freeform tags (e.g., "campaign:summer2026", "client-approved").
- Tags are used for filtering and searching posts across the calendar and analytics.

**Internal Notes:**
- A text field for team-only notes (e.g., "Client specifically requested we use this photo," "Part of the Q3 campaign").
- Internal notes are never visible to users with the Client role.
- Internal notes are not included in post previews or published content.

**AI Assist:**
- An "AI" button in the composer toolbar opens an AI assistant panel on the right side of the composer (overlaying or replacing the preview panel temporarily).
- The AI assistant requires at least one AI provider configured at the org level (see F-5.3 - AI Integration). If no provider is configured, the button shows a tooltip directing the admin to settings.
- **Provider/model selector (per-generation override):** At the top of the AI panel, a compact dropdown shows the currently selected provider and model (defaulting to the org-wide default). The user can change the provider (OpenAI, Anthropic, OpenRouter - only configured providers appear) and the model (dropdown of models for that provider, matching the options in F-5.3 settings). This selection persists for the duration of the composer session but does not change the org-wide default. Switching provider/model takes effect on the next AI action - it does not re-run previous generations.
- AI capabilities:
  - **Generate caption:** Given the media (if image - sent as vision input if the AI provider supports it) and optional context (e.g., "Write a caption for a coffee shop's Instagram promoting a new latte"), generate 3 caption variations. A text input field above the generate button lets the user provide context/instructions.
  - **Rewrite for tone:** Select existing caption text and choose a tone (professional, casual, humorous, inspirational, urgent). AI rewrites the caption in that tone.
  - **Suggest hashtags:** Based on the caption and media, suggest 10–15 relevant hashtags. User can click to add individual hashtags to the caption or first comment.
  - **Translate:** Translate the caption into a selected language. Language list: top 20 languages by internet users.
  - **Shorten/Lengthen:** Rewrite the caption to be shorter (e.g., fit within Bluesky's 300-char limit) or longer (expand a brief idea).
- All AI operations are performed server-side via the selected provider's API. The request includes the model specified in the per-generation selector.
- The user can accept, edit, or discard any AI-generated suggestion.
- AI-generated content is not auto-inserted - the user always confirms before it replaces the caption. An "Insert" button places the selected suggestion into the caption field; a "Discard" button clears the suggestions.

**Templates:**
- "Save as Template" button saves the current post's configuration (caption, media placeholders, category, platform selections, first comment, hashtags) as a reusable template.
- Templates are scoped to the workspace.
- Templates have a name (required) and optional description.
- "Use Template" button in the composer loads a template, populating all fields. The user can then modify and schedule as usual.
- Templates are managed (list, rename, delete) in a "Templates" section of workspace settings.

**Draft Saving:**
- The composer auto-saves to a draft every 30 seconds while the user is editing.
- Unsaved changes are warned about if the user tries to navigate away.
- Drafts appear in the content calendar (F-2.3) with a "Draft" status.
- A "Drafts" section in the sidebar or calendar filter shows all drafts for the workspace.

**Composer Actions (bottom bar):**
- "Save Draft" - saves without scheduling.
- "Submit for Approval" - visible if the workspace approval workflow is "optional" or "required". Transitions the post to "pending_review" status.
- "Schedule" - opens a date/time picker. Visible if the user's role permits direct publishing and the approval workflow allows it.
- "Publish Now" - immediately publishes. Visible only if the user's role permits direct publishing.
- "Add to Queue" - adds the post to the next available slot in the selected queue (see F-2.3). Visible if queues are configured.

### Data Model
- `Post`: id, workspace_id, author_id, status (enum: draft, pending_review, pending_client, approved, scheduled, publishing, published, partially_published, failed), caption (text), first_comment (text), category_id (nullable), tags (json array of strings), internal_notes (text), template_source_id (nullable), scheduled_at (datetime, nullable), published_at (datetime, nullable), proposed_publish_at (datetime, nullable — optional draft-stage suggested publish time, distinct from scheduled_at), created_at, updated_at.
- `PlatformPost`: id, post_id, social_account_id, platform_specific_caption (text, nullable - null means use base caption), platform_specific_media (json, nullable), platform_specific_first_comment (text, nullable), platform_post_id (string, nullable - populated after publish), publish_status (enum: pending, published, failed), publish_error (text, nullable), published_at (datetime, nullable).
- `PostMedia`: id, post_id, media_asset_id, position (integer, for ordering), alt_text (text, nullable), platform_overrides (json - e.g., {"instagram": {"crop": "4:5"}}).
- `PostVersion`: id, post_id, version_number (integer), snapshot (json - full post state at time of save), created_by, created_at.
- `PostTemplate`: id, workspace_id, name, description, template_data (json - caption, media references, category, platform selections, first comment, hashtags), created_by, created_at, updated_at.

### Dependencies
- F-1.2 (Workspace) - workspace scoping, default hashtags, first comment template.
- F-1.3 (RBAC) - role determines which composer actions are visible.
- F-2.2 (Approval Workflow) - determines post status transitions.
- F-2.3 (Calendar & Scheduling) - scheduled posts appear on the calendar.
- F-2.4 (Publishing Engine) - executes the actual publish.
- F-5.3 (Integrations - AI) - AI Assist functionality.
- F-5.3 (Integrations - Canva/Stock) - media sourcing.
- F-6.1 (Media Library) - media selection and storage.

### Acceptance Criteria
- Composing a post with 3 platform targets (Instagram, LinkedIn, Facebook) and customizing the caption for LinkedIn displays all 3 previews correctly and stores the LinkedIn override separately.
- Attaching 11 images to a post targeting Instagram shows a warning that Instagram carousels support max 20 images and displays a warning for other platforms with lower limits.
- AI Assist generates 3 caption suggestions within 5 seconds when an API key is configured. Switching provider/model in the AI panel correctly routes the next generation to the selected provider.
- Auto-save creates a draft every 30 seconds; closing and reopening the composer restores the draft.
- A Contributor role user sees only "Save Draft" and "Submit for Approval" buttons - no "Schedule" or "Publish Now."
- Character counters update in real-time as the user types and correctly reflect each platform's limit.

---

## F-2.2 - Approval Workflow

### Purpose
Configurable content review process that ensures posts are vetted by the right people before publishing. Supports both internal team review and external client approval.

### User Stories
- As a workspace Owner, I can configure whether posts require approval before scheduling.
- As a Manager, I receive notifications when posts are submitted for review and can approve or request changes.
- As a Client, I receive an email when posts are ready for my review and can approve or reject them from the client portal.
- As an Editor, I can see the approval status of my posts and respond to reviewer feedback.

### Functional Requirements

**Workflow Modes (configured per workspace in F-1.2):**

| Mode | Behavior |
|------|----------|
| `none` | Posts go directly from the composer to "scheduled" or "draft" status. No review step. |
| `optional` | Authors choose: "Save Draft," "Submit for Approval," or "Schedule" (if role permits). |
| `required_internal` | All posts must be approved by a user with the Manager or Owner role before they can be scheduled. The "Schedule" and "Publish Now" buttons are hidden until the post is approved. |
| `required_internal_and_client` | Same as `required_internal`, but after internal approval, the post transitions to "pending_client" and the client must also approve before scheduling. |

**Status Transitions:**

```
draft ──────────────> scheduled (mode: none, or optional + author chooses to schedule)
draft ──> pending_review ──> approved ──> scheduled (mode: required_internal)
draft ──> pending_review ──> approved ──> pending_client ──> approved ──> scheduled (mode: required_internal_and_client)

At any stage:
  pending_review ──> changes_requested ──> (author edits) ──> pending_review (resubmit)
  pending_client ──> changes_requested ──> (author edits) ──> pending_review (restart)
```

- When a client requests changes, the post goes back to "changes_requested" and the internal team is notified. The post re-enters the internal review cycle before going back to the client.
- Rejected posts (by internal reviewer or client) move to a "rejected" status. The author can edit and resubmit or delete the post.

**Approval Actions:**

*For internal reviewers (Manager, Owner):*
- "Approve" - moves post to "approved" (or "pending_client" if client approval is required).
- "Request Changes" - requires a comment explaining what to fix. Post moves to "changes_requested." Author is notified.
- "Reject" - requires a comment. Post moves to "rejected." Author is notified.

*For clients (via Client Portal F-1.4):*
- "Approve" - moves post to "approved" → "scheduled."
- "Request Changes" - requires a comment. Post moves back to "changes_requested."
- "Reject" - requires a comment. Post moves to "rejected."

**Comments:**
- Two types of comments on each post:
  - **Internal comments:** Visible only to org members (not clients). For team discussion about the post.
  - **External comments:** Visible to both team and client. For communicating with the client about the post.
- Comments are threaded (replies to a specific comment).
- Comments support @mentions of workspace members (triggers a notification).
- Comments are displayed in chronological order within each thread.
- File attachments on comments: images only (for sharing reference screenshots, etc.). Max 5MB per attachment.

**Bulk Operations:**
- In the approval queue view, reviewers can select multiple posts and:
  - Approve all selected.
  - Reject all selected (with a shared comment).
- Bulk approval is only available for internal reviewers, not clients.

**Version History:**
- Every time a post is edited after initial creation, a new version is saved (see PostVersion in F-2.1).
- The approval view shows a "View Changes" button that displays a diff between the current version and the last reviewed version.
- Diff highlights: added text (green), removed text (red), changed media (side-by-side thumbnails).

**Auto-Reminders:**
- If a post has been in "pending_review" for more than a configurable number of hours (default: 24), the system sends a reminder notification to all eligible reviewers.
- If a post has been in "pending_client" for more than a configurable number of hours (default: 48), the system sends a reminder to the client.
- Maximum 2 auto-reminders per post per stage. After that, a workspace Manager is notified that the post is stalled.
- Reminder intervals are configurable per workspace.

**Approval Queue Views:**
- Workspace-level: a "Pending Approval" tab/page showing all posts awaiting review in this workspace, sorted by scheduled date (soonest first).
- Organization-level (for Admins/Owners): "All Pending Approvals" across all workspaces, grouped by workspace.

### Data Model
- `ApprovalAction`: id, post_id, user_id, action (enum: submitted, approved, changes_requested, rejected, resubmitted), comment (text, nullable), created_at.
- `PostComment`: id, post_id, author_id, parent_comment_id (nullable, for threading), body (text), visibility (enum: internal, external), attachment_url (nullable), created_at, updated_at, deleted_at.
- Post status transitions are enforced at the application level with a state machine. Invalid transitions return an error.

### Dependencies
- F-1.2 (Workspace) - workflow mode configuration.
- F-1.3 (RBAC) - determines who can approve.
- F-1.4 (Client Portal) - client approval interface.
- F-2.1 (Composer) - post creation and editing.
- F-7.1 (Notifications) - approval request notifications, reminders.

### Acceptance Criteria
- In `required_internal` mode, an Editor cannot schedule a post - the "Schedule" button is not rendered. After a Manager approves, the post auto-schedules at the time the author originally selected.
- In `required_internal_and_client` mode, a client requesting changes sends the post back to "changes_requested" and notifies the internal team. The post must go through internal review again before returning to the client.
- Version diffs correctly show text additions, deletions, and media changes.
- Auto-reminders fire at the configured interval and stop after 2 reminders.
- Bulk approving 20 posts completes within 3 seconds.

---

## F-2.3 - Content Calendar & Scheduling

### Purpose
The visual calendar is the daily operational hub for agencies. It provides an overview of all content across platforms, supports drag-and-drop scheduling, queue-based auto-scheduling, and bulk import.

### User Stories
- As an Editor, I can see all scheduled, draft, and pending posts on a visual calendar.
- As a Manager, I can drag a post to reschedule it to a different date and time.
- As an Editor, I can set up a content queue that auto-publishes posts at my preferred times.
- As a Manager, I can bulk-import a month's worth of posts from a CSV file.
- As an Org Admin, I can view a cross-workspace calendar to see all clients' content at a glance.

### Functional Requirements

**Calendar Views:**

*Month View:*
- Grid layout with days as columns and weeks as rows.
- Each day cell shows: post count badge per platform (icons), and up to 3 post preview cards.
- If a day has more than 3 posts, a "+N more" link expands the day.
- Posts are color-coded by status: draft (gray), pending approval (orange), scheduled (blue), published (green), failed (red).
- Clicking a post card opens the composer (F-2.1) with that post loaded.

*Week View:*
- 7-column layout with hourly rows.
- Posts are positioned at their scheduled time as cards showing: platform icon, caption snippet (first 50 characters), thumbnail of first media item.
- Cards can be dragged vertically (change time) or horizontally (change day).

*Day View:*
- Single-day timeline with hourly divisions.
- More detailed post cards showing: full platform icon set, caption (first 100 characters), all media thumbnails, author avatar, status badge.

*List View:*
- Table format: date, time, platform(s), caption snippet, status, author, category.
- Sortable by any column.
- Filterable (see below).
- Pagination: 50 posts per page.

**Filtering (applies to all views):**
- By platform: checkbox per connected platform. Multi-select.
- By status: draft, pending_review, pending_client, approved, scheduled, published, failed. Multi-select.
- By category: dropdown of workspace content categories. Multi-select.
- By author: dropdown of workspace members. Multi-select.
- By tag: text input with autocomplete from existing tags.
- By date range: start date and end date pickers.
- Filters are combinable (AND logic). Active filters are shown as removable chips above the calendar.

**Drag-and-Drop Rescheduling:**
- In week and day views, posts can be dragged to a new time slot.
- Dragging a post updates its `scheduled_at` timestamp.
- Only posts with status "draft," "approved," or "scheduled" can be dragged. Pending-approval and published posts are locked.
- A confirmation dialog appears if the new time is in the past or within 5 minutes of the current time.
- Drag-and-drop respects RBAC: only users who can edit the post (Editor+ for own posts, Manager+ for others') can drag.

**Optimal Time Suggestions:**
- For each connected social account, the system analyzes historical engagement data (from F-4.1) to determine the best posting times.
- Suggested times are displayed on the calendar as subtle highlighted slots (e.g., a light green background on the time row).
- Calculation: for each hour of the week, compute the average engagement rate of posts published during that hour over the last 90 days. Top 3 hours per day are highlighted.
- If insufficient data (fewer than 10 posts in the last 90 days), no suggestions are shown. A tooltip explains why.

**Time Slots / Posting Schedule:**
- Per social account, users can define recurring time slots (e.g., "Monday, Wednesday, Friday at 9am and 6pm").
- Time slots represent the default publishing times for queue-based scheduling.
- Time slots are managed in workspace settings → account settings.
- Time slots are visualized on the calendar as dotted outlines on days/times where they recur.

**Queue-Based Scheduling:**
- A "Queue" is defined by: a content category and a set of time slots.
- When a post is "Added to Queue" (from the composer), the system assigns it to the next available time slot for that queue.
- Multiple queues can exist per workspace (e.g., "Educational content - MWF 9am" and "Promotional - TTh 12pm").
- Queue management: view the queue as an ordered list. Posts can be reordered within the queue (drag-and-drop). Reordering changes which slot each post gets assigned to.
- If a queue has no available slots in the next 30 days, the user is warned.

**Bulk Scheduling (CSV Import):**
- Upload a CSV or TSV file with one row per post.
- Columns: date (YYYY-MM-DD), time (HH:MM, 24h format), timezone (optional - defaults to workspace timezone), platform(s) (comma-separated platform identifiers: instagram, facebook, linkedin, tiktok, youtube, pinterest, threads, bluesky, google_business, mastodon), caption (text), media_url (URL to an image/video - fetched and stored in media library on import), category (name - matched to existing categories or created), tags (comma-separated), first_comment (text).
- Column mapping: after upload, the user sees a column mapping interface where they assign each CSV column to a post field. The system attempts auto-detection based on column headers.
- Validation: before import, the system validates all rows and shows errors per row (e.g., "Row 12: date is in the past," "Row 34: platform 'twitter' is not supported"). The user can fix the CSV and re-upload or skip invalid rows.
- Import limit: unlimited posts per upload (processed in batches of 100).
- Media fetching: media URLs are downloaded asynchronously. Posts with failed media downloads are created as drafts with a warning.
- Imported posts enter the approval workflow if required by workspace settings.

**Recurring Posts:**
- When scheduling a post, an "Make recurring" toggle is available.
- Options: repeat every N days / weeks / months. End date (optional - if not set, repeats indefinitely).
- The system creates individual Post records for each recurrence up to 90 days in advance. A background job generates new recurrences as time progresses.
- Each recurrence is an independent post that can be individually edited or cancelled without affecting other recurrences.
- A "Recurring" badge appears on recurring posts with a link to "View all recurrences."

**Holiday/Event Calendar:**
- An overlay on the calendar showing social media awareness days (e.g., "World Coffee Day," "International Women's Day") and public holidays.
- Holiday data: bundled dataset of major international awareness days and US/UK/EU public holidays. Updated with each platform release.
- Users can toggle the overlay on/off.
- Users can add custom events to the calendar (workspace-scoped) - e.g., "Client product launch" or "Campaign start."
- Custom events show as full-width bars on the calendar, similar to all-day events in Google Calendar.

**Cross-Workspace Calendar (Organization Level):**
- Accessible to Org Admins and Owners from the organization dashboard.
- Shows all workspaces' scheduled/published posts in a single calendar view.
- Posts are color-coded by workspace (workspace color from F-1.2 settings).
- Read-only - clicking a post navigates into the specific workspace's calendar.
- Filterable by workspace (multi-select).

**Empty State:**
- When a workspace has no posts (no drafts, no scheduled, no published), the calendar shows a centered empty state:
  - Illustration: a simple calendar icon with a "+" symbol.
  - Heading: "No content scheduled yet."
  - Body text: "Create your first post to see it on the calendar."
  - Primary CTA button: "Create Post" → opens the composer (F-2.1).
  - Secondary text link: "Or import from CSV" → opens the bulk import dialog.
- When filters are active but produce no results, the calendar shows: "No posts match your filters." with a "Clear filters" button.

### Data Model
- `PostingSlot`: id, social_account_id, day_of_week (integer, 0–6), time (time without timezone), is_active (boolean).
- `Queue`: id, workspace_id, name, category_id, social_account_id, created_at, updated_at.
- `QueueEntry`: id, queue_id, post_id, position (integer), assigned_slot_datetime (datetime), created_at.
- `CustomCalendarEvent`: id, workspace_id, title, description, start_date, end_date, color (hex), created_by, created_at.
- `RecurrenceRule`: id, post_id, frequency (enum: daily, weekly, monthly), interval (integer), end_date (nullable), last_generated_at (datetime).

### Dependencies
- F-2.1 (Composer) - post creation and editing.
- F-2.2 (Approval Workflow) - status filtering and post status.
- F-2.4 (Publishing Engine) - publishes posts at scheduled times.
- F-4.1 (Analytics) - optimal time calculations.
- F-1.3 (RBAC) - drag-and-drop permissions.

### Acceptance Criteria
- Month view loads within 2 seconds for a workspace with 200 scheduled posts in the visible month.
- Dragging a post to a new time updates the scheduled_at value and the calendar reflects the change immediately (optimistic UI update).
- Bulk importing a 500-row CSV completes processing within 60 seconds (excluding media download time).
- Queue-based scheduling assigns posts to the correct next available slot and updates the queue order view in real-time.
- Recurring post generation job creates posts for the next 90 days within 5 seconds of the rule being created.
- Cross-workspace calendar correctly displays posts from 50 workspaces with distinct colors.

---

## F-2.4 - Publishing Engine

### Purpose
The backend system responsible for sending posts to social media platforms at the scheduled time. Handles API communication, rate limiting, retry logic, media processing, and status reporting.

### User Stories
- As a user, my scheduled posts are published at the correct time on the correct platform.
- As a user, if a post fails to publish, I am notified and can see the error reason.
- As a user, the first comment is posted automatically after the main post.
- As a self-hosted admin, I can see a log of all publish attempts for debugging.

### Functional Requirements

**Scheduling & Dispatch:**
- A background worker process runs continuously, checking for posts where `scheduled_at <= now()` and `status = 'scheduled'`.
- Poll interval: every 15 seconds.
- When a post is picked up, its status changes to "publishing" (to prevent duplicate processing).
- For each PlatformPost associated with the post, the engine dispatches a publish job to the appropriate platform provider.
- Platform posts are published in parallel (not sequentially) for multi-platform posts.

**Platform Providers:**
- Each supported platform has a dedicated provider module that implements the standard provider interface.
- Provider responsibilities: OAuth token management (refresh if expired), API request construction, media upload, response parsing, error handling.

| Platform | API | Auth Method | Publishing Capabilities |
|----------|-----|-------------|----------------------|
| Facebook Pages | Graph API v21+ | OAuth 2.0 (page access token) | Text posts, single image, multi-image (carousel via multi-photo), video, link posts. Stories. |
| Instagram | Instagram Graph API (via Facebook) | OAuth 2.0 (Instagram business account linked to Facebook page) | Single image, carousel (up to 20 items), Reel (video), Story (image or video). Two-step: create container → publish container. |
| LinkedIn | LinkedIn Marketing API v2 | OAuth 2.0 (3-legged) | Text posts, image posts (up to 20 images), video posts, articles, polls, documents (PDF). Profiles and Company Pages. |
| TikTok | TikTok Content Posting API | OAuth 2.0 | Video posts. Requires video upload → publish flow. Direct publish or "inbox" mode (user publishes from TikTok app). Privacy level setting required. |
| YouTube | YouTube Data API v3 | OAuth 2.0 (Google) | Video upload with title, description, tags, category, privacy status, thumbnail. Shorts detected by aspect ratio + duration. |
| Pinterest | Pinterest API v5 | OAuth 2.0 | Pins: image or video with title, description, link, board_id. |
| Threads | Threads API (via Instagram Graph API) | OAuth 2.0 (Instagram business account) | Text posts, image posts, carousel (up to 20 items), video posts. |
| Bluesky | AT Protocol (XRPC) | Session-based (handle + app password) | Text posts (300 char limit), image posts (up to 4 images), video posts. Rich text with facets (links, mentions, hashtags parsed into facets). |
| Google Business Profile | Google Business Profile API | OAuth 2.0 (Google) | Local posts: What's New, Event, Offer. Image + text. |
| Mastodon | Mastodon API v1 | OAuth 2.0 (per-instance app registration) | Text posts (character limit varies by instance), image (up to 4), video, poll. Content warnings. Visibility: public, unlisted, private, direct. |

**Media Processing:**
- Before publishing, the engine processes media to meet platform requirements:
  - Image resizing: if an image exceeds a platform's max dimensions, resize proportionally. Preserve original in media library.
  - Image format conversion: convert WebP to JPEG for platforms that don't support WebP. Convert PNG to JPEG if file size exceeds platform limits.
  - Video transcoding: if a video's codec, bitrate, or container format is incompatible, transcode using FFmpeg. Target: H.264 codec, AAC audio, MP4 container.
  - Thumbnail generation: extract a frame at 1 second for video thumbnails (used in calendar previews and for YouTube if no custom thumbnail is uploaded).
- Media processing is done asynchronously before the scheduled publish time. A background job processes media for posts scheduled within the next hour.
- If media processing fails, the post is marked as "failed" with error "Media processing failed: [reason]" and the author is notified.

**First Comment:**
- After the main post is successfully published and the platform_post_id is received, the engine posts the first comment using the platform's comment API.
- Delay: 5-second wait between main post publish and first comment (some platforms flag immediate comments as spam).
- Supported platforms for first comment: Instagram (comment on own media), Facebook Pages (comment on own post), LinkedIn (comment on own post), YouTube (comment on own video).
- If the first comment fails, the main post is still considered "published." The first comment failure is logged separately and the author is notified.

**Rate Limit Management:**
- Each platform provider tracks its own rate limits based on API response headers.
- Rate limit state is stored per social account (not globally) since limits are typically per-account.
- Known limits:
  - Instagram: 100 API-published posts per 24-hour rolling window per account. 200 API calls per hour per account.
  - Facebook: 200 API calls per hour per user token. 4,800 posts per 24 hours per page.
  - LinkedIn: 100 API calls per day per member for posting. Company pages: 100 shares per day.
  - TikTok: Varies by app review tier. Default: 5 videos per day.
  - YouTube: per Google Cloud project, reset at midnight US/Pacific: 100 `videos.insert` (upload) calls and 100 `search.list` calls per day, each in its own bucket at 1 unit per call, plus 10,000 units per day for every other method (custom thumbnail and comment = 50 units each).
  - Pinterest: 1,000 API calls per hour.
  - Bluesky: 5,000 actions per hour, 35,000 per day per account.
  - Mastodon: Varies by instance. Typical: 300 posts per 3 hours.
- If a publish attempt hits a rate limit, the post is queued for retry after the rate limit window resets.
- The system proactively checks rate limit headroom before attempting to publish. If the remaining quota is low, posts are delayed and the author is warned.

**Retry Logic:**
- If a publish attempt fails (API error, network timeout, server error), the engine retries with exponential backoff:
  - Retry 1: after 1 minute.
  - Retry 2: after 5 minutes.
  - Retry 3: after 30 minutes.
- After 3 failed retries, the PlatformPost is marked as "failed" with the error message from the last attempt.
- If a multi-platform post succeeds on some platforms and fails on others, the overall post status is "partially_published." Each PlatformPost has its own status.
- Failed PlatformPosts can be manually retried by the author from the calendar or post detail view (a "Retry" button).

**Publish Log:**
- Every publish attempt (including retries) is logged with: timestamp, social_account_id, platform_post_id (if received), HTTP status code, response body (truncated to 1,000 characters), error message (if any), duration (milliseconds).
- Publish logs are viewable per post in the post detail view (accessible to Manager+ roles).
- Logs are retained for 90 days, then deleted by a cleanup job.

**Token Refresh:**
- A background job runs every hour to check all OAuth tokens expiring within the next 24 hours.
- Expiring tokens are refreshed using the platform's refresh token flow.
- If a refresh fails (e.g., user revoked access), the social account is marked as "disconnected" and the workspace Manager is notified.
- Platforms with non-refreshable tokens (Bluesky app passwords don't expire; Mastodon tokens don't expire by default) are skipped.

**Post-Publish Actions:**
- After successful publication, the engine:
  1. Stores the platform_post_id on the PlatformPost record.
  2. Updates the PlatformPost status to "published" and sets published_at.
  3. If all PlatformPosts for a Post are published, updates the Post status to "published."
  4. Triggers the first analytics fetch for the post (scheduled for 1 hour after publish).
  5. Sends a notification to the author ("Your post was published on [platforms]").

### Data Model
- `PublishLog`: id, platform_post_id (FK), attempt_number (integer), status_code (integer, nullable), response_body (text, truncated), error_message (text, nullable), duration_ms (integer), created_at.
- `RateLimitState`: id, social_account_id, platform, requests_remaining (integer), window_resets_at (datetime), last_updated.

### Dependencies
- F-1.5 (Platform API Credentials) - API keys for platform access.
- F-2.1 (Composer) - Post and PlatformPost entities.
- F-2.3 (Calendar) - scheduling timestamps.
- F-6.1 (Media Library) - media assets for upload.
- F-7.1 (Notifications) - publish success/failure notifications.
- F-4.1 (Analytics) - triggers first metric fetch after publish.

### Acceptance Criteria
- A post scheduled for 2:00:00 PM is published within 30 seconds of that time (by 2:00:30 PM).
- A multi-platform post (Instagram + LinkedIn + Facebook) publishes to all 3 platforms in parallel; total time does not exceed the slowest platform + 10 seconds.
- If Instagram rate limit is hit, the post is queued for retry after the window resets; the author is notified within 1 minute.
- After 3 failed retries, the post shows "Failed" status with a human-readable error message and a "Retry" button.
- Video transcoding for a 1-minute 1080p video completes within 60 seconds.
- First comment posts within 10 seconds of the main post being published.
- Token refresh job successfully refreshes tokens before they expire; no posts fail due to expired tokens.

---

## F-2.5 - Social Account Connection

### Purpose
Connect social media accounts to a workspace so the platform can publish content and read engagement data on behalf of the user.

### User Stories
- As a workspace Manager, I can connect my client's Instagram Business account to this workspace.
- As a user, I can see which accounts are connected, their status, and reconnect if needed.
- As a user, I want the connection process to be as simple as clicking "Connect" and completing the platform's OAuth flow.

### Functional Requirements

**Connection Flow:**
- In workspace settings → "Social Accounts," the user sees a grid of supported platforms with a "Connect" button for each.
- Clicking "Connect" initiates the platform's OAuth flow:
  1. User is redirected to the platform's authorization page.
  2. User grants permissions.
  3. User is redirected back to the app with an authorization code.
  4. The app exchanges the code for access + refresh tokens.
  5. The app fetches the account profile (name, avatar, follower count) and stores it.
  6. The account appears in the workspace's connected accounts list.
- For platforms where one OAuth flow grants access to multiple accounts (e.g., Facebook OAuth grants access to multiple Pages), the user is shown a selection screen after OAuth to choose which specific account(s) to connect to this workspace.
- For Bluesky: instead of OAuth, the user enters their handle (e.g., user.bsky.social) and an app password (generated in Bluesky settings). The system creates a session.
- For Mastodon: the user enters their instance URL (e.g., mastodon.social). The system auto-registers an OAuth app on that instance, then proceeds with standard OAuth.

**Connected Account Display:**
- Each connected account shows: platform icon, account name/handle, avatar, follower count (fetched periodically), connection status (connected, token_expiring, disconnected, error).
- Status meanings:
  - `connected`: working normally.
  - `token_expiring`: token expires within 7 days and refresh attempt hasn't happened yet.
  - `disconnected`: token is invalid and refresh failed. Requires re-authentication.
  - `error`: API error on last interaction (with error message).

**Reconnection:**
- If an account is disconnected, a "Reconnect" button initiates the OAuth flow again for that specific account.
- Reconnecting preserves all historical data (posts, analytics) - it only updates the OAuth tokens.

**Disconnection:**
- Workspace Owner/Manager can disconnect an account.
- Disconnecting revokes the OAuth token (if the platform's API supports revocation) and marks the account as disconnected.
- Historical data (published posts, analytics) is retained.
- Scheduled posts targeting this account are paused and the team is notified.

**Account Health Check:**
- A background job checks each connected account every 6 hours by making a lightweight API call (e.g., fetch profile info).
- If the check fails, the account status is updated and the workspace Manager is notified.

**Permissions Required (per platform):**

| Platform | Required Permissions/Scopes |
|----------|-----------------------------|
| Facebook | pages_manage_posts, pages_read_engagement, pages_read_user_content, pages_manage_metadata |
| Instagram | instagram_basic, instagram_content_publish, instagram_manage_comments, instagram_manage_insights |
| LinkedIn | w_member_social, r_member_social (profiles); w_organization_social, r_organization_social (company pages) |
| TikTok | user.info.basic, video.publish, video.upload |
| YouTube | youtube.upload, youtube.readonly, youtube.force-ssl |
| Pinterest | boards:read, pins:read, pins:write |
| Threads | threads_basic, threads_content_publish, threads_manage_insights, threads_manage_replies |
| Bluesky | N/A (session auth) |
| Google Business Profile | business.manage |
| Mastodon | read, write, follow (standard scopes) |

### Data Model
- `SocialAccount`: id, workspace_id, platform (enum), account_platform_id (string - the account's ID on the platform), account_name (string), account_handle (string, nullable), avatar_url (string), follower_count (integer), oauth_access_token (encrypted), oauth_refresh_token (encrypted), token_expires_at (datetime, nullable), instance_url (string, nullable - for Mastodon), connection_status (enum: connected, token_expiring, disconnected, error), last_health_check_at (datetime), last_error (text, nullable), connected_at (datetime).

### Dependencies
- F-1.2 (Workspace) - accounts belong to workspaces.
- F-1.5 (Platform API Credentials) - app credentials for OAuth flows.
- F-2.4 (Publishing Engine) - uses tokens to publish.

### Acceptance Criteria
- Connecting an Instagram Business account completes in under 30 seconds (user time, excluding time spent on Instagram's authorization page).
- After connecting, the account appears in the workspace with correct name, avatar, and follower count.
- A disconnected account shows a clear "Reconnect" button and does not lose historical data.
- Health check detects a revoked token within 6 hours and notifies the Manager.

---
---

# 3. ENGAGEMENT & SOCIAL INBOX

---

## F-3.1 - Unified Social Inbox

### Purpose
Aggregate all inbound engagement (comments, mentions, DMs where API permits, reviews) across all connected accounts in a workspace into a single, manageable feed. Allows team members to respond without leaving the platform.

### User Stories
- As an Editor, I can see all comments and mentions from all connected accounts in one feed.
- As a Manager, I can assign a conversation to a team member for response.
- As an Editor, I can reply to a comment directly from the inbox and the reply posts natively on the platform.
- As a Manager, I can use saved replies to respond quickly to common questions.
- As a Manager, I can see response time metrics for my team.

### Functional Requirements

**Inbox Feed:**
- Default view: chronological feed of all inbound messages, newest first.
- Each message shows: platform icon, account name it was received on, sender name/handle, sender avatar, message text, timestamp, message type badge (comment, mention, DM, review), sentiment badge (positive/neutral/negative), assignment status.
- Messages are grouped by conversation thread where applicable (e.g., all replies to a specific post's comment thread are grouped under that post).
- Clicking a message expands it to show the full conversation context (original post, parent comment, all replies in thread).

**Message Types:**

| Type | Platforms | API Source |
|------|-----------|-----------|
| Comment | Instagram, Facebook, LinkedIn, YouTube, TikTok (read-only), Pinterest, Threads, Bluesky, Mastodon | Platform comment/reply APIs |
| Mention | Instagram, Facebook, LinkedIn, Mastodon, Bluesky | Mentions/tagging APIs |
| DM | Instagram (business accounts with approved permissions), Facebook Pages (Page conversations) | Messaging APIs |
| Review | Google Business Profile | GBP review API |

- For platforms where DM access requires elevated permissions or is not available (LinkedIn, TikTok, Pinterest, YouTube, Threads, Bluesky), the DM message type is not shown.

**Filtering:**
- By platform: multi-select checkboxes.
- By social account: multi-select dropdown (useful if workspace has multiple accounts on the same platform).
- By message type: comment, mention, DM, review.
- By status: unread, open, resolved, archived. Multi-select.
- By assigned team member: dropdown including "Unassigned."
- By sentiment: positive, neutral, negative.
- By date range.
- Free-text search across message content.

**Assignment:**
- Any workspace member with inbox access (Editor+ role) can assign a message to a specific team member.
- Assignment: click the avatar/initials slot on a message → select team member from dropdown.
- Assigned messages appear in the assignee's "My Queue" view.
- Unassigned messages appear in the "Unassigned" queue.
- Assignment triggers a notification to the assignee.

**Replying:**
- Click "Reply" on any message to open a reply composer at the bottom of the conversation thread.
- The reply text is submitted via the platform's API and appears as a native reply on the platform.
- Reply composer shows: text input, character limit (if applicable), option to attach an image (on platforms that support image replies).
- After replying, the message status auto-changes to "resolved" (configurable: auto-resolve on reply, or require manual resolve).

**Saved Replies:**
- Workspace-level library of pre-written response templates.
- Each saved reply has: title (for searchability), body text, optional personalization variables: `{sender_name}`, `{account_name}`, `{post_url}`.
- Inserting a saved reply populates the reply composer. The user can edit before sending.
- Saved replies are managed in workspace settings.

**Internal Notes:**
- On any message, team members can add an internal note (text, visible only to the team, not posted publicly).
- Internal notes appear in the conversation thread with a distinct visual style (e.g., yellow background, "Internal" badge).
- Use case: "Client says don't respond to this" or "Escalate to account manager."

**Sentiment Analysis:**
- Each incoming message is auto-tagged with a sentiment: positive, neutral, or negative.
- Sentiment is determined by a keyword-based rules engine (configurable positive/negative keyword lists per workspace) with optional AI-based sentiment analysis if an AI key is configured (F-5.3).
- Sentiment tags are editable - a team member can manually override the auto-detected sentiment.
- Sentiment is used for filtering and is included in analytics/reports.

**Bulk Actions:**
- Select multiple messages (checkboxes) and:
  - Mark as read.
  - Mark as resolved.
  - Archive.
  - Assign to a team member.
- Bulk actions process within 2 seconds for up to 50 selected messages.

**SLA Timer (optional):**
- Per workspace, a target response time can be configured (e.g., "Respond within 2 hours").
- Unresolved messages show a countdown timer or an "Overdue" badge if the SLA has been exceeded.
- SLA metrics (average response time, SLA compliance rate) are available in analytics (F-4.2).

**Inbox Sync:**
- A background job syncs messages from each connected account every 5 minutes.
- For platforms that support webhooks (Facebook, Instagram via webhook subscriptions), real-time message delivery is used instead of polling.
- New messages trigger a notification (in-app badge count update, optional email/Slack notification).
- Sync retrieves messages from the last 24 hours on each poll. Deduplication ensures messages are not duplicated.

**Empty State:**
- When the inbox has zero messages (no social accounts connected or no engagement yet):
  - Illustration: a speech-bubble icon.
  - Heading: "Your inbox is empty."
  - Body text: "Comments, mentions, and DMs from your connected accounts will appear here."
  - If no social accounts are connected: CTA button "Connect Accounts" → opens the social account connection flow (F-2.5).
  - If accounts are connected but no messages yet: informational text "Messages are synced every 5 minutes. New engagement will appear automatically."
- When filters are active but produce no results: "No messages match your filters." with a "Clear filters" button.

### Data Model
- `InboxMessage`: id, workspace_id, social_account_id, platform_message_id (string, unique per platform), message_type (enum: comment, mention, dm, review), sender_name, sender_handle, sender_avatar_url, body (text), sentiment (enum: positive, neutral, negative), sentiment_source (enum: auto, manual), status (enum: unread, open, resolved, archived), assigned_to (user_id, nullable), parent_message_id (nullable, for threads), related_post_id (nullable - links to PlatformPost if message is a comment on our post), received_at (datetime), created_at.
- `InboxReply`: id, inbox_message_id, author_id (team member who replied), body (text), platform_reply_id (string - from API), sent_at (datetime).
- `InternalNote`: id, inbox_message_id, author_id, body (text), created_at.
- `SavedReply`: id, workspace_id, title, body (text), created_by, created_at, updated_at.
- `InboxSLAConfig`: id, workspace_id, target_response_minutes (integer), is_active (boolean).

### Dependencies
- F-2.5 (Social Account Connection) - connected accounts for message sync.
- F-1.3 (RBAC) - inbox access permissions.
- F-5.3 (AI Integration) - optional AI-based sentiment analysis.
- F-7.1 (Notifications) - new message and assignment notifications.
- F-4.2 (Cross-Account Analytics) - SLA metrics.

### Acceptance Criteria
- New comments on a connected Instagram post appear in the inbox within 5 minutes (polling) or 30 seconds (webhook).
- Replying to an Instagram comment from the inbox posts the reply on Instagram within 5 seconds.
- Saved reply variable `{sender_name}` is replaced with the actual sender's name before insertion.
- Sentiment auto-tagging processes at sync time and does not delay message display.
- SLA timer accurately counts down from the configured target and shows "Overdue" when exceeded.

---
---

# 4. ANALYTICS & REPORTING

---

## F-4.1 - Per-Account Analytics

### Purpose
Provide engagement and growth metrics for each connected social account, sourced from the platform APIs. Data is collected automatically and displayed in dashboards within each workspace.

### User Stories
- As a Manager, I can view follower growth, engagement rate, and reach trends for each connected account.
- As an Editor, I can see which of my posts performed best.
- As a Manager, I can identify the best times to post based on historical data.

### Functional Requirements

**Metrics Collected:**

| Metric | Platforms | Collection Frequency |
|--------|-----------|---------------------|
| Follower/subscriber count | All | Daily |
| Follower growth (net change) | All | Calculated from daily snapshots |
| Post impressions | Instagram, Facebook, LinkedIn, Pinterest, YouTube, Threads, Bluesky, Google Business | Hourly for first 48h, then daily |
| Post reach | Instagram, Facebook, LinkedIn, Threads | Hourly for first 48h, then daily |
| Post engagements (likes, comments, shares, saves, clicks) | All | Hourly for first 48h, then daily |
| Video views | Instagram (Reels), Facebook, YouTube, TikTok, Pinterest, LinkedIn | Hourly for first 48h, then daily |
| Video watch time | YouTube, TikTok | Daily |
| Engagement rate | All (calculated) | Calculated: (total engagements / reach) × 100. If reach unavailable, use impressions. |
| Profile views | Instagram, TikTok (if available) | Daily |
| Website clicks | Instagram, LinkedIn, Pinterest, Google Business | Daily |
| Audience demographics | Instagram, Facebook, YouTube, LinkedIn (company pages), TikTok | Weekly |

**Analytics Dashboard (per workspace, per account):**

*Overview Card:*
- Top-level metrics for a selected date range (default: last 30 days): total impressions, total reach, total engagements, average engagement rate, follower count (current), follower change (delta).
- Comparison: show percentage change versus the previous period of equal length.

*Follower Growth Chart:*
- Line chart showing follower count over time.
- Date range selector: 7 days, 30 days, 90 days, 12 months, custom.
- Tooltip on hover shows exact count and date.

*Engagement Over Time Chart:*
- Stacked bar or line chart showing daily engagements broken down by type (likes, comments, shares, saves).
- Same date range selector.

*Top Performing Posts:*
- Table/card view of posts ranked by engagement rate (or selectable: by reach, by impressions, by total engagements).
- Shows: post thumbnail, caption snippet, published date, platform, and the selected metric value.
- Filterable by content category, date range, platform.
- Top 10 by default, expandable to 50.

*Best Time to Post Heatmap:*
- 7×24 grid (days of week × hours of day) showing average engagement rate for posts published during each time slot.
- Color gradient from low (cool) to high (warm) engagement.
- Based on the last 90 days of data.
- Minimum data threshold: cells with fewer than 3 data points are grayed out with a "Insufficient data" tooltip.

*Audience Demographics (where available):*
- Pie chart or bar chart for: age ranges, gender split, top countries, top cities.
- Data source: platform-provided audience insights APIs.
- Updated weekly.

**Data Collection Engine:**
- A background job fetches analytics data from each platform's API.
- Schedule:
  - For posts published within the last 48 hours: metrics fetched every hour.
  - For posts published 2–30 days ago: metrics fetched daily.
  - For posts published 30+ days ago: no further collection (final snapshot retained).
  - Account-level metrics (followers, demographics): fetched daily.
- Data is stored as time-series snapshots (see Data Model).
- If an API call fails, it is retried on the next scheduled run.

**Data Retention:**
- All collected analytics data is retained indefinitely (cloud and self-hosted).

**Empty State:**
- When an account has no analytics data yet (newly connected, no posts published):
  - Illustration: a bar-chart icon with a placeholder line.
  - Heading: "No analytics data yet."
  - Body text: "Publish your first post and analytics will begin collecting automatically. Initial metrics appear within 1 hour of publishing."
  - CTA button: "Create Post" → opens the composer (F-2.1).
- When the workspace has no connected social accounts:
  - Heading: "Connect an account to see analytics."
  - CTA button: "Connect Accounts" → opens social account connection flow (F-2.5).
- Individual chart empty states: if a specific chart has insufficient data (e.g., fewer than 3 data points for the heatmap), the chart area shows a placeholder with "Not enough data to display this chart. Publish more content and check back later."

### Data Model
- `AnalyticsSnapshot`: id, platform_post_id (FK to PlatformPost), impressions (integer), reach (integer), likes (integer), comments (integer), shares (integer), saves (integer), clicks (integer), video_views (integer, nullable), engagement_rate (decimal), snapshot_at (datetime).
- `AccountMetricsSnapshot`: id, social_account_id, follower_count (integer), following_count (integer), post_count (integer), profile_views (integer, nullable), website_clicks (integer, nullable), snapshot_at (datetime).
- `AudienceDemographics`: id, social_account_id, age_ranges (json), gender_split (json), top_countries (json), top_cities (json), snapshot_at (datetime).

### Dependencies
- F-2.4 (Publishing Engine) - triggers first analytics fetch after publish.
- F-2.5 (Social Account Connection) - connected accounts and tokens for API access.

### Acceptance Criteria
- Analytics dashboard for an account with 500 posts loads within 3 seconds.
- Follower growth chart accurately reflects daily net changes.
- Best time heatmap correctly identifies the highest-engagement time slots.
- Data collection job handles API rate limits gracefully (backs off and retries).

---

## F-4.2 - Cross-Account & Cross-Workspace Analytics

### Purpose
Organization-level dashboards that let agency owners see the health of all clients at a glance, compare performance, and track team productivity.

### User Stories
- As an Org Admin, I can see which workspaces are performing well and which need attention.
- As a Manager, I can see my team's average approval turnaround time and inbox response time.
- As an Org Admin, I can compare engagement rates across all clients.

### Functional Requirements

**Organization Dashboard:**

*Client Health Overview:*
- Card grid showing each workspace with: workspace name, icon, total posts published (this month), average engagement rate (this month), follower growth delta (this month), pending approvals count, failed posts count.
- Color-coded health indicator: green (above average), yellow (average), red (below average or issues).
- "Below average" is defined as below the median engagement rate across all workspaces in the org.

*Cross-Workspace Comparison Table:*
- Sortable table with columns: workspace name, platform(s), posts published, impressions, reach, engagement rate, follower growth, average response time (inbox).
- Date range selector (default: current month).
- Export as CSV.

*Team Performance Metrics:*
- Table of org members with: name, posts created (count), average approval turnaround time (hours between "pending_review" and "approved"), average inbox response time (minutes between message received and first reply), posts currently assigned in inbox.
- Date range selector.
- Filterable by workspace.

**Alerts:**
- Configurable alerts at the org level:
  - "Engagement rate dropped below [threshold]% for [workspace]." Threshold is configurable per workspace.
  - "No posts published for [workspace] in the last [N] days." N is configurable.
  - "[N] posts have failed in the last 24 hours across all workspaces."
- Alerts sent to Org Admins via in-app notification and email.

### Data Model
- Cross-workspace analytics are computed on-the-fly by querying per-workspace data (F-4.1) with workspace-level aggregation. No separate storage needed.
- Team performance metrics query: PostVersion (approval timestamps), InboxMessage (response timestamps).
- `OrgAlert`: id, organization_id, alert_type (enum), workspace_id (nullable), threshold_value, is_active (boolean).

### Dependencies
- F-4.1 (Per-Account Analytics) - source data.
- F-3.1 (Inbox) - response time data.
- F-2.2 (Approval Workflow) - approval turnaround data.
- F-7.1 (Notifications) - alert delivery.

### Acceptance Criteria
- Org dashboard loads within 5 seconds for an organization with 50 workspaces.
- Cross-workspace comparison CSV export includes all visible columns and respects the selected date range.
- Team performance accurately calculates average approval turnaround time (verified against manual calculation on 10 sample posts).

---

## F-4.3 - Report Builder

### Purpose
Generate branded PDF reports for client delivery. Reports combine analytics data, commentary, and visualizations into a professional document that agencies can share with clients.

### User Stories
- As a Manager, I can create a monthly performance report for my client in 5 minutes.
- As a Manager, I can white-label the report with my agency's branding.
- As a Manager, I can schedule reports to auto-generate and email to my client monthly.
- As a Client, I can view and download reports shared with me.

### Functional Requirements

**Report Creation:**
- "Create Report" button in the workspace analytics section.
- Step 1: Choose a template or start from scratch.
- Step 2: Configure report parameters: title, date range, social accounts to include, content categories to include.
- Step 3: Report editor - a drag-and-drop editor for arranging report sections.

**Report Sections (building blocks):**

| Section Type | Content |
|-------------|---------|
| Cover page | Report title, date range, workspace logo (or agency logo if white-labeled), generated date. |
| Executive summary | Text block where the user writes a manual summary/commentary. Supports basic rich text (bold, italic, bullet points). |
| Key metrics | A row of metric cards (impressions, reach, engagements, engagement rate, follower growth) with period-over-period comparison. User selects which metrics to show. |
| Follower growth chart | Line chart from F-4.1. User selects which accounts to include. |
| Engagement breakdown chart | Bar chart of engagements by type over the date range. |
| Top performing posts | Grid of top N posts with thumbnails, captions, and metrics. N is configurable (default: 5). |
| Best time heatmap | The heatmap from F-4.1. |
| Platform breakdown | Pie chart or table showing metrics split by platform. |
| Content category performance | Table or chart showing metrics per content category. |
| Custom text | A freeform text block for additional commentary. |
| Audience demographics | Pie/bar charts from F-4.1. |

- Sections can be reordered by dragging.
- Sections can be added or removed.
- Each section has a toggle to include/exclude it from the final report.

**Templates:**
- Pre-built templates: "Monthly Overview," "Campaign Report," "Quarterly Review."
- Users can save a report configuration as a custom template for reuse.
- Templates store: which sections are included, their order, and default metric selections. Data is not stored - it's fetched fresh on generation.

**White-Label Branding:**
- If white-label is configured (F-5.2), reports use: agency logo (in header and cover page), agency colors (for chart accents and section headers), agency name and contact info (in footer).
- If no white-label is configured, reports use the platform's default branding.
- The platform's own branding is never shown if white-label is active.

**Generation & Export:**
- "Generate Report" button produces a rendered report.
- Preview: the report is rendered as HTML in a preview pane.
- Export options: download as PDF, download raw data as CSV.
- PDF generation: server-side rendering using WeasyPrint (Python-native HTML-to-PDF library). Charts are pre-rendered as SVG images and embedded in the HTML template before PDF conversion. WeasyPrint is chosen over headless browser solutions (Playwright, Puppeteer) because it adds no external binary dependencies, keeps the Docker image small, and integrates natively with Django templates. CSS limitations (no flexbox/grid in WeasyPrint) are handled by using table-based and float-based layouts in report templates only. If WeasyPrint's CSS support proves insufficient for complex layouts in future iterations, a migration path to a headless browser renderer is available but not required at launch.

**Scheduled Reports:**
- Users can configure a report to auto-generate on a schedule: weekly (every Monday), biweekly, monthly (1st of each month).
- On the scheduled date, the system generates the report with the latest data for the configured date range (e.g., "last 30 days" is always relative to the generation date).
- The generated report is emailed to configured recipients (workspace members and/or client email addresses).
- Email subject and body text are configurable. Default subject: "[Workspace Name] - [Report Title] - [Date Range]."

**Shareable Link:**
- Each generated report can be shared via a URL.
- The URL renders the report as a read-only web page (same HTML as the preview).
- Access control: optionally password-protected. Optionally set an expiry date after which the link stops working.
- Shareable links are listed in the Client Portal (F-1.4).

### Data Model
- `Report`: id, workspace_id, title, date_range_start, date_range_end, social_account_ids (json array), category_ids (json array), sections (json - ordered list of section configs), template_id (nullable), created_by, created_at, updated_at.
- `ReportGeneration`: id, report_id, generated_at, pdf_url (string - stored file path/URL), html_url (string), share_token (string, unique), share_password_hash (nullable), share_expires_at (datetime, nullable).
- `ReportSchedule`: id, report_id, frequency (enum: weekly, biweekly, monthly), recipients (json array of emails), email_subject, email_body, next_run_at (datetime), is_active (boolean).

### Dependencies
- F-4.1 (Analytics) - data source for all report sections.
- F-5.2 (White-Label) - branding for reports.
- F-1.4 (Client Portal) - reports visible to clients.
- F-7.1 (Notifications) - scheduled report delivery.

### Acceptance Criteria
- Generating a report for a 30-day period with 5 sections completes in under 10 seconds.
- PDF output is well-formatted with no visual artifacts, correct charts, and proper white-label branding.
- Scheduled reports generate and email on the configured schedule within 1 hour of the scheduled time.
- Shareable link with password rejects access without the correct password.
- A report with an expired share link shows a "This link has expired" page.

---
---

# 5. PLATFORM CONFIGURATION

---

## F-5.1 - Authentication & User Accounts

### Purpose
User registration, login, and session management. Supports email/password, social OAuth login, and magic links for clients.

### User Stories
- As a new user, I can sign up with email/password or Google/GitHub OAuth.
- As a returning user, I can log in and be taken to my last-used workspace.
- As a client, I can access the platform via a magic link without a password.

### Functional Requirements

**Registration:**
- Email + password: email must be unique across the platform. Password minimum: 8 characters, no other complexity requirements. Password is hashed with bcrypt (cost factor 12).
- OAuth login: Google and GitHub. On first OAuth login, an account is created automatically. The user's name and avatar are populated from the OAuth profile.
- After registration, an Organization is automatically created for the user (F-1.1) with sensible defaults - no setup steps or prompts. If the user was invited to an existing organization, no new organization is created - they join the existing one.

**Login:**
- Email + password form.
- "Continue with Google" and "Continue with GitHub" OAuth buttons.
- "Forgot password" flow: enter email → receive a password reset link (expires in 1 hour) → set new password.
- On successful login, the user is redirected to their last-used workspace. If no workspace exists, they see the empty organization dashboard with a prompt to create their first workspace.

**Sessions:**
- Session token stored as an HTTP-only, secure, SameSite=Lax cookie.
- Session duration: 30 days (sliding - refreshed on each request).
- Users can view and revoke active sessions from their account settings ("Active Sessions" list showing device, IP, last active time).

**Magic Links (for clients):**
- See F-1.4 for full magic link specification.

**Account Settings (per user):**
- Name, email, avatar.
- Change password.
- Connected OAuth providers (link/unlink Google, GitHub).
- Notification preferences (see F-7.1).
- Active sessions.
- Two-factor authentication (TOTP via authenticator app).

**Two-Factor Authentication (2FA):**
- Optional. Users can enable TOTP-based 2FA from account settings.
- Setup: scan QR code with authenticator app, enter confirmation code.
- On subsequent logins, after password, the user is prompted for a TOTP code.
- Recovery codes: 10 one-time-use codes generated during 2FA setup. Stored hashed.
- Org Owners can enforce 2FA for all org members (configurable in org settings).

### Data Model
- `User`: id, email (unique), name, avatar_url, password_hash (nullable - null for OAuth-only users), totp_secret (encrypted, nullable), totp_recovery_codes (encrypted json, nullable), totp_enabled (boolean), created_at, updated_at.
- `OAuthConnection`: id, user_id, provider (enum: google, github), provider_user_id, provider_email, created_at.
- `Session`: id, user_id, token_hash, device_info (string), ip_address, last_active_at, created_at, expires_at.

### Dependencies
- F-1.1 (Organization) - org creation during signup.
- F-1.3 (RBAC) - roles assigned post-authentication.
- F-1.4 (Client Portal) - magic link auth.

### Acceptance Criteria
- Registration with email/password completes in under 5 seconds.
- OAuth login with Google redirects, authenticates, and returns the user to the app within 10 seconds.
- 2FA setup generates a valid QR code and accepts the confirmation code within a 30-second TOTP window.
- An expired session redirects to the login page without errors.

---

## F-5.2 - White-Label Configuration

### Purpose
Allow agencies to completely rebrand the platform with their own identity. When configured, the agency's clients see the agency's brand - not the platform's.

### User Stories
- As an Org Owner, I can upload my agency's logo and set brand colors.
- As an Org Owner, I can point my agency's subdomain to the platform.
- As a client, I see my agency's branding on the login page, portal, reports, and emails.

### Functional Requirements

**Branding Settings (org level):**

| Setting | Detail |
|---------|--------|
| Agency logo | Image upload (PNG, SVG, JPG). Max 2MB. Used in: sidebar, login page, client portal header, report header/footer, email header. Two variants: full logo (horizontal) and icon (square, for favicon and compact displays). |
| Primary color | Hex color code. Applied to: sidebar accent, buttons, links, chart accents, report section headers. |
| Secondary color | Hex color code. Applied to: hover states, secondary buttons, chart secondary color. |
| Agency name | Text. Shown in: page title, email sender name, report footer. |
| Agency contact info | Email, phone, website URL. Shown in: report footer, login page footer. |
| Favicon | Image upload (ICO, PNG, 32x32 or 64x64). Replaces the platform's favicon in the browser tab. |
| Login page | Custom background image (upload, max 5MB), custom welcome text (max 200 characters). |

**Custom Domain:**
- The agency can configure a custom subdomain (e.g., social.myagency.com) or a full custom domain.
- Setup flow: (1) Agency enters desired domain in settings, (2) system provides DNS instructions (CNAME record pointing to the platform's domain), (3) agency configures DNS, (4) system verifies DNS resolution, (5) SSL certificate is auto-provisioned (Let's Encrypt).
- DNS verification: the system checks DNS every 5 minutes for 72 hours after domain entry. On successful verification, the custom domain is activated.
- All platform URLs for that organization are served under the custom domain.
- The default platform URL (app.platform.com/org/...) redirects to the custom domain if configured.
- **Scaling note (cloud):** Custom domains use Caddy's on-demand TLS, which provisions certificates at request time. This works well for a single-VPS deployment. If the cloud version scales to multiple instances behind a load balancer, all HTTPS termination must route through a single Caddy instance (or a shared certificate store like Caddy's `storage` directive backed by a database/S3) so that on-demand TLS challenges succeed. This is a post-launch scaling concern, not a launch blocker - document the migration path when horizontal scaling becomes necessary.

**Email Branding:**
- All outgoing emails (approval requests, magic links, report deliveries, notifications) use:
  - Agency logo in header.
  - Agency name as sender name.
  - Reply-to address: configurable (default: agency contact email from settings).
  - Custom email domain (e.g., notifications@myagency.com): requires DNS setup (SPF, DKIM, DMARC records). Instructions provided in settings. Uses a third-party email sending service integration.
- If no custom email domain is set, emails are sent from the platform's default domain with the agency name as the display name.

**Scope of White-Label:**
- White-label applies to: client portal, login page, all emails sent by the system, all reports, the sidebar logo.
- White-label does NOT apply to: the internal dashboard for the agency's own team members (they see the platform brand in the full app, but can toggle "Preview as client" to see the white-labeled view).

### Data Model
- `WhiteLabelConfig`: id, organization_id, agency_name, agency_logo_url, agency_icon_url, primary_color (hex string), secondary_color (hex string), agency_email, agency_phone, agency_website, favicon_url, login_background_url, login_welcome_text, custom_domain (string, nullable), custom_domain_verified (boolean), custom_email_domain (nullable), custom_email_verified (boolean), created_at, updated_at.

### Dependencies
- F-1.1 (Organization) - white-label is org-scoped.
- F-1.4 (Client Portal) - rendered with white-label.
- F-4.3 (Reports) - reports use white-label branding.
- F-7.1 (Notifications) - emails use white-label branding.

### Acceptance Criteria
- Uploading a logo and setting colors immediately reflects in the client portal (no cache delay > 5 seconds).
- Custom domain works with a valid CNAME record within 10 minutes of DNS propagation.
- SSL certificate is provisioned automatically within 5 minutes of DNS verification.
- A client accessing the white-labeled portal sees zero references to the platform's own brand.
- Emails sent from the platform use the agency name and logo in the header.

---

## F-5.3 - Integrations

### Purpose
Connect the platform to external tools for design, media, communication, automation, and AI.

### User Stories
- As an Editor, I can open Canva from the composer and bring a finished design back into my post.
- As a Manager, I can receive approval notifications in Slack.
- As an Editor, I can use AI to generate captions with my org's OpenAI API key.
- As a developer, I can use the REST API to create posts programmatically.

### Functional Requirements

**Design & Media Integrations:**

*Canva:*
- A "Design in Canva" button in the post composer (F-2.1) opens the Canva editor via the Canva Connect API (formerly Canva Button).
- After the user finishes designing, the resulting image is exported to the platform and saved in the workspace media library.
- Supported Canva export formats: PNG, JPG.
- Canva integration requires a Canva API key configured at the org level.
- **Self-hosted note:** The Canva Connect API requires approval through Canva's developer program. Self-hosters must apply for their own Canva developer access (https://www.canva.dev/) and create a Canva integration to obtain API credentials. This approval process can take days to weeks. The platform should document this clearly in the self-hosted setup guide, and the Canva integration UI should display a help link with setup instructions when no API key is configured.

*Unsplash, Pexels, GIPHY:*
- In the composer's media picker, a "Stock Media" tab provides search across Unsplash (photos), Pexels (photos + video), and GIPHY (GIFs).
- Search results display a grid of thumbnails. Clicking a result adds it to the post and saves it to the workspace media library.
- Attribution: Unsplash and Pexels require attribution under their licenses. The platform auto-appends a caption note (configurable: on by default, toggleable off).
- API keys: Unsplash and Pexels require API keys configured at the org level (free tiers available). GIPHY uses their public beta key for basic access.

**Communication Integrations:**

*Slack:*
- Configurable per workspace. Connect a Slack workspace and select a channel for notifications.
- Events that can trigger Slack notifications (each toggleable): new post submitted for approval, post approved, post rejected, post published, post failed, new inbox message, SLA overdue.
- Slack messages include: event description, post preview (caption snippet, thumbnail), link to the post in the platform.
- Connection via Slack OAuth (Slack App with incoming-webhooks and chat:write scopes).

*Email (SMTP):*
- Self-hosted deployments configure SMTP settings (host, port, username, password, TLS) for all outbound email.
- Cloud version uses the platform's managed email service.
- Email templates are customizable (HTML/text) for: invitation, magic link, approval request, report delivery, password reset.

**AI Integration:**

- Configurable at the org level. Settings page: Organization → Settings → "AI Providers."
- Three supported providers, each configured independently. Users can configure one, two, or all three simultaneously. One is designated as the default.

| Provider | Configuration Fields |
|----------|---------------------|
| OpenAI | API key, default model (dropdown: gpt-4o, gpt-4o-mini, gpt-4.1, gpt-4.1-mini, gpt-4.1-nano, o3-mini, or custom model ID string) |
| Anthropic | API key, default model (dropdown: claude-sonnet-4-20250514, claude-haiku-4-5-20251001, or custom model ID string) |
| OpenRouter | API key, default model (text field - OpenRouter provides access to hundreds of models, so this is a free-text model identifier, e.g., "anthropic/claude-sonnet-4", "google/gemini-2.5-pro", "meta-llama/llama-4-maverick"). A "Browse models" link opens OpenRouter's model directory in a new tab for reference. |

- **Default provider setting:** A dropdown at the top of the AI settings page selects which provider is the default when AI features are invoked from the composer or inbox. Options: OpenAI, Anthropic, or OpenRouter (only providers with a configured API key appear in the dropdown).
- **Test Connection:** Each provider has a "Test" button that sends a simple prompt ("Reply with OK") and validates that the API key and model are working. Displays success with the model name and response latency, or failure with the error message.
- **Per-generation model override in the composer (see F-2.1):** When a user triggers any AI action in the composer, a small provider/model selector appears in the AI panel allowing them to override the default for that specific generation. This does not change the org-wide default.
- AI features throughout the platform (composer AI assist, sentiment analysis in inbox) use the default provider unless overridden.
- If no AI provider is configured, AI features show a greyed-out state with a tooltip: "Configure an AI provider in Organization Settings to enable this feature."
- No AI usage limits or credits - usage is limited only by the user's own API key quota with each provider.
- API keys are stored encrypted at rest (AES-256-GCM), same encryption approach as platform credentials.

**Automation (REST API & Webhooks):**

*REST API:*
- Full CRUD API for: organizations (read), workspaces (read), posts (create, read, update, delete), social accounts (read), analytics (read), inbox messages (read, reply), media (upload, read), reports (generate, read).
- Authentication: API keys (bearer tokens) scoped to an organization. Keys are created/revoked in org settings.
- Each API key has a configurable scope: "full access" or restricted to specific resources (e.g., "posts: read/write, analytics: read-only").
- Rate limiting: 1,000 requests per hour per API key. Configurable for self-hosted.
- API documentation: auto-generated OpenAPI/Swagger spec served at /api/docs.
- Pagination: cursor-based for list endpoints.
- Filtering: query parameters matching the UI filter options.

*Webhooks (outbound):*
- Configurable per workspace. Users can register webhook URLs that receive HTTP POST requests when events occur.
- Supported events: post.created, post.approved, post.scheduled, post.published, post.failed, inbox_message.received, inbox_message.replied, report.generated.
- Webhook payload: JSON containing event type, timestamp, and the relevant resource data (e.g., the full post object for post events).
- Webhook delivery: POST request with HMAC-SHA256 signature in a header for payload verification.
- Retry: 3 retries with exponential backoff on non-2xx responses.
- Webhook logs: last 100 deliveries per webhook endpoint, showing status code, response time, payload size.

*Zapier / Make / n8n:*
- The REST API and webhooks enable integration with automation platforms.
- (Future) Dedicated Zapier triggers and actions as a separate project.

**Storage Integrations:**

*Google Drive:*
- Import media from Google Drive into the workspace media library.
- In the media picker, a "Google Drive" tab lets users browse their Drive and select files.
- Requires Google OAuth with drive.readonly scope.

*Dropbox:*
- Same as Google Drive, using Dropbox Chooser API.
- No OAuth needed - the Dropbox Chooser widget handles authentication.

### Data Model
- `IntegrationConfig`: id, organization_id, integration_type (enum: canva, unsplash, pexels, giphy, slack, smtp, google_drive, dropbox), config (encrypted json - API keys, OAuth tokens, SMTP settings), is_active (boolean), created_at, updated_at.
- `AIProviderConfig`: id, organization_id, provider (enum: openai, anthropic, openrouter), api_key (encrypted), default_model (string), is_active (boolean), created_at, updated_at.
- `AIDefaultProvider`: id, organization_id, ai_provider_config_id (FK - points to the provider/model used by default when AI features are invoked).
- `SlackWorkspaceConfig`: id, workspace_id, slack_team_id, slack_channel_id, slack_channel_name, webhook_url, events (json array of enabled event types), oauth_token (encrypted).
- `APIKey`: id, organization_id, name, token_hash, scopes (json), last_used_at, created_at, revoked_at (nullable).
- `WebhookEndpoint`: id, workspace_id, url, secret (for HMAC), events (json array), is_active (boolean), created_at.
- `WebhookDelivery`: id, webhook_endpoint_id, event_type, payload (json), response_status_code (integer, nullable), response_time_ms (integer, nullable), attempt_number (integer), delivered_at.

### Dependencies
- F-2.1 (Composer) - Canva, stock media, AI in composer.
- F-3.1 (Inbox) - AI sentiment analysis.
- F-7.1 (Notifications) - Slack notifications.
- F-6.1 (Media Library) - media from integrations saved to library.

### Acceptance Criteria
- Canva button opens Canva and returns a design within the user's session (no page reload).
- Unsplash search returns results within 2 seconds.
- Slack notification for a published post arrives in the configured channel within 30 seconds of publication.
- AI caption generation returns 3 suggestions within 5 seconds when using OpenAI GPT-4o. Switching to Anthropic Claude in the composer AI panel correctly routes the request to the Anthropic API. Switching to an OpenRouter model correctly routes via OpenRouter.
- REST API responds within 200ms for simple read endpoints.
- Webhook deliveries include correct HMAC signature and retry on failure.

---
---

# 6. MEDIA MANAGEMENT

---

## F-6.1 - Media Library

### Purpose
Per-workspace asset management system for organizing, storing, and reusing images, videos, and other media across posts.

### User Stories
- As an Editor, I can upload images and videos and organize them into folders.
- As an Editor, I can search for media by name or tag.
- As a Manager, I can see which posts use a particular media asset.
- As an Editor, I can edit images (crop, resize) without leaving the platform.

### Functional Requirements

**Upload:**
- Drag-and-drop upload area. Multiple files supported simultaneously.
- Bulk upload: up to 50 files at once.
- Supported formats: JPEG, PNG, WebP, GIF, SVG (images); MP4, MOV, AVI, WebM (video); PDF (for LinkedIn documents).
- File size limits: images up to 20MB each, videos up to 1GB each.
- Upload progress indicator per file.
- On upload, the system auto-generates: a thumbnail (for images and videos), metadata (dimensions, duration, file size, format).

**Organization:**
- Folders: create, rename, delete, nest (up to 3 levels deep). Drag-and-drop files between folders.
- Tags: freeform tags on any asset. Multiple tags per asset. Tag autocomplete from existing tags in the workspace.
- Starred assets: mark important assets for quick access (filtered view).

**Search & Filtering:**
- Full-text search across file names and tags.
- Filter by: file type (image, video, document, GIF), folder, upload date range, uploaded by, starred status.
- Sort by: name, date uploaded, file size.

**Media Detail View:**
- Clicking an asset opens a detail panel showing: full preview (image renders at display size; video plays inline), metadata (dimensions, file size, format, duration, upload date, uploaded by), tags (editable), usage (list of posts that reference this asset - links to those posts).
- Edit capabilities:
  - Image: crop, resize, rotate, flip. Edits create a new version; original is retained.
  - Video: trim (set start and end time). Trim creates a new version.
- Download original file.
- Delete asset: prevented if the asset is referenced by any scheduled (not yet published) posts. A warning shows which posts reference it. For published posts, deletion is allowed (the already-published content is unaffected).

**Version History:**
- Each edit creates a new version of the asset.
- Version history panel shows: version number, creation date, change description (e.g., "Cropped to 4:5"), thumbnail.
- Users can restore a previous version (makes it the current version).

**Shared Organization Library:**
- In addition to workspace-scoped libraries, an org-wide "Shared Library" exists for brand assets (logos, fonts, templates) that are used across workspaces.
- Only Org Admins can upload to the shared library.
- All workspace members can browse and use assets from the shared library in the composer.
- Shared assets are read-only in workspace context (cannot be edited or deleted from within a workspace).

**Platform Compatibility Warnings:**
- When selecting media for a post, the library displays warnings if the asset doesn't meet the target platform's requirements (see F-2.1 media validation).
- Warnings appear as badges on the asset thumbnail: yellow (warning - will work but not optimal), red (error - will fail or be rejected by the platform).

**Empty State:**
- When the media library has no assets:
  - Illustration: an image/video icon with an upload arrow.
  - Heading: "No media uploaded yet."
  - Body text: "Upload images and videos to organize and reuse across your posts."
  - Primary CTA: a large drag-and-drop zone with "Drop files here or click to upload."
  - Secondary text link: "Or import from Google Drive / Dropbox" (if integrations are configured).
- When search/filter produces no results: "No media matches your search." with a "Clear search" button.

### Data Model
- `MediaAsset`: id, workspace_id (nullable - null for shared org library), organization_id, filename, original_filename, file_url (storage path), thumbnail_url, file_type (enum: image, video, gif, document), mime_type, file_size_bytes (integer), width (integer, nullable), height (integer, nullable), duration_seconds (decimal, nullable), folder_id (nullable), tags (json array), is_starred (boolean), uploaded_by (user_id), current_version_id, created_at, updated_at.
- `MediaAssetVersion`: id, media_asset_id, version_number (integer), file_url, thumbnail_url, change_description (string), file_size_bytes, width, height, duration_seconds (nullable), created_by, created_at.
- `MediaFolder`: id, workspace_id, parent_folder_id (nullable), name, created_at, updated_at.

### Dependencies
- F-2.1 (Composer) - media picker in composer.
- F-5.3 (Integrations) - Canva, stock media, Google Drive, Dropbox import.
- F-2.4 (Publishing Engine) - media processing before publish.

### Acceptance Criteria
- Uploading 10 images completes within 15 seconds and all thumbnails are generated.
- Searching 1,000 assets by tag returns results within 1 second.
- Attempting to delete a media asset referenced by a scheduled post is blocked with a clear message listing the affected posts.
- Image crop tool produces the cropped version within 3 seconds for a 5MB image.
- Shared library assets are visible across all workspaces but cannot be edited or deleted from workspace context.

---
---

# 7. NOTIFICATION SYSTEM

---

## F-7.1 - Notification System

### Purpose
Centralized notification engine that powers all alerts and messages across the platform. Every system (publishing, approval, inbox, analytics, scheduling) emits events that the notification system routes to the correct channels.

### User Stories
- As an Editor, I receive an in-app notification when my post is approved or rejected.
- As a Manager, I receive a Slack message when a post fails to publish.
- As a Client, I receive an email when posts are ready for my review.
- As a user, I can configure which notifications I receive and on which channels.

### Functional Requirements

**Notification Channels:**

| Channel | Detail |
|---------|--------|
| In-app | Bell icon in the top navigation bar with an unread count badge. Clicking opens a notification drawer showing recent notifications. Notifications are marked as read when clicked or when the user clicks "Mark all as read." |
| Email | Sent to the user's registered email. Uses the org's white-label branding if configured. Batching: if multiple events occur within 5 minutes, they are batched into a single email (configurable delay). |
| Slack | Sent to the workspace-configured Slack channel (F-5.3). One message per event (no batching). |
| Webhook | Sent to registered webhook endpoints (F-5.3). One delivery per event. |

**Events & Default Channels:**

| Event | Default: In-app | Default: Email | Default: Slack |
|-------|-----------------|----------------|----------------|
| Post submitted for approval | Reviewers: yes | Reviewers: yes | Yes |
| Post approved | Author: yes | Author: no | Yes |
| Post changes requested | Author: yes | Author: yes | Yes |
| Post rejected | Author: yes | Author: yes | Yes |
| Post published | Author: yes | Author: no | Yes |
| Post failed | Author: yes | Author: yes | Yes |
| New inbox message | Assigned: yes, Unassigned: workspace managers | No | Configurable |
| Inbox SLA overdue | Assigned: yes, Manager: yes | Manager: yes | Yes |
| Client approval requested | Client: no (separate magic link email) | Client: yes (magic link) | No |
| Team member invited | Invitee: N/A | Invitee: yes (invite email) | No |
| Social account disconnected | Workspace managers: yes | Workspace managers: yes | Yes |
| Report generated | Configured recipients | Configured recipients: yes | No |
| Engagement alert | Org admins: yes | Org admins: yes | Configurable |

**User Preferences:**
- Each user can configure their notification preferences from account settings.
- Per event type, per channel: on/off toggle.
- "Quiet hours" setting: suppress non-critical notifications during specified hours (timezone-aware).
- "Digest mode" for email: instead of individual emails, receive a daily digest summarizing all notifications from the past 24 hours.

**In-App Notification Drawer:**
- Shows the 50 most recent notifications, sorted by date (newest first).
- Each notification shows: icon (based on event type), title (e.g., "Post approved"), body (e.g., "Your post 'New product launch' was approved by [Manager Name]"), timestamp, read/unread indicator.
- Clicking a notification navigates to the relevant context (e.g., clicking a "Post approved" notification navigates to that post on the calendar).
- "View all notifications" link at the bottom opens a full-page notification history (paginated, filterable by event type and read status).

**Notification Delivery:**
- Notifications are generated asynchronously by background workers (not in the request path).
- Target delivery time: within 30 seconds of the triggering event.
- Email delivery: via configured SMTP (self-hosted) or managed email service (cloud).
- Slack delivery: via Slack webhook or API.
- Failed deliveries are retried up to 3 times with exponential backoff. Permanently failed deliveries are logged but not retried further.

### Data Model
- `Notification`: id, user_id (recipient), event_type (enum), title, body, data (json - contextual data like post_id, workspace_id), is_read (boolean), read_at (datetime, nullable), created_at.
- `NotificationPreference`: id, user_id, event_type, channel (enum: in_app, email, slack), is_enabled (boolean).
- `NotificationDelivery`: id, notification_id, channel, status (enum: pending, delivered, failed), error_message (nullable), delivered_at (nullable), attempts (integer).

### Dependencies
- All features emit events that this system consumes.
- F-5.2 (White-Label) - email branding.
- F-5.3 (Integrations - Slack) - Slack delivery.

### Acceptance Criteria
- In-app notifications appear within 5 seconds of the triggering event (via WebSocket or polling).
- Email notifications are delivered within 60 seconds of the event (excluding email provider latency).
- A user who disables email for "Post published" events does not receive emails for that event, but still receives in-app notifications if enabled.
- Quiet hours correctly suppress notifications during the specified window.
- The notification drawer correctly shows unread count and marks notifications as read on click.

---
---

# 8. ADDITIONAL FEATURES

---

## F-8.1 - Global Search

### Purpose
Provide a fast, workspace-scoped search that lets users find posts, drafts, templates, media, and inbox messages without manually browsing through calendars, libraries, or feeds. As workspaces accumulate hundreds of posts over months, search becomes essential for daily operations.

### User Stories
- As an Editor, I can search for a post I created 3 months ago by typing part of the caption.
- As a Manager, I can find all posts tagged with a specific campaign name.
- As an Editor, I can search my media library for a specific image by filename or tag.
- As a Manager, I can find a specific inbox conversation by searching for the sender's name or message content.

### Functional Requirements

**Search Interface:**
- A search bar is always visible in the top navigation bar (keyboard shortcut: Cmd/Ctrl+K to focus).
- Typing opens a search dropdown that shows results grouped by type: Posts, Media, Inbox Messages, Templates.
- Each result shows: type icon, title/caption snippet (highlighted match), date, status.
- Clicking a result navigates to the relevant item (post in calendar/detail view, media in library, inbox message in inbox, template in composer).
- Search is scoped to the current workspace. A toggle allows Org Admins to search across all workspaces.

**Search Scope:**

| Content Type | Searchable Fields |
|-------------|-------------------|
| Posts | Caption text, first comment, internal notes, tags, content category name, author name |
| Media | Filename, tags |
| Inbox Messages | Message body, sender name, sender handle, internal notes |
| Templates | Template name, caption text |

**Search Behavior:**
- Full-text search using PostgreSQL's built-in `tsvector`/`tsquery` (no external search engine needed at launch).
- Results are ranked by relevance (PostgreSQL `ts_rank`), with a secondary sort by recency.
- Minimum query length: 2 characters.
- Search is debounced: 300ms after the user stops typing.
- Pagination: first 5 results per type in the dropdown. "View all [N] results" link per type opens a full-page search results view with pagination (20 per page).

**Full-Page Search Results:**
- Accessible from the dropdown ("View all results") or by pressing Enter in the search bar.
- Filters: content type (checkboxes), date range, status (for posts), author.
- Sort: by relevance (default) or by date.

**Empty State:**
- No results: "No results for '[query]'. Try different keywords or check your filters."
- No query yet: "Search posts, media, inbox messages, and templates."

### Data Model
- No new tables. Search uses PostgreSQL full-text search indexes on existing tables:
  - `Post`: GIN index on `tsvector` of caption, first_comment, tags.
  - `MediaAsset`: GIN index on `tsvector` of filename, tags.
  - `InboxMessage`: GIN index on `tsvector` of body, sender_name, sender_handle.
  - `PostTemplate`: GIN index on `tsvector` of name, caption_text.

### Dependencies
- F-2.1 (Composer) - posts and templates.
- F-3.1 (Inbox) - inbox messages.
- F-6.1 (Media Library) - media assets.

### Acceptance Criteria
- Search returns results within 500ms for a workspace with 5,000 posts.
- Typing "product launch" surfaces all posts containing that phrase, ranked by relevance.
- Cross-workspace search (Org Admin) correctly returns results from multiple workspaces with workspace name labels.
- Keyboard shortcut Cmd/Ctrl+K focuses the search bar from any page within the workspace.

---

## F-8.2 - Post Detail View

### Purpose
Provide a dedicated read-only view for a published or completed post that aggregates all relevant information in one place: the post content, its platform-specific versions, publish log, analytics, approval history, and comments. The calendar and list views link to this detail view for published posts instead of reopening the composer.

### User Stories
- As a Manager, I can click a published post on the calendar and see its full details - content, analytics, publish history, and team comments - in one view.
- As a Client, I can view a published post's performance metrics alongside its content.
- As an Editor, I can review the approval history and version timeline of a post.

### Functional Requirements

**Navigation:**
- Clicking a published post from the calendar (F-2.3), list view, or search results opens the post detail view.
- Clicking a draft, pending, or scheduled post still opens the composer (F-2.1) for editing.
- The post detail view has an "Edit" button (visible only for posts that can be edited - drafts/scheduled). For published posts, "Edit" is hidden; instead, a "Duplicate as Draft" button allows creating a copy for revision.

**Layout:**
- Full-page view with a left content area and a right sidebar.

*Left Content Area:*
- **Post content:** The canonical caption text, media (images/videos displayed inline), first comment text, tags, content category.
- **Platform versions:** If platform-specific overrides exist, a tabbed interface shows each platform's version (e.g., "Instagram," "LinkedIn," "Facebook") with the platform-specific caption and media. A "Common" tab shows the shared base version.
- **Publish log:** A timeline showing each platform's publish status: platform icon, published timestamp (or failure reason), platform post URL (clickable link to the live post on the platform).

*Right Sidebar:*
- **Status badge:** Current post status (published, partially_published, failed, scheduled, etc.).
- **Metadata:** Author, created date, scheduled date, published date.
- **Analytics summary (for published posts):** Key metrics pulled from F-4.1 - impressions, reach, engagements, engagement rate. Per-platform breakdown. A "View full analytics" link navigates to the per-account analytics dashboard filtered to this post.
- **Approval history:** Timeline of approval actions (submitted, approved, changes requested, etc.) with who, when, and any comments.
- **Internal comments:** Thread of team comments (from F-2.2 PostComment). Ability to add new comments from the detail view.

**Empty State:**
- Analytics section for a recently published post (data not yet collected): "Analytics data will be available within 1 hour of publishing."
- Approval history for a post that skipped approval (workflow set to "None"): "This post was published without an approval workflow."

### Data Model
- No new tables. This view aggregates data from existing models: Post, PlatformPost, PublishLog, AnalyticsSnapshot, ApprovalAction, PostComment, PostVersion.

### Dependencies
- F-2.1 (Composer) - post data, platform versions.
- F-2.2 (Approval Workflow) - approval history.
- F-2.3 (Calendar) - navigation from calendar to detail view.
- F-2.4 (Publishing Engine) - publish logs.
- F-4.1 (Analytics) - per-post metrics.

### Acceptance Criteria
- Post detail view loads within 2 seconds for a post published to 5 platforms with 30 days of analytics data.
- Clicking a published post on the calendar opens the detail view (not the composer).
- Clicking a draft/scheduled post on the calendar opens the composer (not the detail view).
- "Duplicate as Draft" creates an exact copy with status "draft" and opens it in the composer.
- Platform post URLs in the publish log correctly link to the live post on each platform.

---

## F-8.3 - Post Trash & Soft Delete

### Purpose
Prevent accidental permanent deletion of posts by implementing a soft-delete mechanism with a recoverable trash. Deleted posts are moved to trash and can be restored within a retention period.

### User Stories
- As an Editor, if I accidentally delete a post, I can recover it from the trash.
- As a Manager, I can view all recently deleted posts and restore them.
- As an Org Admin, I can configure how long deleted posts are retained before permanent deletion.

### Functional Requirements

**Soft Delete:**
- When a user deletes a post (from the calendar, list view, or composer), the post is not permanently removed. Instead, it is moved to the trash (status set to `trashed`, `trashed_at` timestamp recorded).
- The post disappears from the calendar, list views, queues, and search results.
- A confirmation dialog before deletion: "This post will be moved to trash. You can restore it within [N] days." The dialog shows the post caption snippet and platforms.

**Trash View:**
- Accessible from the workspace sidebar: "Trash" link (with a count badge of trashed posts).
- Shows a list of trashed posts: caption snippet, platforms, original status (before deletion), deleted by, deleted date, days remaining before permanent deletion.
- Actions per post: "Restore" (returns post to its previous status), "Delete permanently" (requires Manager+ role, with a second confirmation dialog: "This cannot be undone").
- Bulk actions: "Restore selected," "Delete selected permanently."
- Sort: by deletion date (newest first, default).

**Retention:**
- Default retention period: 30 days (configurable via F-1.6 workspace settings - add `trash_retention_days`, min 7, max 90).
- A daily background job permanently deletes posts where `trashed_at + retention_days < now()`.
- Permanently deleted posts are removed from the database along with their associated PlatformPost records, PostVersions, PostMedia references (media assets themselves are NOT deleted - only the reference), ApprovalActions, and PostComments.

**Restore Behavior:**
- Restoring a post returns it to its pre-deletion status. If the post was "scheduled" and the scheduled time is now in the past, the status is changed to "draft" instead.
- Restoring a post places it back on the calendar at its original date/time (or as a draft if the time has passed).
- Restored posts retain all version history, approval history, and comments.

**RBAC:**
- Any user who can delete a post (Editor+ for own posts, Manager+ for others') can send it to trash.
- Viewing the trash: Editor+ (see own trashed posts), Manager+ (see all trashed posts in the workspace).
- Restore: same permissions as delete.
- Permanent deletion: Manager+ only.

### Data Model
- Extend `Post` table: add `trashed_at` (datetime, nullable), `trashed_by` (user_id, nullable), `pre_trash_status` (enum, nullable - stores the status the post had before it was trashed).
- Add status value `trashed` to the Post status enum.

### Dependencies
- F-2.1 (Composer) - delete action in composer.
- F-2.3 (Calendar) - delete action on calendar, trash view in sidebar.
- F-1.3 (RBAC) - permission checks for trash operations.
- F-1.6 (Configurable Defaults) - `trash_retention_days` setting.

### Acceptance Criteria
- Deleting a post moves it to trash and removes it from the calendar immediately.
- Restoring a trashed post returns it to the calendar with its original content and metadata intact.
- A post trashed 31 days ago (with default 30-day retention) is permanently deleted by the background job.
- The trash view correctly shows the remaining days before permanent deletion.
- A permanently deleted post cannot be recovered.

---

## F-8.4 - Data Export (GDPR Compliance)

### Purpose
Allow organization owners to export all data associated with their organization or a specific workspace in a structured, portable format. Supports GDPR data portability requirements and provides a path for users to migrate off the platform.

### User Stories
- As an Org Owner, I can export all my organization's data as a downloadable archive.
- As a Manager, I can export a single workspace's data for client handoff.
- As an Org Owner, I can request deletion of all my organization's data.

### Functional Requirements

**Export Scope:**
- Two export levels: organization-wide or single workspace.
- Organization export: includes all workspaces, members, settings, and shared library.
- Workspace export: includes only data scoped to that workspace.

**Export Contents:**

| Data Type | Format | Included In |
|-----------|--------|-------------|
| Posts (all statuses including trashed) | JSON + CSV | Workspace, Org |
| Post media files (images, videos) | Original files in `media/` directory | Workspace, Org |
| Platform post metadata (publish logs, platform post IDs) | JSON | Workspace, Org |
| Analytics snapshots | CSV (one file per account) | Workspace, Org |
| Inbox messages and replies | JSON | Workspace, Org |
| Internal notes | JSON | Workspace, Org |
| Saved replies | JSON | Workspace, Org |
| Report configurations | JSON | Workspace, Org |
| Generated report PDFs | PDF files in `reports/` directory | Workspace, Org |
| Media library (all assets + folder structure) | Original files in `media/` directory + `media_index.json` | Workspace, Org |
| Content categories and tags | JSON | Workspace, Org |
| Team members and roles | JSON (email, name, role - no passwords) | Workspace, Org |
| Approval history | JSON | Workspace, Org |
| Organization settings | JSON | Org only |
| White-label config | JSON + logo/favicon files | Org only |
| Audit log | CSV | Org only |

**Export Process:**
- Triggered from: Organization Settings → Data Management → "Export Data" (org-wide) or Workspace Settings → "Export Workspace Data."
- Only Org Owners can trigger org-wide exports. Managers+ can trigger workspace exports.
- After clicking "Export," the system shows: "Your export is being prepared. You will receive an email with a download link when it's ready. Large exports may take up to 1 hour."
- The export runs as a background job. Progress is not shown in real-time (fire-and-forget with email notification on completion).
- The export is packaged as a `.zip` file containing JSON, CSV, and media files organized in directories.
- The download link is emailed to the requesting user. The link expires after 7 days.
- The download link is also available in Organization Settings → Data Management → "Recent Exports" (list of past exports with download links and expiry dates).

**Export ZIP Structure:**
```
export-[org-slug]-[date]/
├── manifest.json          # Export metadata: date, scope, version
├── organization.json      # Org settings, members, roles
├── workspaces/
│   ├── [workspace-slug]/
│   │   ├── posts.json
│   │   ├── posts.csv
│   │   ├── analytics/
│   │   │   ├── [account-name].csv
│   │   ├── inbox_messages.json
│   │   ├── media/
│   │   │   ├── [original files]
│   │   │   └── media_index.json
│   │   ├── reports/
│   │   │   ├── [generated PDFs]
│   │   └── settings.json
├── shared_media/
│   ├── [shared library files]
│   └── media_index.json
├── whitelabel/
│   ├── config.json
│   ├── logo.png
│   └── favicon.ico
└── audit_log.csv
```

**Data Deletion:**
- Organization Settings → Data Management → "Delete All Data."
- Only Org Owners can trigger deletion.
- Deletion follows the same grace-period flow as organization deletion (F-1.1): 30-day grace period with email confirmation, countdown, and cancellation option.
- After the grace period, all data is permanently erased: database records, media files, generated reports, audit logs.
- Deletion is logged in a separate, immutable system log (not the org's own audit log, which is itself deleted).

### Data Model
- `DataExport`: id, organization_id, workspace_id (nullable - null for org-wide), requested_by (user_id), status (enum: pending, processing, completed, failed), file_url (string, nullable), file_size_bytes (integer, nullable), expires_at (datetime, nullable), error_message (nullable), created_at, completed_at (nullable).

### Dependencies
- F-1.1 (Organization) - org-wide export and deletion.
- F-1.2 (Workspace) - workspace-scoped export.
- F-7.1 (Notifications) - email with download link.

### Acceptance Criteria
- Exporting a workspace with 1,000 posts and 500 media assets completes within 30 minutes.
- The exported ZIP is well-structured and all JSON files are valid JSON.
- Media files in the export match the originals (byte-for-byte).
- The download link correctly expires after 7 days and returns a 410 Gone response.
- Data deletion after the grace period removes all records - a query for the org ID returns zero rows across all tables.

---

## F-8.5 - Timezone Handling

### Purpose
Define how dates and times are stored, displayed, and converted across the platform. Social media scheduling is inherently timezone-sensitive - an agency in New York scheduling a post for a client in Tokyo must be confident about when the post will publish.

### Functional Requirements

**Storage:**
- All timestamps in the database are stored in UTC. No exceptions.
- Timezone information is stored at three levels: organization (default timezone for new workspaces), workspace (the primary timezone for scheduling and display), user (the user's personal timezone for notifications and display).

**Display Rules:**

| Context | Timezone Used | Display Format |
|---------|--------------|----------------|
| Calendar (workspace) | Workspace timezone | "Mar 15, 2:30 PM EST" - always shows the timezone abbreviation |
| Post composer: schedule picker | Workspace timezone (default), with a dropdown to switch to user's timezone | Shows both workspace time and equivalent in user's timezone if they differ |
| Post detail view: publish timestamps | Workspace timezone | Same as calendar |
| Inbox: message received timestamps | Workspace timezone | Relative ("2 hours ago") with full timestamp on hover |
| Analytics: date range selectors | Workspace timezone | Date only (no time component) |
| Notifications (in-app) | User's timezone | Relative ("5 minutes ago") with full timestamp on hover |
| Notification emails | User's timezone | Full date + time with timezone abbreviation |
| Reports (PDF) | Workspace timezone | Explicit: "All times shown in Eastern Standard Time (UTC-5)" in report header |
| Audit log | UTC | ISO 8601 format with Z suffix |
| REST API (all endpoints) | UTC | ISO 8601 format with Z suffix |

**Timezone Selection:**
- Org default timezone: set in Organization Settings → General. Dropdown of all IANA timezones grouped by region. Default: detected from the Org Owner's browser during signup.
- Workspace timezone: set in Workspace Settings → General. Defaults to the organization's timezone. Can be overridden per workspace (e.g., for a client in a different timezone).
- User timezone: set in Account Settings → Preferences. Auto-detected from browser on first login. Can be manually overridden.

**Scheduling Clarity:**
- In the post composer's schedule picker, when the user's timezone differs from the workspace timezone, the picker shows dual times:
  - Primary: "Schedule for Mar 15, 2:30 PM EST" (workspace timezone).
  - Secondary: "(9:30 AM your time, PST)" (user's timezone).
- This ensures a New York-based user scheduling for a Tokyo client sees both times clearly.

**Daylight Saving Time (DST):**
- The platform uses IANA timezone database (via `pytz` or Python's `zoneinfo`) which handles DST transitions automatically.
- When a post is scheduled for a time that falls into a DST gap (e.g., 2:30 AM on a spring-forward day), the system shifts the post to the next valid time and notifies the user: "The scheduled time was adjusted due to a daylight saving time change."
- When a post is scheduled for a time in a DST overlap (fall-back), the system uses the first occurrence (pre-fall-back time).

### Data Model
- No new tables. Timezone fields already exist on Organization (`default_timezone`), Workspace (`timezone`), and User (`timezone`).
- All existing `datetime` columns use `DateTimeField` (stores UTC). Display conversion happens at the view/template layer, never at the database layer.

### Dependencies
- F-1.1 (Organization) - org timezone setting.
- F-1.2 (Workspace) - workspace timezone setting.
- F-2.1 (Composer) - dual-timezone display in scheduler.
- F-2.3 (Calendar) - timezone-aware date display.
- F-2.4 (Publishing Engine) - publishes at correct UTC time.

### Acceptance Criteria
- A user in PST scheduling a post for 9:00 AM EST (workspace timezone) sees "9:00 AM EST (6:00 AM your time, PST)" in the composer.
- The post publishes at exactly 14:00 UTC (9:00 AM EST).
- Calendar view shows all posts in workspace timezone, regardless of the viewing user's personal timezone.
- A post scheduled for 2:30 AM on a spring-forward DST day is automatically shifted to 3:00 AM and the user is notified.
- REST API always returns UTC timestamps in ISO 8601 format.

---

## F-8.6 - Link Shortening & UTM Tracking

### Purpose
Agencies need to track link performance to prove ROI to clients. This feature provides UTM parameter management (for campaign attribution in Google Analytics) and optional link shortening for cleaner social posts.

### User Stories
- As a Manager, I can set default UTM parameters for a workspace so every post automatically includes tracking.
- As an Editor, I can customize UTM parameters per post.
- As a Manager, I can generate shortened links for my posts.

### Functional Requirements

**UTM Parameter Management:**

*Workspace-Level Defaults (configured in Workspace Settings → Link Tracking):*
- Default UTM parameters applied to all links in posts for this workspace:

| Parameter | Default Template | Editable Per Post |
|-----------|-----------------|-------------------|
| `utm_source` | `{platform}` (auto-replaced: instagram, facebook, linkedin, etc.) | Yes |
| `utm_medium` | `social` | Yes |
| `utm_campaign` | `{workspace_slug}` | Yes |
| `utm_content` | `{post_id}` | Yes |
| `utm_term` | (empty) | Yes |

- Template variables: `{platform}`, `{workspace_slug}`, `{post_id}`, `{category}`, `{date}` (YYYY-MM-DD of scheduled publish).
- Toggle: "Auto-append UTM parameters to all links in posts" (default: off). When enabled, any URL in a post caption has UTM parameters appended automatically at publish time.

*Per-Post Override:*
- In the post composer (F-2.1), a "Link Tracking" panel (collapsible) shows the UTM parameters that will be applied.
- The user can edit any parameter for this specific post.
- Preview: a read-only field shows the full URL with UTM parameters as it will appear after publishing.

**Link Shortening:**

*Built-in shortener:*
- Not included at launch. Link shortening is external-only (see below). A built-in shortener may be added in a future release.

*External shortener integration:*
- Workspace Settings → Link Tracking → "Link Shortener" section.
- Supported services: Bitly, Short.io. Each requires an API key configured at the workspace level.
- When a shortener is configured and enabled, links in posts are shortened at publish time (after UTM parameters are appended).
- The original long URL (with UTMs) is stored on the Post record. The shortened URL replaces it in the published caption.
- If the shortening API fails, the post publishes with the full (unshortened) URL and a warning is logged.

**Link Tracking in Analytics:**
- UTM-tagged links are tracked by the client's own Google Analytics (or equivalent). The platform does not provide its own click tracking - it relies on the UTM parameters being picked up by the destination's analytics.
- In the post detail view (F-8.2), the "Links" section shows: original URL, UTM parameters applied, shortened URL (if applicable).

### Data Model
- `WorkspaceLinkSettings`: id, workspace_id, auto_append_utm (boolean), default_utm_source (string), default_utm_medium (string), default_utm_campaign (string), default_utm_content (string), default_utm_term (string), shortener_provider (enum: none, bitly, short_io, nullable), shortener_api_key (encrypted, nullable), created_at, updated_at.
- Extend `Post`: add `link_utm_overrides` (json, nullable - per-post UTM overrides).
- Extend `PlatformPost`: add `shortened_urls` (json, nullable - mapping of original URL → shortened URL for this platform's published version).

### Dependencies
- F-2.1 (Composer) - UTM panel in composer.
- F-2.4 (Publishing Engine) - appends UTMs and shortens at publish time.
- F-1.6 (Configurable Defaults) - workspace-level UTM defaults.
- F-8.2 (Post Detail View) - link tracking display.

### Acceptance Criteria
- A post with auto-UTM enabled and a link `https://example.com/sale` publishes with `https://example.com/sale?utm_source=instagram&utm_medium=social&utm_campaign=client-a&utm_content=123`.
- Per-post UTM overrides correctly replace the workspace defaults.
- A configured Bitly integration shortens the UTM-tagged URL and the shortened link appears in the published post.
- If Bitly API fails, the post still publishes with the full URL and an error is logged.
- Template variables (`{platform}`, `{post_id}`, etc.) are resolved correctly at publish time.

---

## F-8.7 - Content Category Management

### Purpose
Content categories are referenced throughout the platform - in the composer, calendar, queues, analytics, and reports - but need a dedicated management interface for creating, editing, and organizing them.

### User Stories
- As a Manager, I can create content categories for my workspace (e.g., "Educational," "Promotional," "Behind the Scenes").
- As a Manager, I can assign colors to categories for visual distinction on the calendar.
- As an Editor, I can assign a category to any post.
- As a Manager, I can see analytics broken down by category.

### Functional Requirements

**Category CRUD (Workspace Settings → Content Categories):**
- **Create:** Name (required, unique per workspace, max 50 characters), color (hex picker from a palette of 12 predefined colors, or custom hex input), description (optional, max 200 characters).
- **Edit:** Update name, color, or description. Changes are reflected everywhere the category is referenced (calendar, analytics, reports) without needing to re-tag posts.
- **Reorder:** Drag-and-drop to set the display order. Order determines the sort in dropdowns and the calendar legend.
- **Delete:** A category can only be deleted if no posts are currently assigned to it. If posts reference the category, the user must first reassign those posts to a different category or to "Uncategorized." A count of affected posts is shown: "This category is used by [N] posts. Reassign them before deleting."
- **Default categories:** New workspaces are created with no categories. A "Starter set" button provides a one-click option to create a common set: "Educational," "Promotional," "Behind the Scenes," "User Generated Content," "Seasonal/Holiday." The user can skip this and create their own from scratch.

**Category Assignment:**
- In the post composer (F-2.1), a "Category" dropdown shows all workspace categories, sorted by display order.
- A post can have exactly one category (or none - "Uncategorized" is the implicit default when no category is selected).
- Categories are also assignable from the calendar (right-click a post → "Set Category" → dropdown).

**Category Colors on Calendar:**
- When a category is assigned to a post, the post card on the calendar shows a colored left border or dot matching the category color.
- A legend (toggleable) at the top of the calendar shows all categories with their colors.

**Category Analytics:**
- F-4.1 analytics dashboard includes a "Performance by Category" section: a table or bar chart showing total posts, average engagement rate, total reach, and total impressions per category for the selected date range.
- F-4.3 report builder includes a "Content Category Performance" section type.

### Data Model
- `ContentCategory`: id, workspace_id, name, color (hex string), description (nullable), display_order (integer), created_by (user_id), created_at, updated_at.
- Post.category_id already exists as an FK to ContentCategory.

### Dependencies
- F-2.1 (Composer) - category dropdown.
- F-2.3 (Calendar) - category color display, legend, right-click assignment.
- F-4.1 (Analytics) - per-category breakdown.
- F-4.3 (Reports) - category performance report section.

### Acceptance Criteria
- Creating a category with a name and color immediately makes it available in the composer and calendar.
- Renaming a category updates all existing references (calendar, analytics) without requiring post re-tagging.
- Attempting to delete a category with assigned posts shows the count and blocks deletion.
- Calendar correctly displays category colors as left-border accents on post cards.
- Analytics "Performance by Category" chart correctly aggregates metrics per category.

---
---

# 9. DATA MODEL (COMPLETE)

```
Organization
  ├── has_many: OrgMemberships → Users
  ├── has_many: Workspaces
  ├── has_one: WhiteLabelConfig
  ├── has_many: PlatformCredentials
  ├── has_many: IntegrationConfigs
  ├── has_many: APIKeys
  ├── has_many: CustomRoles
  ├── has_many: AIProviderConfigs
  ├── has_one: AIDefaultProvider
  ├── has_many: OrgSettings (F-1.6)
  ├── has_many: OrgAlerts
  └── has_many: DataExports (F-8.4)

Workspace
  ├── belongs_to: Organization
  ├── has_many: WorkspaceMemberships → Users
  ├── has_many: SocialAccounts
  ├── has_many: Posts
  ├── has_many: MediaAssets
  ├── has_many: MediaFolders
  ├── has_many: InboxMessages
  ├── has_many: SavedReplies
  ├── has_many: Reports
  ├── has_many: ContentCategories
  ├── has_many: PostTemplates
  ├── has_many: Queues
  ├── has_many: CustomCalendarEvents
  ├── has_many: WebhookEndpoints
  ├── has_many: SlackWorkspaceConfigs
  ├── has_many: WorkspaceSettings (F-1.6)
  ├── has_many: ConnectionLinks (F-1.7)
  ├── has_one: InboxSLAConfig
  ├── has_one: WorkspaceLinkSettings (F-8.6)
  └── has_many: ContentCategories (F-8.7)

Post
  ├── belongs_to: Workspace
  ├── belongs_to: Author (User)
  ├── has_many: PlatformPosts
  ├── has_many: PostVersions
  ├── has_many: PostMedia → MediaAssets
  ├── has_many: ApprovalActions
  ├── has_many: PostComments
  ├── belongs_to: ContentCategory (optional)
  ├── has_one: RecurrenceRule (optional)
  ├── trashed_at, trashed_by, pre_trash_status (F-8.3)
  ├── link_utm_overrides (json, F-8.6)
  └── status: draft | pending_review | changes_requested | pending_client | rejected | approved | scheduled | publishing | published | partially_published | failed | trashed

PlatformPost
  ├── belongs_to: Post
  ├── belongs_to: SocialAccount
  ├── has_many: AnalyticsSnapshots
  ├── has_many: PublishLogs
  ├── shortened_urls (json, F-8.6)
  └── publish_status: pending | published | failed

SocialAccount
  ├── belongs_to: Workspace
  ├── has_many: PostingSlots
  ├── has_many: InboxMessages
  ├── has_many: AccountMetricsSnapshots
  ├── has_many: AudienceDemographics
  └── has_one: RateLimitState

InboxMessage
  ├── belongs_to: Workspace
  ├── belongs_to: SocialAccount
  ├── has_many: InboxReplies
  ├── has_many: InternalNotes
  └── assigned_to: User (optional)
```

---
---

# 10. BUILD PHASES

### Phase 1: Foundation & Core Publishing (Weeks 1–6)
- F-1.1 Organization Management
- F-1.2 Workspace Management (basic - no archiving or cross-workspace views yet)
- F-1.3 Members & RBAC (org + workspace roles, invitations)
- F-1.5 Platform API Credentials
- F-1.6 Configurable Defaults & Platform Settings (org + workspace settings infrastructure)
- F-2.5 Social Account Connection (start with: Instagram, Facebook, LinkedIn)
- F-2.1 Post Composer (basic - full-page composer, multi-platform, media upload, character counts)
- F-2.3 Content Calendar (month/week/day views, basic scheduling, drag-and-drop, empty states)
- F-2.4 Publishing Engine (core publishing, retry logic, rate limits)
- F-5.1 Authentication (email/password, Google OAuth)
- F-6.1 Media Library (upload, folders, tags, search, empty states)
- F-8.3 Post Trash & Soft Delete (soft delete with 30-day retention)
- F-8.5 Timezone Handling (UTC storage, workspace/user timezone display)
- F-8.7 Content Category Management (CRUD, calendar colors)

### Phase 2: Collaboration & Approval (Weeks 7–10)
- F-2.2 Approval Workflow (all four modes, comments, version history)
- F-1.4 Client Portal (magic links, approval UI, published post view)
- F-1.7 Client Onboarding Flow (connection links, get-started checklist)
- F-2.1 Post Composer enhancements (templates, content categories, internal notes, UTM panel)
- F-2.3 Calendar enhancements (filtering, bulk CSV import, queues, recurring posts)
- F-7.1 Notification System (in-app + email)
- F-8.1 Global Search (workspace-scoped search across posts, media, inbox, templates)
- F-8.2 Post Detail View (read-only view for published posts)

### Phase 3: Engagement (Weeks 11–14)
- F-3.1 Unified Social Inbox (message sync, reply, assignment, saved replies, sentiment, empty states)
- F-5.3 Integrations - Slack (notifications)
- F-5.3 Integrations - Stock Media (Unsplash, Pexels, GIPHY in composer)

### Phase 4: Analytics & Reporting (Weeks 15–18)
- F-4.1 Per-Account Analytics (data collection, dashboard, charts, empty states)
- F-4.2 Cross-Account & Cross-Workspace Analytics (org dashboard, team metrics)
- F-4.3 Report Builder (templates, editor, WeasyPrint PDF export, scheduled reports, shareable links)
- F-2.3 Calendar enhancement - optimal time suggestions (requires analytics data)
- F-8.6 Link Shortening & UTM Tracking (workspace UTM defaults, per-post overrides, Bitly/Short.io)

### Phase 5: Branding & Growth (Weeks 19–24)
- F-5.2 White-Label Configuration (branding, custom domain, email branding)
- F-5.3 Integrations - AI (BYO API key, caption generation, sentiment enhancement)
- F-5.3 Integrations - Canva, Google Drive, Dropbox
- F-5.3 Integrations - REST API & Webhooks
- F-5.1 Authentication enhancements (2FA)
- F-2.5 Additional platforms (TikTok, YouTube, Pinterest, Threads, Bluesky, GBP, Mastodon)
- F-1.2 Workspace enhancements (archiving, cross-workspace calendar)
- F-4.2 Org alerts
- F-8.4 Data Export / GDPR (org-wide and workspace-scoped export, data deletion)

### Phase 6: Post-Launch
- Advanced analytics (competitor benchmarking, industry benchmarks)
- Content recycling / evergreen queues
- Built-in link shortener (replace external-only with self-hosted option)

---
---

# 11. TECHNICAL REQUIREMENTS

### Platform Integration Architecture

All social platform integrations use direct first-party APIs. Each platform has a dedicated provider module.

```
Provider Interface (abstract):
  - authenticate(credentials) → OAuth tokens / session
  - refreshToken(tokens) → new tokens
  - publishPost(account, content, media) → PlatformPostResult
  - publishComment(platformPostId, text) → CommentResult
  - getPostMetrics(platformPostId) → Metrics
  - getAccountMetrics(account, dateRange) → AccountMetrics
  - getAudienceDemographics(account) → Demographics
  - getInboxMessages(account, since) → Message[]
  - replyToMessage(messageId, text) → Reply
  - getAccountProfile(tokens) → Profile

Implementations:
  - FacebookProvider (Graph API)
  - InstagramProvider (Instagram Graph API via Facebook)
  - LinkedInProvider (Marketing API v2)
  - TikTokProvider (Content Posting API)
  - YouTubeProvider (Data API v3)
  - PinterestProvider (API v5)
  - ThreadsProvider (Threads API)
  - BlueskyProvider (AT Protocol)
  - GoogleBusinessProvider (GBP API)
  - MastodonProvider (Mastodon API)
```

No unified or third-party social media API providers are used. Each provider manages its own OAuth flow, token refresh, rate limiting, and error handling.

### Background Jobs
- **Post publisher:** runs every 15 seconds, picks up scheduled posts, dispatches to providers.
- **Analytics collector:** hourly for recent posts, daily for older posts and account metrics, weekly for demographics.
- **Inbox syncer:** every 5 minutes per account (polling). Webhook receivers for supported platforms.
- **Token refresher:** hourly check for expiring tokens.
- **Report generator:** triggered on schedule or manual request.
- **Media processor:** processes media for posts scheduled within the next hour.
- **Recurrence generator:** daily, creates post instances for recurring rules up to 90 days ahead.
- **Cleanup:** daily, removes expired magic links, old publish logs (90 days), old webhook delivery logs (30 days).
- **Trash purge:** daily, permanently deletes posts where `trashed_at + retention_days < now()` (F-8.3).
- **Data export generator:** on-demand (triggered by user request), processes workspace or org export and emails download link on completion (F-8.4).
- **Account health checker:** every 6 hours per connected account.

### Security
- OAuth tokens: AES-256-GCM encrypted at rest. Encryption key from environment variable, never stored in DB.
- Workspace isolation: all database queries include workspace_id in WHERE clause. Enforced at the ORM/query layer, not just the application layer.
- API rate limiting: configurable (default: 1,000 req/hour per API key).
- Login rate limiting: 5 failed attempts per email per 15 minutes → temporary lockout (15 minutes).
- CSRF protection on all state-changing endpoints.
- Audit log: all destructive actions (delete workspace, remove member, disconnect account, delete post) logged with: user_id, action, target entity, timestamp, IP address. Audit logs retained for 1 year.
- GDPR compliance: data export (full workspace data as JSON/CSV zip) and data deletion (workspace or org level) available via settings. Self-hosters own all data.
- Content Security Policy headers on all pages.
- Dependency scanning: automated vulnerability scanning in CI pipeline.
