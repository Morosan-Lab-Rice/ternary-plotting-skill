# Phase discovery

Search the three binary systems and the ternary system separately. Use ICSD as the first database for experimental structure discovery. Consult assessed phase diagrams and primary experimental literature for phase identity, conditions, and coverage gaps. Use Materials Project as a secondary database if ICSD access or coverage is incomplete, or if computed candidates are requested. Check the reported composition, polymorph and relevant temperature, pressure, or synthesis conditions. For a solid solution, record which representative composition or boundary was plotted.

Mark experimental phases `reported`, computed records `computed`, and user-supplied entries without independently checked provenance `user`. Record the DOI, URL, database ID, or named dataset on each record. If a literature and database record refer to the same phase, keep the experimental classification and cite both sources. Keep independently identified polymorphs even when their stoichiometries coincide.

For computed candidates, install `mp-api`, set `MP_API_KEY` locally and run `python <skill-dir>/scripts/ternary.py discover A B C candidates.json`. This queries the four exact systems using the [Materials Project summary API](https://docs.materialsproject.org/downloading-data/using-the-api/querying-data). Review the candidates before merging them into the inventory. Database coverage, experimental existence and equilibrium stability are separate questions. If the API is unavailable, use literature or user-provided records and report the gap.

For Alkemade lines, look for experimental or assessed liquidus projections showing adjacent primary fields at the stated conditions. An isothermal tie line requires its own evidence of coexistence. See the [NIST phase diagrams glossary](https://www.nist.gov/system/files/documents/srd/General-Discussion-and-Glossary-of-Phase-Diagrams.pdf).

## Select phases for the ternary

1. Start with assessed phase diagrams and primary experimental papers for the three binaries and the ternary. Make a shortlist of the named phases at ambient pressure, about 0.1 MPa. Add separately identified condition-specific solids when the evidence warrants it, and label their conditions on the plot or in the inventory. Only claim equilibrium for the temperature and conditions established by the source.
2. Use ICSD as the first database for targeted verification. Look up shortlisted formulas or collection codes in the experimental inorganic collection. Keep one representative record per phase, with collection code and release, formula, structure type or space group, pressure, and original citation. Capture temperature when it affects phase identity or stability. Record synthesis and measurement pressure separately for recovered high-pressure products. Exclude phases documented only at nonambient pressure from the default plot and flag unclear pressure for review.
3. Group repeated refinements and measurements. Keep independently identified polymorphs even if they share a plotted point. Use a documented representative composition for solid solutions unless a sourced range is needed. Compare normalized compositions against Materials Project's experimental matches, and use the structure or citation when judging whether two records describe the same phase. Review database-only hits for conditions and provenance before including them. Report unresolved cases and coverage gaps.
4. For a short list, enter the selected metadata directly in the plot JSON. Skip cell parameters, Wyckoff sequences, CIFs, and full-page exports unless needed to resolve an assignment. Use the [local metadata parser](#process-a-saved-icsd-results-table) when an authorized export is useful. Narrow an export to the selected collection codes, and use the licensed API Service for scripted retrieval.

## Connect Materials Project

1. Sign in to [Materials Project](https://materialsproject.org/) or register for a free account. Open your profile dashboard and copy your API key.
2. In the Python environment you use for the skill, install the client with `python -m pip install mp-api`.
3. Set `MP_API_KEY` in the terminal session where you will run discovery. On macOS or Linux, run `export MP_API_KEY='<your key>'`. In PowerShell, run `$env:MP_API_KEY = '<your key>'`. Keep the key local and out of chat, input JSON, and Git.
4. Verify access with `python -c "from mp_api.client import MPRester; print(MPRester().get_database_version())"`. Then run `python <skill-dir>/scripts/ternary.py discover Mg Al O candidates.json`.

Ask whether the user wants to export `MP_API_KEY` for the current terminal session or configure it persistently for their user account. Persistent configuration saves them from exporting the key manually for each new session. Explain before proceeding that storing the key in a shell startup file makes it readable by anyone who can access that account or file, including other people who share the login and administrators with access. Keep it session-only on shared machines where others can access the account.

If the user opts in, show them how to add the export to their own shell startup file, such as `~/.zshrc` for zsh, and open a new terminal. Explain that this applies to shells that load that file. Use a placeholder in instructions and have the user enter the real key locally. Keep the key out of chat, repositories, and system-wide configuration.

When Materials Project is needed and cannot connect, give the user these steps and offer to help verify the local setup once they have an account. If they want to proceed offline, use reported or user-supplied compositions and state the resulting coverage gap. See the [official API setup guide](https://docs.materialsproject.org/downloading-data/using-the-api/getting-started).

## Experimental provenance in Materials Project

Discovery stores the Materials Project summary field `theoretical`. A value of `false` indicates an experimental structure match in Materials Project. A value of `true` means Materials Project found no experimental match, and these markers and labels are available at 20% opacity with `plot --include-theoretical`. The default plot includes computed records only when their flag is `false`. Missing or null flags indicate unknown provenance and are excluded in both modes. Keep experimental matches classified as Materials Project computed records. Use primary literature to identify independently reported phases and to establish phase equilibria. See the [Materials Project database notes](https://docs.materialsproject.org/changes/database-versions).

When plotting one marker per composition, retain every record ID and its flag in the inventory. Use the experimental-match style if any record at that composition has a match. Use the faded style only if all records are flagged theoretical.

## Search ICSD for reported structures

Ask whether the user has a licensed ICSD login or institutional access. Open [ICSD Web](https://icsd.fiz-karlsruhe.de/) through the institution's library link, on an authorized campus network, or via the institution's approved proxy or VPN if supported. For Rice, use the [Fondren ICSD proxy link](https://ezproxy.rice.edu/login?url=https://icsd.fiz-karlsruhe.de/) listed in the [Fondren database directory](https://libguides.rice.edu/az/databases?q=ICSD). Let the user complete sign-in and verification in the browser. If access is unavailable, report that ICSD was not searched and continue with accessible literature and Materials Project records.

Search each binary and the ternary separately for experimental inorganic structures with the exact element set. Review the structure type, composition, polymorph and cited publication. Record the ICSD collection code, database release and original citation. Use `kind: reported` for verified experimental records, retaining independently identified polymorphs. Structural evidence supports reported occurrence. Use separate phase-equilibrium evidence for tie lines and phase boundaries. Follow [FIZ Karlsruhe's citation guidance](https://icsd.products.fiz-karlsruhe.de/en/about/about-icsd).

Use the [official ICSD REST API](https://icsd.products.fiz-karlsruhe.de/en/products/icsd-products) for programmatic discovery only when the user has API Service access. A Web subscription alone does not establish API access. For the browser workflow, retain only the citation and composition metadata needed for the plot, subject to the user's license.

### Process a saved ICSD results table

For ICSD Web, run each exact-system query with **Experim. inorganic structures** selected. If your license permits local processing of the results, save the rendered **List Search Results** pages as HTML, or place the table metadata in CSV or TSV with the original column headers. The required columns are `Coll. Code` and `Struct. Form.`. The built-in **Export as CSV File** option can produce a tab-separated `.txt` file with headers such as `CollectionCode` and `StructuredFormula`. Pass the downloaded file directly to the parser. In the Rice session, exporting a page containing two records produced one file and used two CSV quota units. Include every result page needed for the comparison and record the release and reported hit counts separately. Install `beautifulsoup4` in the plotting environment for HTML input.

```sh
python scripts/icsd_metadata.py Mg Al O results/*.html --output-prefix output/mg-al-o-icsd
```

In PowerShell, collect the paths with `$tables = (Get-ChildItem .\results -Filter *.html -File).FullName` and pass `$tables` where the example uses `results/*.html`. Use the appropriate filter for your exported file extension.

The script runs locally. It writes a metadata-only `-records.csv` with one row per ICSD collection code and a `-compositions.csv` with normalized atomic fractions and all collection codes at each composition. It retains polymorphs and repeated measurements in the records table and reports formulas needing manual review. Compare the composition table with Materials Project using the same element order and atomic fractions rounded to 12 decimal places. Report supplied-page coverage and any unresolved formulas before treating the counts as complete.

Use the licensed [ICSD API Service](https://icsd.products.fiz-karlsruhe.de/en/products/icsd-products) for end-to-end scripted search and retrieval. Connect an adapter against the Swagger documentation supplied with that access. The [standard ICSD license](https://icsd.products.fiz-karlsruhe.de/sites/default/files/ICSD/documents/terms/ICSD_AGB_E_2021.pdf) restricts automated downloading, text mining, and indexing unless otherwise stipulated.
