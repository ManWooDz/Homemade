# Homemade — AI Recipe Generator (Capstone Project)

ระบบสร้างสูตรอาหารไทยจากวัตถุดิบในตู้เย็นที่ grounded และตรวจสอบได้ (React+Vite frontend, FastAPI backend, กำลังย้าย SQLite → PostgreSQL). ทีม 2 คน, capstone 1 ปีการศึกษา.

รายละเอียดเต็ม: [docs/project-proposal.md](docs/project-proposal.md)
สถานะปัจจุบัน / งานค้าง: [spec.md](spec.md)
บทเรียนที่ห้ามพลาดซ้ำ: [MEMORY.md](MEMORY.md)

@MEMORY.md

## Hard Rules (non-negotiable — no exceptions without the user saying so explicitly)

- **Never modify anything in `/backend/` without explicit confirmation.** Backend changes require a separate review step — propose the diff/plan first, wait for a yes, then edit.
- **Don't install new packages without asking first** — npm (frontend) or pip (backend). List what you'd install and why, then wait.
- **Never use force commands** — e.g. `git worktree remove --force`, `git push --force`, `git reset --hard`, `rm -rf`. Ask first, always, even if it looks safe.
- **Don't delete files.** Mark them as deprecated with a comment instead, and flag them for manual removal by the user.

## Operating Rules

### NO MAGIC — don't guess

All assumptions explicit. If context is missing, state assumptions.
Don't hallucinate hidden infra or invent unspecified services.
If you don't know where something lives, ask — don't guess the path.
ก่อนเสนอเทคนิค/ไลบรารีใหม่ ให้เช็คโค้ดจริงก่อนว่ามันตรงกับ stack ที่มีอยู่ (เช่น อย่าเสนอ Node-only library ให้ FastAPI backend).

### VERIFY BEFORE DONE — no "done" without evidence

Never claim a change is complete without running verification.
"I edited the file" is not done. "I edited the file and here's the output" is done.
No "should work now." Evidence before assertions, always.

### DISSENT — argue before you commit

Before any major change, surface concerns:

- What's the blast radius if this goes wrong?
- What assumptions are we making?
- What's the reversibility path?
- What are we NOT seeing because of momentum?

### SCOPE DRIFT — flag scope creep

Track stated goals vs actual execution. Flag when:

- "Just one more thing" accumulates
- Nice-to-haves get treated as must-haves
- The ask was "fix bug X" but we're now "refactoring the entire module"
  สำหรับโปรเจกต์นี้: contribution ที่ต้องวัดผลทางวิชาการ (nutrition engine, allergen validation, critic-feedback loop) ต้องแคบและลึกเสมอ — feature ใหม่ที่ไม่ใช่ 3 ตัวนี้ให้จัดเป็น "product envelope" (ดู spec.md) ไม่ใช่ contribution ที่ต้องมี KPI

### R0 / R1 / R2 — classify by reversibility

- R0 (irreversible) — STOP. Ask before proceeding.
- R1 (costly to reverse) — Do it, but tell me what and why.
- R2 (easily reversed) — Just do it. No permission needed.

### LEARNING CAPTURE — log failures, don't repeat them

When you identify a pattern failure or operational mistake:

1. Log it to MEMORY.md
2. Include three fields: what happened / root cause / correct behavior
3. Make the correct-behavior a command you can follow, not a feeling

### SPEC-DRIVEN — the spec is the source of truth, not the chat

At session start: read spec.md before doing anything.
After completing any task:

1. Update spec.md — current state, decisions made, what's next.
2. Update data contracts if any interface changed.
3. Never claim "done" without updating spec.md first.
