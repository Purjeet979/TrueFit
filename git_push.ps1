Set-Location -LiteralPath "d:\Downloads\India_runs_data_and_ai_challenge"

# Initialize git if not already
git init

# Configure user
git config user.email "commercialsude36@gmail.com"
git config user.name "Purjeet"

# Force branch name to main
git branch -M main

# Get all files that are untracked and not ignored by .gitignore
$untrackedFiles = git ls-files --others --exclude-standard

foreach ($file in $untrackedFiles) {
    if ($file -match "git_push.ps1") { continue }
    
    # Extract file name for commit message
    $filename = Split-Path $file -Leaf
    
    git add $file
    git commit -m "Add $filename"
}

# Check if origin already exists, if so update it, else add it
$remotes = git remote
if ($remotes -contains "origin") {
    git remote set-url origin https://github.com/Purjeet979/TrueFit.git
} else {
    git remote add origin https://github.com/Purjeet979/TrueFit.git
}

# Force push to github to overwrite the previous wrong push
git push -u origin main --force
