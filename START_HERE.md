# Run your project

1. Extract `AgentHarnessLab.zip`.
2. Open the `agent-harness-lab` folder in VS Code or a terminal.
3. Install Python 3.11 or newer if needed, and check `python --version`.
4. Run:

```bash
python -m unittest discover -s tests -v
python -m agentharness demo --trusted-local --output results/my-run
```

On Windows, replace `python` with `py` if that is your installed launcher.

5. Open `results/my-run/dashboard.html` in your browser.

You can view the included `results/demo/dashboard.html` immediately without installing anything. It contains recorded fixture results, not real-model benchmark results.

Read `README.md` for actual model configuration, Docker, Harbor/Codex/Claude Code, and project structure. API keys are needed only for a provider that requires them. There is no paid dependency for the offline demo.

To upload this repository to a new, empty GitHub repository:

```bash
git init
git add .
git commit -m "Build AgentHarnessLab and AgentScope"
git branch -M main
git remote add origin YOUR_NEW_GITHUB_REPOSITORY_URL
git push -u origin main
```

Replace `YOUR_NEW_GITHUB_REPOSITORY_URL` with your actual empty repository URL. Review generated files before committing. Never add API keys or `.env` files. The repository's ignore rules exclude candidate run directories from Git while retaining compact reports and trace evidence.
