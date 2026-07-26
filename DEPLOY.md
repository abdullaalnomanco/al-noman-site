# Getting this live, with a working login

Everything in this folder is ready to go. Five steps left, all on your end
(I can't create accounts or push code on your behalf) — about 15 minutes total.

## 1. Create a GitHub repo
- Go to github.com → New repository → name it anything (e.g. `al-noman-site`) → Create.
- Don't add a README/gitignore — keep it empty.

## 2. Push these files to it
From a terminal, inside this folder:
```
git init
git add .
git commit -m "Initial site"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/al-noman-site.git
git push -u origin main
```

## 3. Connect the repo to Netlify
- app.netlify.com → Add new site → Import an existing project → GitHub → pick the repo.
- Build settings: leave everything blank (no build command, publish directory = `/`). Deploy.
- You'll get a live URL like `random-name-123.netlify.app` (you can rename it in Site settings → Domain management).

## 4. Turn on Identity + Git Gateway (this is what makes /admin work)
- In your new Netlify site: Site settings → Identity → **Enable Identity**.
- Still in Identity settings → Registration → set to **Invite only** (so strangers can't sign up).
- Site settings → Identity → Services → Git Gateway → **Enable Git Gateway**.
- Identity tab (top of dashboard) → **Invite users** → invite your own email.

## 5. Log in and edit
- Check your email for the Netlify Identity invite, set a password.
- Visit `yoursite.netlify.app/admin` → log in → edit the hero text, mission line,
  and contact links → **Publish**.
- That commits straight to GitHub, and Netlify redeploys automatically (~30 seconds).

---

## What's editable right now vs. what isn't

The admin panel currently edits: the hero pull-quote, the mission line, and your
contact links (email / LinkedIn / Scholar / GitHub). Those are the fields wired
up to `content.json`.

The Research, Practice, Skills, Journey map, and Extracurricular sections are
still hand-authored HTML — editing those means asking me to update the code
directly, or I can wire more of them into the CMS the same way (each one is a
similar amount of work to what's already done). Tell me which section you want
editable next and I'll extend `content.json` + `admin/config.yml` to cover it.

## Why not a "real" custom database + full login system instead?

That's a bigger, different kind of project — your own server, a database,
real user accounts — and it's overkill for a personal portfolio. This
Git-based CMS setup (Decap CMS + Netlify Identity) gives you actual
password-protected login and real persistence, without needing to run or pay
for a backend server. If you later want a true multi-user system (e.g. other
people submitting content), that's the point where a custom backend would
make sense — happy to scope that separately if it comes up.
