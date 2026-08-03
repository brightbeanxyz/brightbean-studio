# The application runs on a supported Django release

The application must run on a Django release that is still receiving security fixes.

At migration time the tree was pinned to `Django>=5.1,<5.2`. Django 5.1 left extended support in December 2025, so the deployed framework had been unpatched for roughly eight months while handling stored OAuth refresh tokens for a dozen third-party platforms.

A pin that excludes every supported release is a defect, not a configuration preference.
