# User guide

Short guides for each kind of user. The app and dashboard are in English and
Kiswahili; switch language on the Welcome screen or Account tab (app) or at
the bottom of the menu (dashboard).

## Community reporter (mobile app)

1. **Register** with your name, phone number and a password, and accept the
   privacy notice.
2. **Report pollution:** Home → *Report pollution*. Take a photo **from a safe
   distance** (never go near fires, smoke, chemicals or needles), confirm the
   location, choose the type, and add a short description if it helps.
3. **No connection?** The report is saved on your phone and sent automatically
   when you are back online. *My reports* shows "Waiting to send".
4. **Follow up:** *My reports* shows each report's status: waiting for review,
   verified, rejected (with the reason) or under second review. The *Inbox*
   tab and phone alerts tell you when something changes.
5. **Rewards:** Account → *Rewards by mobile money*. Switch on "Send my
   rewards by M-Pesa" and, if you like, enter a different M-Pesa number. You
   receive a small reward for each **verified** report. You can switch this off
   at any time; your reports still count. During testing, rewards are marked
   **Test** and no real money is sent.

## Verifier (mobile app)

1. Sign in with the account your administrator created. The **Review** tab
   lists reports waiting for review in your zone plus reports outside every
   zone. Use the zone chips to see others.
2. Open a report: look at the photo, the map position, the type, the time and
   the description. *Nearby reports* lists reports close in place and time, to
   help you spot duplicates.
3. Decide:
   - **Confirm** if the photo clearly shows the pollution described, at that place.
   - **Reject** with a reason (e.g. not pollution, unclear photo, photo shows a person).
   - **Flag** with a reason when you are unsure or it may be a duplicate.
     Another verifier makes the final decision.
4. Decisions need a connection; the app tells you if one was not saved. You
   never see your own reports for review.

## Agency staff (web dashboard)

- **Overview:** verified reports at a glance, by type and zone, and any
  **health signals** (amber) needing attention.
- **Pollution map:** verified reports as coloured markers or as a density map;
  filter by date, zone and type. Click a marker to open the report.
- **Health trends:** weekly verified reports against clinic visits for a
  chosen condition; possible illness clusters; every linkage result with its
  rate change and p-value. Read [health-linkage-method.md](health-linkage-method.md):
  a signal is a reason to look closer, **not proof that pollution caused
  illness**. Small clinic counts are hidden to protect privacy.
- **Reports:** search verified reports and open their photo and linkage results.

## Administrator (web dashboard)

Everything agency staff can do, plus:

- **Clinic data:** download the CSV template, upload aggregated visit counts
  from the partner clinic. A file with any problem (including any column that
  looks like patient data) is refused whole, with a list of what to fix.
  Accepted files recalculate the health linkages straight away.
- **Payouts:** see every reward, its provider and status. *Send due payouts
  now* processes waiting payouts immediately. *Retry* a failed payout only
  after reading the reason; if it says to check the M-Pesa portal, do that
  first so nobody is paid twice.
- **Users:** add verifiers (with a zone), agency staff (with an agency) and
  administrators; change roles; reset a password; deactivate an account (signs
  the person out everywhere). You cannot remove your own administrator role or
  deactivate yourself.
- **Audit log:** every decision, import, payout and change, with who and when.
  It cannot be edited.
- **Settings:** health-linkage method (radius, windows, thresholds, which
  conditions are checked for each pollution type), reward amount and currency,
  the small-count privacy threshold, and verifier zones. Changing a linkage
  setting recalculates all results.
