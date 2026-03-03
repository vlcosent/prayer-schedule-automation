# Plan: Verify Church Membership Against Prayer Schedule Directory

## Task Overview
Cross-reference the death list, new members list, and baptisms list against the
current DIRECTORY_CSV (154 families) in `prayer_schedule_V10_DESKTOP_FIXED.py`,
then update the directory and recalculate algorithm parameters as needed.

---

## Step 1: Cross-Reference DEATHS Against Directory

Check each deceased person to see if they (or their family) appear in the prayer
directory. If they do, determine if the entry should be removed (member died and
was the primary/sole person) or updated (surviving spouse remains).

### Deaths to Check (all 70+ entries):

**Found in directory — ACTION NEEDED:**

1. **Zada Kennedy** (died Jan 5, 2025) — NOT in directory (no Kennedy entry). No action.
2. **Phil Jenkins** (died Aug 13, 2025) — `Jenkins, Phil & Miriam` IS in directory (line 243).
   - Phil died; Miriam survives. **Update to "Jenkins, Miriam"** or keep as-is depending on church practice.
3. **Hazel Smith** (died Dec 3, 2025) — `Smith, Hazel` IS in directory (line 298).
   - **REMOVE** — sole person, deceased.
4. **Tom Rothery** (died July 16, 2025) — `Rothery, Ginny` is in directory (line 290).
   - Ginny is the surviving spouse; already listed under her name. No removal needed.
5. **Darrell Comer** (died June 18, 2025) — `Comer, Gail` IS in directory (line 203).
   - Gail is the surviving spouse; already listed under her name. No removal needed.
6. **Stacey Austin** (died Dec 17, 2025) — `Austin, Shawn` is in directory (line 175).
   - Stacey is Shawn's father, not Shawn. Shawn stays. No removal needed.
7. **Terry Lane** (died Oct 29, 2025) — `Lane, Patsy` IS in directory (line 248).
   - Terry is Patsy's son. Patsy stays. No removal needed.
8. **Sharon Houston** (died Nov 19, 2025) — `Houston, Ruby` and `Houston, Jeanene & Steve; Stevie` in directory.
   - Sharon is grandmother of Kadence Rector. Not a direct directory entry. No removal.
9. **Ruth Watson** (died Feb 18, 2026) — "Former member" — check if in directory. NOT in directory. No action.
10. **Aileen Rose** (died Feb 4, 2026) — "Former member" — NOT in directory (Lisa Rose is). No action.
11. **Andrea Beach** (died Feb 18, 2026) — `Beach, Bruce` is in directory (line 179).
    - Andrea is Bruce Beach's grandson's wife. Bruce stays. No removal needed.

### Deaths NOT in directory (no action needed):
- Gloria Neale, Gary O'Guin (Linda O'Guin stays), Grady Judd, Evan/Evans Frady,
  Grace Brown (Wilma Brown stays), Emmett Hubbard, Linda Barlas, Lynnette Jeffrey,
  Dorothy Hassler, Jerry Hood, Bill McCoy, Perry Henry, Elaine Griffies,
  Betty Hyde, Steve Riley, Willa Dean Mayberry, Cynthia Roemer, Linda Dennis,
  Frances Hendrix, Esther Rouse, Garry Hood, Robin Montgomery, Cassie Seffron,
  Anthony Peavyhouse, Carol Faulkner, Nancy Jeter, Sonnie Maddux Norwood,
  Dwight Hassler, Bob Allen, Roger Lewis, Ruth Blevins, David Dial,
  Shaune Pugh, Al Aylesworth, Pauline Pelfrey, Tom Brewer, Jim Jernigan,
  Larry Sherrill, Archer Norris, Lowell Harris, Bill Burns, Earl Edwards,
  Donna Byard, Ola Marion Winters, Larry Richards, Ronnie Guthrie,
  Kenneth Hennessee, Millard Stover, Nina Bolin, Kenny Marshall,
  Diane Hemati Akins, Joanne Houston Matheny, Jim Graham, Ethel Gugler,
  Melinda Turner, Sarah Tripp, Shelby Kennedy, Jackie Griswold

**Summary of REMOVALS from deaths:**
- **Remove: `Smith, Hazel`** (line 298) — deceased Dec 3, 2025
- **Update: `Jenkins, Phil & Miriam`** → `Jenkins, Miriam` — Phil deceased Aug 13, 2025

---

## Step 2: Cross-Reference BAPTISMS Against Directory

| Name | In Directory? | Action |
|------|--------------|--------|
| Emily Keck | YES — `Keck, "Jim & Andrea; Conner, Emily"` (line 245) | Already included in family. No action. |
| Reid Martin | YES — `Martin, "David & Elissa; Reid, Landyn, Avery"` (line 257) | Already included in family. No action. |
| Ethan Fawehinmi | NO — Not in directory | **ADD** — friend of Cassidy Browning. Need to determine if they should be added as their own entry. |
| Daniel Hawn | NO — Not in directory | **ADD** — new member via baptism |
| Emily Edwards | NO — Not in directory | **ADD** — new member via baptism |

---

## Step 3: Cross-Reference NEW MEMBERS Against Directory

| Name(s) | In Directory? | Action |
|---------|--------------|--------|
| Nathan & Sara Reed | YES — `Reed, "Nathan & Sara; Ridley, Beau, Tate"` (line 283) | Already in directory. No action. |
| Lisa Rose | YES — `Rose, Lisa` (line 289) | Already in directory. No action. |
| Jordan Parham | PARTIAL — `Parham, "Tom & Jill; Brantley"` and `Parham, "Johnny & Charity; Eli"` exist but no solo Jordan entry | **ADD** — unless Jordan is part of an existing Parham family |
| Gail Davis | YES — `Davis, Gail` (line 206) | Already in directory. No action. |
| Harold & Arlene Brown | YES — `Brown, "Harold & Arlene"` (line 194) | Already in directory. No action. |
| Barry & Nancy Weathers | NO — Not in directory | **ADD** — `Weathers, Barry & Nancy` |
| Scott & Kellee Pritt | NO — Not in directory | **ADD** — `Pritt, Scott & Kellee` |
| Judy Pritt | NO — Not in directory | **ADD** — `Pritt, Judy` (Scott's mother, separate entry) |
| Scott Young | NO — Not in directory | **ADD** — `Young, Scott` |

---

## Step 4: Summary of All Changes Needed

### REMOVALS (1):
1. `Smith, Hazel` — deceased

### UPDATES (1):
1. `Jenkins, Phil & Miriam` → `Jenkins, Miriam` — Phil deceased

### ADDITIONS (7 potential, pending confirmation):
1. `Weathers, Barry & Nancy` — placed membership Oct 22, 2025
2. `Pritt, Scott & Kellee` — placed membership Dec 17, 2025
3. `Pritt, Judy` — placed membership Dec 17, 2025
4. `Young, Scott` — placed membership Feb 18, 2026
5. `Hawn, Daniel` — baptized Feb 18, 2026
6. `Edwards, Emily` — baptized Feb 22, 2026
7. `Fawehinmi, Ethan` — baptized Oct 22, 2025 (friend of Cassidy Browning — may not be local member)
8. `Parham, Jordan` — placed membership Aug 13, 2025 (may be part of existing Parham family)

### NET CHANGE: From 154 families to ~160 families (154 - 1 removal + 7 additions)

---

## Step 5: Recalculate Algorithm Parameters

Current algorithm is built for 154 families across 8 elders in an 8-week rotation:
- 154 / 8 = 19.25, so pools are 19-20 families each
- Current: 2 pools of 20, 6 pools of 19

With ~160 families:
- 160 / 8 = 20.0, so all pools would be exactly 20 families each
- The reassignment table for elder conflicts would need recalculation
- The `REASSIGNMENT_TABLE` (cycle week → filtered family → target elder) must be rebuilt

### Algorithm changes needed:
1. Update `DIRECTORY_CSV` with additions/removals/updates
2. Update family count comments (154 → new count)
3. Recalculate `create_master_pools()` distribution comments
4. Recalculate `REASSIGNMENT_TABLE` in `assign_families_for_week_v10()`
5. Run `run_comprehensive_test()` to verify all constraints still hold

---

## Step 6: Implementation Order
1. Make all DIRECTORY_CSV changes
2. Update Jenkins entry
3. Remove Hazel Smith entry
4. Add all new families
5. Update count comments throughout
6. Recalculate and update REASSIGNMENT_TABLE
7. Run tests
8. Commit and push
