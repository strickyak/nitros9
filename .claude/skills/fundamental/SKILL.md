---
name: fundamental
description: Fundamental workspace boundary rule for nitros9. Enforces Rule Number One: never modify files outside this nitros9 directory, and stop to report external bugs or needed changes to the user for coordination.
---

# Fundamental Workspace Rule

## Rule Number One: nitros9 Workspace Boundary

> **Do not change any files outside of this `nitros9` folder.**
> If you find bugs or have other changes you want to make in other directories, stop and tell me about it, so I can coordinate the changes with other projects.

---

### Core Directives

1. **Strict Directory Scope**:
   - All file creations, modifications, refactorings, deletions, and build artifact generations must strictly reside within the `nitros9` repository root (`/home/strick/modoc/coco-shelf/nitros9`) and its subdirectories.
   - Do **NOT** edit, create, or touch any files in parent directories or sibling directories under `/home/strick/modoc/coco-shelf/` (e.g., `toolshed`, `tfr9`, `turbos`, `lwtools`, `cmoc`, `gccretro`, `fujinet-*`, `copico-*`, `spectranet`, `whippets`, etc.).

2. **External Bugs & Changes Protocol**:
   - If a bug, missing feature, broken header, or build failure points to code in an external repository or sibling directory:
     1. **STOP immediately**: Do not make changes or apply quick fixes in the external directory.
     2. **Report to user**: Explain clearly:
        - The exact file and path outside `nitros9`.
        - The bug or change discovered.
        - The rationale and proposed solution.
        - How it affects the current task in `nitros9`.
     3. **Wait for coordination**: Allow the user to coordinate and apply changes across repositories.
