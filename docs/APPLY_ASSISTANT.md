# Apply with Claude (semi-automatic applications)

Every job in the digest email and in the Excel file has two Claude links next to **Apply**:

- **Tailor CV** opens claude.ai with a cv-tailoring request for the job typed in. You get a tailored one-page CV PDF.
- **Apply with Claude** does the same and then fills in the employer's application form for you in Chrome. It
  stops before **Submit**. You check every field and press Submit yourself.

Clicking a link never sends anything: claude.ai opens with the message typed in, and you press send.
Nothing is submitted to an employer unless you press their Submit button.

## One-time setup

1. **cv-tailoring skill**: already set up on your account.
2. **apply-assistant skill**: save the proposed skill card in the Claude project thread, then open
   claude.ai → Settings → Capabilities → Skills → apply-assistant and replace every `<FILL IN>` with your
   answers (right to work, notice period, salary, etc.). `apply_profile.example.yaml` in this repo lists the
   same fields. **This repo is public, so keep your real answers in the skill, not in the repo.**
3. **Claude in Chrome**: install the Claude in Chrome extension, sign in with the same Claude account, and
   allow it in claude.ai so chats can use your browser.
4. Sign in once to the job sites you use most (LinkedIn, Workday tenants, Greenhouse, etc.) in that Chrome
   profile. Claude never types passwords. When a site asks you to sign in or create an account, it stops and
   waits for you.

## What happens when you click "Apply with Claude"

1. claude.ai opens with the job details typed in. Press send.
2. Claude reads the job ad and writes the tailored CV PDF (cv-tailoring rules: honest, one page, Times New Roman).
   **Download the PDF.**
3. Claude opens the apply page in a new Chrome tab and fills the form from your apply profile and CV:
   contact details, links, education, right to work, notice period, salary and the like.
4. For custom questions ("Why this firm?", "Describe a project...") it drafts short, honest answers based on
   your Master Profile and shows them to you in the chat before typing them in.
5. When it reaches the CV upload field, it stops and asks you to attach the downloaded PDF. Browser tools
   can't choose a file from your computer's file dialog.
6. It stops before Submit and lists what it filled, what it left empty and anything it was unsure of. You
   review the form, fix anything, and press Submit yourself.

## Limits

- **No passwords, CAPTCHAs or account creation.** Claude stops and you do these yourself.
- **Equal-opportunities and declaration questions** are only answered as your profile says (`ask_me` by default).
- **No guessing.** A `<FILL IN>` left in the profile means that field stays empty and Claude asks you.
- **Multi-page forms** (Workday, Oracle) take a few minutes. Claude goes page by page and never clicks the
  final Submit or "Send application".
- **Older jobs** carried over from earlier runs have no stored description, so their links only carry the job
  details and ad link. Claude reads the ad from the link.
