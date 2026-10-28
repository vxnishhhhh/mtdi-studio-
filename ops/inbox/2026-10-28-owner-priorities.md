# Owner priorities, 28 Oct 2026 (afternoon, in the setup session)

The owner's words, condensed. These come before S1-06 slice 13, S1-08 and the rest of Stage 1.
Sessions take them in this order, one slice per session, behind the usual gates (ADR 0002).

1. **Make the back end visible.** Every engine capability must have a place in the studio where
   the owner can use it. "If I describe a feature, I should be able to go to a place in it and use it."
   No feature that exists only as a CLI command or an API route.
2. **Fix the UI glitches** across the studio ("a lot of UI glitches in between"), and teach the tour
   to catch each kind found so it cannot come back.
3. **A much bigger research database, usable from the studio.** Far more datasets (the catalogue has
   28 today); clicking a dataset in the Research tab opens it (metadata, licence, credit, a preview of
   the data); when what the owner looks for is not in the catalogue, the studio searches the public
   dataset sources online and adds what it finds, with licence and credit recorded. Free sources
   only (inbox free-tiers rule).
4. **Describe it, and MTDI helps build it.** The owner describes a project; MTDI uses all its layers
   to produce the firmware (C++), a wiring guide, a parts list and step-by-step build instructions,
   compiles the firmware (the Compatibility Lab, #52, already builds for Uno and ESP32), and saves
   it all as a project. This is Stage 3's Workbench; a first usable version may come earlier. The
   owner was asked whether to pull it ahead of Stage 2; no answer yet, so it stays after items 1 to 3.

Also decided the same day:
* #52 Compatibility Lab: approved by the owner, merged.
* NVTRA must ask before sending a camera frame to Gemini and remember the answer (#78, merged).
* Network access for science hosts: the five hosts in the repo already answer from the cloud
  environment; nothing for the owner to do.
* The owner asked for the full stage plan and a timeline; given in chat: MTDI 5.0 release roughly
  late January to February 2027, with hardware checks by the owner as the main risk.
