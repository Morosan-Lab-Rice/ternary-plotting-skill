# Phase discovery

Search the three binary systems and the ternary system separately. Start with assessed phase diagrams and primary experimental literature. Check the reported composition, polymorph and relevant temperature, pressure, or synthesis conditions. For a solid solution, record which representative composition or boundary was plotted.

Mark experimental phases `reported`, computed records `computed`, and user-supplied entries without independently checked provenance `user`. Record the DOI, URL, database ID, or named dataset on each record. If a literature and database record refer to the same phase, keep the experimental classification and cite both sources. Keep independently identified polymorphs even when their stoichiometries coincide.

For computed candidates, install `mp-api`, set `MP_API_KEY` locally and run `python <skill-dir>/scripts/ternary.py discover A B C candidates.json`. This queries the four exact systems using the [Materials Project summary API](https://docs.materialsproject.org/downloading-data/using-the-api/querying-data). Review the candidates before merging them into the inventory. Database coverage, experimental existence and equilibrium stability are separate questions. If the API is unavailable, use literature or user-provided records and report the gap.

For Alkemade lines, look for experimental or assessed liquidus projections showing adjacent primary fields at the stated conditions. An isothermal tie line requires its own evidence of coexistence. See the [NIST phase diagrams glossary](https://www.nist.gov/system/files/documents/srd/General-Discussion-and-Glossary-of-Phase-Diagrams.pdf).

## Connect Materials Project

1. Sign in to [Materials Project](https://materialsproject.org/) or register for a free account. Open your profile dashboard and copy your API key.
2. In the Python environment you use for the skill, install the client with `python -m pip install mp-api`.
3. Set `MP_API_KEY` in the terminal session where you will run discovery. On macOS or Linux, run `export MP_API_KEY='<your key>'`. In PowerShell, run `$env:MP_API_KEY = '<your key>'`. Keep the key local and out of chat, input JSON, and Git.
4. Verify access with `python -c "from mp_api.client import MPRester; print(MPRester().get_database_version())"`. Then run `python <skill-dir>/scripts/ternary.py discover Mg Al O candidates.json`.

When discovery cannot connect, give the user these steps and offer to help verify the local setup once they have an account. If they want to proceed offline, use reported or user-supplied compositions and state the resulting coverage gap. See the [official API setup guide](https://docs.materialsproject.org/downloading-data/using-the-api/getting-started).
