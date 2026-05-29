# Portfolio Prompt For Another Agent

Use this repo as a traceable data-product portfolio, not as a pile of folders.

Start here:

- [portfolio/manifest.json](manifest.json)
- [portfolio/README.md](README.md)

Rules:

- every visual artifact must point back to a real repo file
- every claim must be backed by a file, script, endpoint, or test
- do not invent warehouse or Airflow deployment state that is not in the repo
- keep A1 as the control-room overview
- keep A2 as the trust investigation room
- keep A3 as the data model explorer
- keep A4 as pipeline operations
- keep A5 as warehouse explorer
- keep A6 as system architecture

When updating a PNG or mock:

- make sure the payload or proof file exists
- update the README that points to it
- update the manifest so the click path stays valid

The main question to answer is:

Can a hiring manager understand the system in 60 seconds and click every important claim back to a real artifact?
