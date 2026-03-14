# TRIBUTARY — Manual Testing Guide

End-to-end walkthrough for testing the full user journey across all 4 phases.

---

## Prerequisites

### Start the Backend

```bash
cd tributary_api
./venv/Scripts/python.exe manage.py runserver 8000
```

### Start the Frontend

```bash
cd tributary_web
npm run dev
```

Open **http://localhost:3000** in your browser.

### Seed District Data (if needed)

If no districts exist in the database:

```bash
cd tributary_api
./venv/Scripts/python.exe manage.py ingest_nces --file <path-to-nces-csv>
```

---

## Part 1 — Registration & Onboarding

### 1.1 Register a New Account

1. Go to `/register`
2. Fill in: first name, last name, email, password (8+ characters)
3. Submit — you will see a "Check Your Email" confirmation
4. In dev mode, email is auto-verified — proceed directly to `/login`

### 1.2 Log In

1. Go to `/login`
2. Enter the email and password you registered with
3. First-time login redirects you to the onboarding flow

### 1.3 FERPA Consent

1. You land on `/onboarding/consent`
2. Read the consent text and click Accept
3. Redirects to district selection

### 1.4 Select Your District

1. You land on `/onboarding/district`
2. Search for a district by name (e.g., "Spring", "Alpha")
3. Select your district from the results
4. Continue to problem selection

### 1.5 Choose Problem Statements

1. You land on `/onboarding/problems`
2. Select 1–3 problem statements that match your interests
3. Submit — redirects to `/dashboard`

---

## Part 2 — Dashboard & Profile

### 2.1 Dashboard

1. You should see the **profile completion checklist** with 4 items:
   - Add a bio (+40%)
   - Select your district (+30%) — already complete from onboarding
   - Choose a problem statement (+20%) — already complete from onboarding
   - Choose a second problem statement (+10%) — optional
2. The progress bar should reflect your current completion percentage
3. Verify the percentage updates as you complete items

### 2.2 Edit Your Profile

1. Click your avatar initials (top right corner) → **Profile**
2. Add a bio (up to 500 characters)
3. Save changes
4. Return to the dashboard — verify the completion percentage updated (bio adds 40%)

---

## Part 3 — Community & Channels

> **Note:** For community and matching features, you need at least **two registered users**. Register a second user in an incognito window or different browser.

### 3.1 Community Directory

1. Click **Community** in the navigation bar
2. You should see other active members listed as cards
3. Test the **search** box — search by name or district name
4. Test the **state filter** dropdown
5. Test the **locale type filter** dropdown
6. Test the **sort** options: Match Score, Name, Joined
7. Verify pagination works (24 members per page)
8. Click **Connect** on a member card — status should change to "Pending"

### 3.2 Channels

1. Click **Channels** in the navigation bar
2. You should see active problem statements listed with category badges and member counts
3. Click a channel to view members who selected that problem
4. Verify members are sorted by match score
5. Try connecting with a member from within a channel
6. Click **Back to Channels** to return to the channel list

---

## Part 4 — Matching & Connections

### 4.1 Compute Match Scores

Match scores are computed nightly by Celery, but for testing you can trigger them manually:

```bash
cd tributary_api
./venv/Scripts/python.exe -c "
import os; os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tributary_api.settings.dev')
import django; django.setup()
from apps.matching.tasks import compute_all_match_scores
compute_all_match_scores()
print('Match scores computed.')
"
```

### 4.2 Match Feed

1. Click **Matches** in the navigation bar
2. You should see matched users sorted by score (highest first)
3. Each card shows: name, district, bio excerpt, problem selections, match score percentage
4. Click **Connect** to send a connection request

### 4.3 Connection Flow (Two Users Required)

1. **User A**: Go to Matches or Community → click **Connect** on User B
2. **User B**: Go to Matches → see the pending connection request → click **Accept** (or Decline)
3. Once accepted, both users can start a conversation
4. Verify that declining or blocking hides the user from future match results

### 4.4 Block a User

1. From an accepted connection, click **Block**
2. Verify the blocked user no longer appears in your match feed or community directory

---

## Part 5 — Messaging

### 5.1 Start a Conversation

1. After accepting a connection, click **Inbox** in the navigation bar
2. Start a new conversation with the connected user (or one may already exist)
3. Send a message

### 5.2 Message Back and Forth

1. **User A**: Send a message in the conversation
2. **User B**: Open Inbox → see the conversation → read the message → reply
3. Verify messages appear in chronological order
4. Verify the message count and preview update in the conversation list

### 5.3 Notifications

1. After receiving a connection request or message, check the notification indicator
2. Go to notifications and verify they list recent activity
3. Test **Mark All Read** — all notifications should clear

### 5.4 Mark Conversation as Read

1. Open a conversation with unread messages
2. Verify the unread count resets after viewing

---

## Part 6 — Match Feedback

After having a conversation with a connected user, you can submit feedback.

### 6.1 Submit Feedback

Submit via API (or through the UI if prompted):

```
POST http://localhost:8000/api/feedback/
Authorization: Bearer <your_access_token>
Content-Type: application/json

{
  "connection_id": "<connection-uuid>",
  "rating": 4,
  "feedback_text": "Great conversation about reading fluency!"
}
```

### 6.2 Verify Duplicate Prevention

Submit the same feedback again — you should receive a **409 Conflict** with error code `DUPLICATE`.

### 6.3 View Your Feedback

```
GET http://localhost:8000/api/feedback/my/
Authorization: Bearer <your_access_token>
```

Should return a list of all feedback you've submitted.

---

## Part 7 — Staff Features

### 7.1 Promote a User to Staff

```bash
cd tributary_api
./venv/Scripts/python.exe manage.py shell -c "
from apps.users.models import User
u = User.objects.get(email='your@email.com')
u.role = 'UPSTREAM_STAFF'
u.save()
print(f'{u.email} promoted to UPSTREAM_STAFF')
"
```

Log out and log back in for the role change to take effect.

### 7.2 Staff Dashboard

1. Go to `/staff`
2. You should see the staff moderation panel
3. Test the following actions:

| Action | What to Test |
|--------|-------------|
| **Join Conversation** | Pick any conversation between members → join it → verify a system message appears |
| **Send DM** | Send a direct message to any member → verify it creates a staff-initiated conversation |
| **Broadcast** | Send a message to multiple members → verify each gets their own conversation |
| **Suspend Member** | Suspend a member account → verify they can no longer log in |

### 7.3 Taxonomy Manager

1. Go to `/staff/taxonomy`
2. **Add a Statement**: Click "Add Statement" → fill in title, description, category → submit
3. **Edit a Statement**: Click "Edit" on an existing statement → change the title → save → verify version number incremented
4. **Retire a Statement**: Click "Retire" → confirm → verify it shows a "Retired" badge with italic styling
5. **Verify Permission**: Log in as a regular member and try accessing `/staff/taxonomy` — should redirect to dashboard

### 7.4 Analytics Dashboard

1. Go to `/staff/analytics`
2. Verify **4 summary cards** display:
   - Total Members
   - Messages Sent
   - Match Acceptance Rate
   - Avg Feedback Rating
3. Verify **4 charts** render:
   - Member Growth (line chart)
   - Message Volume (bar chart)
   - Problem Distribution (doughnut chart)
   - Top District Pairs (table)
4. Change the **date range** using the date pickers → verify data refreshes
5. Click **Export CSV** → verify a `.csv` file downloads with analytics data
6. **Verify Permission**: Log in as a regular member and try accessing `/staff/analytics` — should redirect to dashboard

### 7.5 Featured Members

1. From the staff panel, feature a community member (provide user ID and optional note)
2. Go to `/community` as a regular member → verify the **Featured** badge appears on the featured user's card
3. Feature up to 5 members — verify the 6th is rejected with "Maximum 5 active featured members allowed"
4. Remove a featured member → verify the badge disappears from the community directory

---

## Part 8 — Accessibility Checks

### 8.1 Keyboard Navigation

1. Press **Tab** from the top of any page — verify the **"Skip to main content"** link appears
2. Press **Enter** on the skip link — focus should jump to the main content area
3. Tab through the navigation bar — verify all links and buttons receive visible focus rings
4. Open the user menu (avatar) with Enter/Space → navigate with Tab → close with Escape

### 8.2 Mobile Navigation

1. Resize your browser to mobile width (< 768px)
2. Click the hamburger menu icon — verify the mobile drawer opens
3. Verify all navigation links are accessible
4. Press **Escape** — verify the drawer closes
5. Click the backdrop overlay — verify the drawer closes

### 8.3 Screen Reader Basics

1. Verify all form inputs have visible labels or `aria-label` attributes
2. Verify modals have `role="dialog"` and `aria-modal="true"`
3. Verify the navigation has `aria-label="Main navigation"`
4. Verify dropdown menus have `aria-expanded` and `role="menu"` attributes

---

## Quick Smoke Test Checklist

For a fast end-to-end verification, follow this condensed flow:

- [ ] Register **User A** (Browser 1)
- [ ] Register **User B** (Browser 2 / Incognito)
- [ ] Both users complete onboarding: consent → district → problem statements
- [ ] Both users add a bio from their profile page
- [ ] Run `compute_all_match_scores()` in the backend shell
- [ ] **User A**: Go to Matches → Connect with User B
- [ ] **User B**: Go to Matches → Accept the connection
- [ ] **User A**: Go to Inbox → Start conversation → Send a message
- [ ] **User B**: Go to Inbox → See message → Reply
- [ ] **User A**: Submit match feedback (rating 1–5)
- [ ] Promote **User A** to staff role
- [ ] **User A**: Visit `/staff/analytics` → verify charts render
- [ ] **User A**: Visit `/staff/taxonomy` → add a new problem statement
- [ ] **User A**: Feature **User B** from staff panel
- [ ] **User B**: Visit `/community` → verify Featured badge shows

If all items pass, the platform is fully functional.
