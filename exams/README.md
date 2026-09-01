# Exams — how the semester works

> **Scope.** This document describes the **exercise (cvičenia)** part of the course only —
> the two exams you work on during the semester, how they are graded, and how to get help.
> The **lectures and the final test** are run by the course lecturer and are graded separately;
> nothing on this page changes those rules.

## Overview

During the semester you work on **two exams**. Both are practical, both are done on the
simulation stack in this repository (Gazebo Sim + ArduPilot SITL + MAVROS), and both are
worth **20 points**.

| | What | Points | Deadline | Where |
|---|---|---|---|---|
| **Exam 1** | Fixed for everyone — autonomous mission, indoor + outdoor | 20 | **end of week 6** | [`exam1/`](exam1/) |
| **Exam 2** | You pick **one** of the offered topics | 10 | **end of week 12** (last exercise) | [`exam2/`](exam2/) |
| **Test** | Short written test on the **lecture** material | 10 | second half of the semester | see below |
| | **Total** | **40** | | |

Exam 1 is split into **four sub-exams** (E1.1 – E1.4) that can be submitted and defended
independently — see [`exam1/README.md`](exam1/README.md). Exam 2 is a single, smaller
assignment; you choose which one.

The **test** covers the lecture material, not the exercises. It is written once in the second
half of the semester; the exact date is announced in advance. Nothing in this document changes
how it is run — ask the lecturer about its content.

## Timeline

| Week | What happens |
|---|---|
| 1 | Environment setup: `gz sim`, ArduPilot SITL, MAVROS, ROS 2 workspace. Exam 1 is assigned. |
| 2 | Work on **E1.1** — map processing and path planning. |
| 3 | Work on **E1.2** — mission control node, indoor flight in simulation. |
| 4 | Work on **E1.3** — outdoor GPS/compass mission. **Earliest possible real-drone flight** (see below). |
| 5 | Integration, consultations, **E1.4** documentation. |
| 6 | **Exam 1 deadline.** Defence during the exercise. Exam 2 topics presented. |
| 7 | Exam 2 topic selection — tell your exercise teacher which one you picked. |
| 8 – 11 | Work on Exam 2, consultations. **Short test on the lecture material** in this period — date announced in advance. |
| 12 | **Exam 2 deadline.** Defence during the last exercise. |

## Grading

### Points

Each sub-exam / section has its points listed in its own file. You get points for what
**demonstrably works** — a feature that is written but not shown running during the defence
does not score.

### Threshold for the final test

To be allowed to sit the final exam you need **at least 56 % from *each* of the two exams
separately**:

- **≥ 11.2 / 20 points from Exam 1**, and
- **≥ 5.6 / 10 points from Exam 2**.

A good total is not enough — 20/20 from Exam 1 and 4/10 from Exam 2 does **not** qualify.
Both thresholds must be met independently. The lecture test is not covered by this rule.

### Late submission

Every **started** week after the deadline costs **10 % of the points you earned** on that exam.

| Submitted | Multiplier | Example: 16 points earned on Exam 1 |
|---|---|---|
| On time | × 1.00 | 16.0 |
| 1 week late | × 0.90 | 14.4 |
| 2 weeks late | × 0.80 | 12.8 |
| 3 weeks late | × 0.70 | 11.2 |
| 4 weeks late | × 0.60 | 9.6 |

The penalty is applied **before** the 56 % threshold is checked, so a late submission can drop
you below the threshold even if the raw score was fine. Plan for that.

## Flying the real drone

From **week 4** to **week 12** you may start flying on the **real UAV** outdoors. This is not automatic — it
is unlocked per student/team once **all** of the following are true:

1. Your **Exam 1 is fully submitted** (all four sub-exams, code in the repository, documentation written).
2. You passed a **consultation** with your exercise teacher, where you walk through your code
   and show the mission flying in simulation.
3. You completed the **safety briefing** and your mission passes the pre-flight checklist in
   [`exam1/03_outdoor_gps_mission.md`](exam1/03_outdoor_gps_mission.md).

Real-drone flights always happen **with a teacher present** and with a **safety pilot holding
an RC transmitter** who can take over at any moment. Never power a real vehicle without a
teacher present.

Flying the real drone brings no extra points — it is what you unlock by finishing early.
Everything is graded from the simulation, so nobody is penalised for not getting there.

## Submission

Unless a specific assignment says otherwise:

1. Work in **your own Git repository** (GitHub/GitLab, private is fine — give your exercise
   teacher read access). One repository per team.
2. The repository must contain the **source code**, a **README** describing how to build and
   run it, and the **documentation** required by the assignment.
3. Record a **rosbag** (or a screen recording) of the successful mission and either commit it
   or link it — this is your evidence if something misbehaves on the demo machine.
4. Submit by **pushing before the deadline** and writing to your exercise teacher on Teams
   with the commit hash. The commit timestamp is what counts.
5. **Defend it in person** during the exercise: run the mission and answer questions about
   your own code.

Working in teams is allowed where the assignment says so, but **every member must be able to
explain the whole solution**. Defence is individual.

## Git version control

There are **no points for using git well**. But a repository that is impossible to follow —
one commit dumped the night before the deadline, force-pushed history, no way to tell who on a
team wrote what — makes it impossible to check the things that *do* carry points: whether the
work is actually yours, and whether each teammate can defend their share of it. In that
situation **points get deducted**, on top of whatever the assignment itself scores.

What counts as badly organized:

- The whole assignment arrives as one commit, or a handful of commits all timestamped minutes
  apart right before the deadline.
- History has been rewritten or force-pushed so earlier work is gone.
- On a team submission, commits don't make it possible to see who did what — everything is
  authored by one member, or messages give no indication of who worked on which part.
- No commits at all until the deadline, despite weeks of the exercise going by.

None of this requires a particular workflow — a handful of honest, incremental commits by
whoever actually wrote each part is enough. If you want a concrete structure instead of
figuring one out yourselves, here is one option (optional — use it, adapt it, or ignore it):

1. From `main`, create a `devel` branch. `main` stays empty/untouched until the end.
2. From `devel`, create a branch per feature or per person (`planning`, `outdoor-mission`,
   `<name>/yaw-control`, whatever fits how you split the work).
3. Open pull requests from those branches **into `devel`**, and merge them **without
   squashing** — keep every commit. This is what preserves the record of who did what and when,
   which matters most on team submissions where each member defends individually.
4. At the end of the semester, merge `devel` into `main` with a **squash merge**, collapsing
   the whole history into one clean commit on `main`. `devel` keeps the full history for
   reference; `main` stays readable for anyone just looking at the final result.

## Consultations

If something is unclear, or you want to check that you understood the assignment correctly:

1. **Ask during the exercise** — that is the fastest route.
2. **Write to your exercise teacher on Teams.** Ask concrete questions and include what you
   already tried, the error message, and the relevant piece of code.
3. **Arrange a private consultation** — online or in person — after writing on Teams.
4. Every teacher also has **consultation hours published in AIS**.

Do not sit stuck for a week. A five-minute question on Tuesday is worth more than five hours
of guessing on Sunday.

## Useful links

- **[`exam1/useful_links.md`](exam1/useful_links.md)** — environment setup, MAVROS/MAVLink
  references, planning and GPS/compass material. Most of it is useful for Exam 2 too.
- **[`tutorial/ros2_cheatsheet.md`](../tutorial/ros2_cheatsheet.md)** — ROS 2 workspace,
  console commands, and how to get a topic from `ros2 topic echo` into your C++ code.

For running the simulation itself, see the [repository README](../README.md). You bring the
three terminals up **by hand** — Gazebo, ArduPilot SITL and MAVROS — there is no launch script
that does it for you, and knowing what each command does is part of the point.
