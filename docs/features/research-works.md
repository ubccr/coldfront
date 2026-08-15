# Research Works

ColdFront includes a Research Information System app (`coldfront.ris`) that
links research works to projects. A research work can be a publication or a funding
(grant) representing the scientific impact of the associated project.

ColdFront currently captures two specific research works:

- **Publication** — Identified by its DOI. Stores title, authors, year,
  journal, and source.
- **Funding** — Identified by its award number within a funding agency.
  Stores title, amount awarded, start date, end date, and source.

Each links to projects through a many-to-many field. The `source` field records
which provider imported the record first.

## Provider Plugins

Research providers search external systems and return candidate works for
import. ColdFront includes the following provider plugins by default:

- **ORCID** — Searches works and funding from a user's linked ORCID account.
- **Crossref** — Searches publications through the public Crossref API.
- **NSF** — Searches funding through the NSF Awards API.
- **Local** — Serves records already stored in ColdFront (never registered).

You can enabled these by adding them to your plugin config, for example:

```
PLUGINS='coldfront.ris.plugins.orcid,coldfront.ris.plugins.crossref,coldfront.ris.plugins.nsf'
```

Providers implement the `ResearchWorkProviderClient` interface and register
themselves using the `register_research_work_provider` decorator. The ris
registry maps each model to its provider classes. 

## Custom Providers

You can add a custom provider by subclassing `ResearchWorkProviderClient`
and implementing `key`, `display_name()`, `search()`, and `fetch()`. Decorate
the class with `register_research_work_provider(Model)` to register it. The
add/link views then call `search()` to build candidate rows for import.

## Linking Works to Projects

A project owner opens the Add Publications or Add Funding page for a project.
The page merges local records and provider results into a candidate table. The
owner selects the works to link, and ColdFront links the selected works to the
project.

## ORCID Accounts

Users can also link their ORCID accounts to ColdFront. After linking, the user
can search their own publications and funding for easier importing into ColdFront.
