# BidWicket — Complete Feature Testing Guide

## Prerequisites: Start Both Servers

Open **two separate terminal windows**:

**Terminal 1 — Start the backend:**
```powershell
cd d:\Projects\BidWicket\backend
.\venv\Scripts\activate
uvicorn app.main:app --reload --port 8000
```
Wait until you see: `Uvicorn running on http://127.0.0.1:8000`

**Terminal 2 — Start the frontend:**
```powershell
cd d:\Projects\BidWicket\frontend
npm run dev
```
Then open your browser at **http://localhost:5173** (or 5174 if 5173 is busy).

> [!IMPORTANT]  
> The `ENVIRONMENT=development` setting in `backend/.env` means **email verification is auto-skipped**. Registration instantly activates your account, so you can log in immediately.

---

## Phase 1 — Create Test User Accounts

You'll need **4 accounts** to test every role. Register each one at `http://localhost:5173/register`.

| Account | Name | Email | Password | Role (dropdown) |
|---|---|---|---|---|
| Admin | Admin User | admin@test.com | Test@1234 | Viewer (we'll promote via API) |
| Organizer | Organizer User | organizer@test.com | Test@1234 | Organizer |
| Team Owner | Team Owner | owner@test.com | Test@1234 | Team Owner |
| Viewer | Viewer User | viewer@test.com | Test@1234 | Viewer |

> [!TIP]
> **Promoting the Admin account:** After registering `admin@test.com`, promote it using Swagger UI:
> 1. Go to `http://localhost:8000/api/v1/docs`
> 2. First, use `POST /auth/login` with the admin credentials to get an `access_token`
> 3. Click **Authorize** at the top of Swagger and paste the token
> 4. Use `PATCH /users/{admin_user_id}/roles` with body: `{"roles": ["admin","organizer","team_owner","viewer"]}`

---

## Phase 2 — Test as ORGANIZER

**Login as:** `organizer@test.com`

### 2.1 Create a Tournament
1. Click **Tournaments** in the sidebar
2. Click **+ New Tournament**
3. Fill in:
   - Name: `IPL Test 2025`
   - Type: `T20`
   - Format: `League`
   - Max Teams: `8`
   - Prize Pool: `50000`
   - Start/End date
4. Click **Create** → ✅ Should appear in the tournament list

### 2.2 View Tournament Detail
1. Click **View** on the tournament you just created
2. ✅ Should open the Tournament Detail page (`/tournaments/:id`)
3. See enrolled teams, match schedule slots, and tournament stats

### 2.3 Create a Match
1. Click **Matches** in the sidebar
2. Click **+ Schedule Match**
3. Select the tournament you created, pick two teams (after teams are created in Phase 3)
4. ✅ Match should appear in the matches list

### 2.4 Update Match Score (Live Scoring)
1. From the Matches list, click **View** on a match
2. ✅ Opens the Live Match page (`/matches/:id`)
3. Use the scoring controls on the Live Match page to add runs/wickets
4. ✅ Score updates in real-time via WebSocket

---

## Phase 3 — Test as TEAM OWNER

**Login as:** `owner@test.com`

### 3.1 Create a Team
1. Click **Teams** in the sidebar
2. Click **+ New Team**
3. Fill in:
   - Name: `Mumbai Roasters`
   - Budget: `1000000` (₹10L)
   - Home Ground: `Wankhede`
   - Home City: `Mumbai`
4. Click **Create** → ✅ Team appears in list

### 3.2 View Team Profile
1. Click **View** on your team
2. ✅ Opens Team Profile page (`/teams/:id`)
3. See Pie chart for Win/Loss ratio, wallet budget, roster

### 3.3 Create Players
1. Click **Players** in sidebar
2. Click **+ Add Player**
3. Add at least 3 players with different roles:
   - `Sachin Test` — Batsman — Base Price: ₹50,000
   - `Bumrah Test` — Bowler — Base Price: ₹80,000
   - `Jadeja Test` — All-Rounder — Base Price: ₹70,000
4. ✅ Players appear in Players list

### 3.4 View Player Profile
1. Click **View** on a player
2. ✅ Opens Player Profile page (`/players/:id`)
3. See player statistics, bar charts for batting/bowling

---

## Phase 4 — Test AUCTION FLOW

**Login as:** `organizer@test.com`

### 4.1 Create an Auction
1. Click **Auctions** in sidebar
2. Click **+ New Auction**
3. Fill in:
   - Name: `IPL Mega Auction 2025`
   - Tournament: select `IPL Test 2025`
   - Bid Timer: `30` seconds
4. Click **Create** → ✅ Appears in auctions list

### 4.2 Add Players to Auction
1. Click into the auction you created (Auction Room)
2. Find the "Add Items" section
3. Add the 3 players you created in Phase 3 as auction items

### 4.3 Start Live Bidding
1. Click **Start Auction** → status changes to `live`
2. **Open a second browser window** and login as `owner@test.com`
3. Both windows navigate to the Auction Room URL
4. As organizer, click on first player item → starts the timer
5. As owner, click **Place Bid** and enter a higher amount
6. ✅ Bid updates in real-time via WebSocket for both users
7. Let timer run out → ✅ Player assigned to highest bidder

### 4.4 Finalize Auction
1. After all items are sold, click **Finalize Auction**
2. ✅ Players are assigned to teams
3. ✅ Email notification sent to auction winners (if SMTP configured)

---

## Phase 5 — Test as ADMIN

**Login as:** `admin@test.com` (after promotion)

### 5.1 Admin Dashboard Overview
1. Click **Admin** in sidebar (only visible to admin role)
2. ✅ See live stats: Total Users, Teams, Players, Tournaments, Matches, Auctions, Bids

### 5.2 Role Management
1. Scroll down on the Admin page to see **User Role Management** table
2. Find `viewer@test.com` 
3. Click **Make Admin** → ✅ Roles update instantly
4. Click **Revoke Admin** to revert → ✅ Works both ways

### 5.3 CSV Exports
1. Click each export button to download:
   - **Users CSV** → downloads all users
   - **Bids CSV** → downloads all bids
   - **Tournaments CSV** → downloads tournament list
   - **Players CSV** → downloads all players
   - **Matches CSV** → downloads match schedule
2. ✅ Each should download a valid `.csv` file

---

## Phase 6 — Test COMMON FEATURES (all roles)

### 6.1 My Profile
1. Click **My Profile** in top navbar
2. Update Full Name → click **Save Changes** → ✅ Updates instantly
3. Enter a photo URL → ✅ Avatar preview updates
4. ✅ Roles badge and email displayed correctly

### 6.2 Search
1. Click **Search** in sidebar
2. Type a player name / team name / tournament name
3. ✅ Live search results appear

### 6.3 Notifications
1. Click **Notifications** in sidebar
2. ✅ List of notifications (bids, auction results, etc.)
3. Click **Mark all as read** → ✅ Unread count clears

### 6.4 Light / Dark Mode
1. Click the **Sun/Moon** icon in top navbar
2. ✅ UI switches between dark and light themes
3. Refresh the page → ✅ Theme persists (saved in localStorage)

---

## Phase 7 — Live Match WebSocket Test

### 7.1 Real-time Commentary
1. Open the Live Match page for a match with `live` status
2. Open the same URL in a second browser tab
3. In one tab, add ball commentary (if you have organizer role)
4. ✅ Commentary appears in the other tab in real-time

### 7.2 Wicket Alerts
1. Record a wicket on the scoring interface
2. ✅ A live toast notification "🚨 Wicket!" appears for all viewers

---

## Quick Checklist Summary

| Feature | Role Needed | Expected Result |
|---|---|---|
| Register | Public | Account created instantly |
| Login | Public | JWT token issued |
| Create Tournament | Organizer | Tournament appears in list |
| Tournament Detail | All | Stats, teams, matches page |
| Create Team | Team Owner | Team in list with budget |
| Team Profile (charts) | All | Pie chart, roster visible |
| Add Player | Team Owner | Player in players list |
| Player Profile (stats) | All | Stats, bar charts visible |
| Create Auction | Organizer | Auction in list |
| Live Bidding (WS) | All | Real-time bid updates |
| Finalize Auction | Organizer | Players assigned to teams |
| Admin Dashboard | Admin | Real-time platform stats |
| Role Management | Admin | Promote/Revoke users |
| CSV Exports | Admin | 5 CSV files download |
| My Profile Update | All | Name/photo save works |
| Live Match (WS) | All | Real-time score + commentary |
| Dark/Light Mode | All | Theme persists on refresh |
| Notifications | All | Unread count + mark read |
| Search | All | Cross-entity results |
