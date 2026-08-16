# Fynvo Release Process

Starting with **v0.3.0**, every production Fynvo release must include:

- version bump;
- database migrations where required;
- automated tests;
- CI validation;
- `CHANGELOG.md` entry;
- Home Assistant-visible release notes;
- Git tag;
- GitHub Release;
- user-readable release notes;
- upgrade/migration notes where relevant.

The changelog must describe changes from the user's perspective rather than listing raw commits.

The Home Assistant add-on must expose useful release information through the repository's changelog/release notes so updates can be understood from the add-on/update experience.

GitHub Releases should use the corresponding version tag, for example `v0.3.0`, with Added / Changed / Fixed / Security sections where applicable.

A release is not ready if the Home Assistant add-on cannot be opened through Home Assistant ingress, if `/` returns 404, if authentication only works through direct port access, or if the add-on enters an unexplained restart loop.
