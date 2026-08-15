---
icon: lucide/rocket
description: ColdFront is an open source resource and allocation management system for HPC centers, providing a central portal for administration, reporting, and measuring scientific impact.
---

# Wrangle Your Resources

ColdFront is an open source **resource and allocation management system** designed to provide a central portal for administration, reporting, and measuring the scientific impact of cyberinfrastructure resources. Created for high-performance computing (HPC) centers, ColdFront helps manage access to diverse resources across large user communities with a rich set of extensible metadata for comprehensive reporting.

!!! warning "Pre-production software"

    ColdFront 2.0.0 is currently under heavy development and is **not ready for production use**. See [Installation](installation/index.md) for development setup instructions.

---

## Resource Allocation Management System for HPC

<div class="grid cards" markdown>

-   :material-account-cog:{ .lg .middle } __HPC Administrators__

    ---

    Manage resource allocations, track utilization, automate policies and approval workflows across your center's infrastructure.

    [:octicons-arrow-right-24: Getting Started](admin-guide/index.md)

-   :material-account-tie:{ .lg .middle } __Principal Investigators__

    ---

    Request and manage allocations for your research group, track project usage, and measure scientific impact.

    [:octicons-arrow-right-24: User Guide](user-guide/index.md)

-   :material-code-tags:{ .lg .middle } __Plugin Developers__

    ---

    Extend ColdFront with custom plugins, integrate with external systems, and tailor the system to your center's needs.

    [:octicons-arrow-right-24: Plugin Development](plugins/index.md)

-   :material-handshake:{ .lg .middle } __Community__

    ---

    Join a vibrant community of HPC centers and contributors. Share experiences, contribute code, and help shape the future of ColdFront.

    [:octicons-arrow-right-24: Community](community.md)

</div>

---

## Key Features

- **Allocation lifecycle** — A structured workflow for managing allocations with self-service for researchers to help lower friction. Automated hooks ensure access stays current without manual effort.
- **Flexible resource modeling** — Organize your Slurm clusters, storage, and build other custom resources for your specific needs.
- **Rich metadata** — Create custom fields, tags, and attributes so you can track what matters in your workflow.
- **Plugin system** — Add new features or provide custom functionality without changing the core code.
- **Change tracking** — Change are logged so admins can see who did what and when.
- **Role based access control** — Set custom permissions per object for precise access control.
- **Multi-tenant** — Support multiple research groups and organizational units.

---

## Quick Start

!!! tip "Development setup"

    Clone the repository and run the development setup:

    ```bash
    git clone https://github.com/coldfront/coldfront.git
    cd coldfront
    uv sync --group dev --extra initializer
    DEBUG=True uv run coldfront migrate
    DEBUG=True PLUGINS="coldfront_initializer" uv run coldfront load_test_data
    DEBUG=True uv run coldfront runserver
    ```

[Learn more about installing ColdFront &rarr;](installation/index.md)

---

## License

ColdFront is released under the **Apache 2.0** license. See the [repository](https://github.com/coldfront/coldfront) for details.
