# The quarterly checks

This is the procedure for the two quarterly checks that
[plainlyai.org/changes](https://plainlyai.org/changes) promises, under "Checks that are due":
the concept pages and the guides, and the resource lists on Start here. Both are due on the
11th of February, May, August and November. They were promised from August 2026, with the
first due on 11 November 2026, and until 23 September 2026 nothing had written down how to
run them.

They run as the Claude scheduled task `plainly-quarterly-check`, in the desktop app on
Shawn's PC, at 14:00 on those days. That is four hours after the monthly check
([MONTHLY-CHECK.md](MONTHLY-CHECK.md)), which falls on the same day. The two must never run
at once, because both edit the log on `public/changes.html` in the same working tree. So the
quarterly check waits for the monthly one and builds on its branch, and the two then merge
as one change. If the monthly check hasn't finished, the quarterly check does not start. It
says so instead, and it can be started again by hand once the monthly check is done.

Everything under "The rule that matters" and "What not to do" in MONTHLY-CHECK.md applies
here unchanged. Never guess a figure, never deploy, and every log entry says whether it is
live. The same goes for the regenerate-and-check step at the end.

## 1. The concept pages and the guides

**This is not a walk through a list of pages.** It is a re-reading of the documents on
[Sources](https://plainlyai.org/sources), followed by seeing which pages have to move as a
result. Every document a concept page or guide depends on is on that list, because a page
here is not published citing something the list does not carry. The 26 August 2026 log
entry explains why that matters.

1. **Re-read every document on Sources that any page other than Model facts depends on.**
   That is the "Pages that depend on it" column. Include the Anthropic models overview:
   the monthly check reads it for figures, but four concept pages cite its word and
   character approximations. Open each one today and read it in full, not a HEAD request.
   A document that moved, now redirects, is paywalled, or has gone is itself a finding.
2. **For each page that depends on it, check each claim it cites to that document.** A
   quote must still be there, word for word. A paraphrase must still be a fair reading. A
   page can go wrong with its citation intact, because the thing described changed, so ask
   of each page whether the explanation still describes how these systems work.
3. **Fix what is small, and flag what is not.** A correction to a sentence, a moved link,
   or a dated caveat that no longer holds: fix it and log it, as a correction if it was
   wrong. A page that needs rethinking is not a quarterly-check edit. Say so in the report
   and in STATUS.md, and leave its verified date alone.
4. **Move a page's `Last verified` only when every source it depends on was re-read today
   and every claim it cites was checked.** That means the stamp and the JSON-LD
   `dateModified` both, which check 10 holds together. A page with one unreadable source
   keeps its old date, and the log says which source and why.
5. **Update `Last read` on Sources for every document you actually opened.** Only those.

Rule 2 still holds. Model names and prices live on Model facts, and check 11 enforces it.

## 2. The resource lists on Start here

Courses get retired, reorganised, and quietly moved behind a payment page. **Every link
gets opened, not just pinged.** For each resource, check:

- it still loads, and still goes where the page says it goes;
- it is still free, or still labelled accurately if it isn't;
- it hasn't been retired, merged into something else, or turned into a sign-up wall;
- the page's description of it is still true.

A resource that fails comes out, and the log says why. Put a replacement in only if it was
opened and checked today, meets the same bar, and fits the track. An empty slot is better
than an unchecked one. Move Start here's `Last verified` only if every link was opened.

## 3. Then

- **One log entry per check**, dated today, at the top of the log, each ending with
  `<strong>Committed, not yet published.</strong>`. If the check ran late, the entry says
  "Due 11 <Month>, run on the <N>th".
- **Move both quarterly lines in "Checks that are due"** to the 11th, three months on.
- **Regenerate and check:** `python feed.py && python modelfacts.py && python check.py`.
  check.py must be clean.
- **Deliverable:** commit on the branch, update STATUS.md (Blocked on Shawn: say go on the
  deploy), and report. The report covers every document re-read with a verdict, every
  Start here link with a verdict, what was fixed, what was flagged, and anything you were
  unsure about.
