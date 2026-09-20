---
name: git-workflow
description: Git branching and commit guidelines for the nitros9 repository. Enforces saving work exclusively on branches prefixed with `work` and forbids committing directly to `main`.
---

# Git Workflow & Branching Guidelines

## Core Directives

1. **Permitted Work Branches**:
   - You may save your work in any git branch whose name begins with `work` (e.g., `work-tfr9-0`, `work-feature-name`, `work/patch-1`).
   - Always verify the current branch with `git branch --show-current` before staging or committing changes.

2. **Main Branch Protection**:
   - **Do NOT commit or save anything directly to `main`.**
   - Do not push, merge, or rebase unreviewed work into `main`.

3. **Inspecting Main**:
   - You **may examine** `main` whenever needed for reference, comparison, or history inspection (e.g., `git diff main`, `git log main`, `git show main:<path>`, or checking out `main` in read-only mode).
   - If `main` is checked out to inspect code, immediately switch back to a `work*` branch before making or saving any modifications.
