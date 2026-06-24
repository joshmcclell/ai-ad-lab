# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Current State

This repository (`ai-ad-lab`) is a greenfield project. As of this writing it contains only `README.md` (a single title line) — there is no source code, build tooling, tests, dependency manifests, or CI configuration yet.

There is therefore nothing to document about build, lint, test, or run commands, and no architecture to describe. Do not invent these; they do not exist yet.

When you add the first real code, update this file in the same change with the concrete details a future instance needs:
- **Commands**: how to install dependencies, build, run, lint, and run the test suite — including how to run a single test.
- **Architecture**: the big-picture structure that requires reading multiple files to understand (entry points, module boundaries, how data/control flows between major pieces).
- **Conventions**: any non-obvious patterns, project-specific idioms, or constraints that aren't discoverable from the code alone.

## Git Workflow

- The default branch is `main`.
- Active development for AI-assisted work happens on dedicated feature branches (e.g. `claude/<topic>`); do not commit directly to `main`.
- Push with `git push -u origin <branch-name>`.
- Do not open a pull request unless explicitly asked.
