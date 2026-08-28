# Exam 2 — Pick one topic (10 points)

**Deadline: end of week 12** (the last exercise). See [`../README.md`](../README.md) for the
semester rules, the late-submission penalty and the 56 % threshold.

> **⚠️ Partially draft.** The rules on this page are fixed, and **obstacle avoidance** below is
> finished — see [`obstacle-avoidance.md`](obstacle-avoidance.md). **Swarm control** and
> **natural language control** are still being reworked; treat their descriptions below as an
> outline of what's coming, and confirm details with your exercise teacher before picking one.

## How it works

You choose **one** of the offered topics and build it. All options are worth the same
**10 points** and all build on the control node you wrote for
[Exam 1](../exam1/README.md) — you are extending your own work, not starting over. Exam 2 is
deliberately smaller than Exam 1: it is one focused capability added to a system that already
flies, not a second full project.

Tell your exercise teacher which topic you picked **in week 7**. Changing your mind later is
possible but the deadline does not move.

## Topics

| Topic | What you build | Spec |
|---|---|---|
| **Obstacle avoidance** | Detect obstacles from the depth camera's point cloud and replan around them in flight | [`obstacle-avoidance.md`](obstacle-avoidance.md) |
| **Swarm control** | Control at least three UAVs — multiple SITL and MAVROS instances, namespaces, leader/follower or group commands | being reworked |
| **Natural language (LLM) control** | Drive the drone from natural-language commands interpreted by an LLM, with tool calling and safety limits | being reworked |

Roughly what the two unfinished topics involve — full specifications land here before you have
to choose:

- **Swarm control** — run several SITL and MAVROS instances under separate ROS namespaces,
  handle each vehicle's state and setpoints, implement either follow-the-leader or common
  commands to the group, and stop everything safely if one vehicle stops reporting.
- **Natural language (LLM) control** — connect an LLM (API or local) to your control node,
  translate free-text commands into flight actions via tool calling or structured output,
  implement a few custom commands, and enforce safety limits the model cannot talk its way past.

## Rules common to all topics

These apply whichever topic you pick:

1. **10 points**, split across the assignment's sections — the exact split is in each
   assignment's own file.
2. **You need ≥ 5.6 points (56 %)** to be allowed to sit the final exam. This threshold is
   separate from Exam 1's — see [`../README.md`](../README.md#grading).
3. **Points are awarded for what demonstrably works** during the defence, on a clean checkout
   of your repository.
4. **Later sections require the earlier ones.** You cannot score the advanced part of an
   assignment without the foundation it stands on.
5. **Documentation is required** — same expectations as
   [E1.4](../exam1/04_documentation_and_defence.md): what you chose, why, pros and cons, plus a
   solution diagram.
6. **You must be able to explain everything you submit.** Team work is allowed; the defence is
   individual.
7. **A badly organized git history can cost you points on top of the above.** No credit for
   git hygiene itself, but a repository nobody can follow — one dumped commit, no sign of who
   on a team did what — gets a deduction. See
   [`../README.md`](../README.md#git-version-control).

## Links

- Setup, MAVROS/MAVLink references and tooling: [`../exam1/useful_links.md`](../exam1/useful_links.md)
- ROS 2 workspace and topics: [`../../tutorial/ros2_cheatsheet.md`](../../tutorial/ros2_cheatsheet.md)
- [`ros_gz` bridge](https://github.com/gazebosim/ros_gz) — needed for obstacle avoidance's point cloud

Note that the **10-point test on the lecture material** is a separate thing from Exam 2, written
in the second half of the semester — see [`../README.md`](../README.md#overview).
