# Git Setup Instructions

## If you haven't initialized Git yet:

```bash
# Initialize repository
git init

# Add .gitignore
git add .gitignore

# Add all files (respecting .gitignore)
git add .

# Make initial commit
git commit -m "Initial commit: Dockerized Docr Canvas application"
```

## If files are already tracked and you want to remove them from Git (but keep locally):

```bash
# Remove tracked files that should be ignored
git rm --cached backend/wow.env
git rm --cached backend/*.db
git rm --cached -r backend/venv/
git rm --cached -r backend/__pycache__/
git rm --cached -r docr-canvas-frontend/node_modules/
git rm --cached -r docr-canvas-frontend/.next/

# Commit the removal
git commit -m "Remove ignored files from tracking"
```

## Verify what will be committed:

```bash
# See what files are staged
git status

# See what would be ignored
git status --ignored
```

## Important Notes:

- `.gitignore` only prevents **untracked** files from being added
- Files already committed will continue to be tracked until you remove them with `git rm --cached`
- The `--cached` flag removes from Git but keeps the file on your disk
- Never commit API keys, passwords, or `.env` files!

