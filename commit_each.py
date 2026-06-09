import subprocess

def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, shell=True)

# Add everything to get full file paths
run("git add .")
status = run("git diff --cached --name-only")
files = [f.strip() for f in status.stdout.split('\n') if f.strip()]

# Unstage everything
run("git reset")

print(f"Committing {len(files)} files individually...")

# Commit each file individually
for f in files:
    # If the file was deleted, `git add` handles it correctly, but to be safe we can use git add --all
    run(f'git add --all "{f}"')
    res = run(f'git commit -m "Update {f}"')
    if res.returncode == 0:
        print(f"Committed {f}")
    else:
        print(f"Failed to commit {f}: {res.stderr}")

# Push to remote
print("Pushing to remote...")
push_res = run("git push")
print(push_res.stdout)
print(push_res.stderr)
print("Done.")
