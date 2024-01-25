# Changelog

<!--next-version-placeholder-->

## v0.2.5 (2024-01-25)

### Fix

* **auto-add:** Don't query users for domains to add if the provided api key is empty ([`7139460`](https://github.com/educationwarehouse/edwh-uptime-plugin/commit/713946079823dcde55bf3deb40e2b71cfe3cc92c))

## v0.2.4 (2024-01-25)

### Fix

* If API key in .env is left empty, don't crash with an error but show a warning instead ([`2ff8713`](https://github.com/educationwarehouse/edwh-uptime-plugin/commit/2ff87131aa1ff450b1f7226eeb12a0530b38a9dd))

## v0.2.3 (2024-01-25)

### Fix

* **auto-add:** Better prompt for domain selection; made --quiet still output but without color ([`306a5ea`](https://github.com/educationwarehouse/edwh-uptime-plugin/commit/306a5ea5c4d021894940e94f5b1041aabde4022b))

## v0.2.2 (2024-01-25)

### Fix

* Add --quiet to auto-add to ignore warnings/errors quietly ([`36e2d6a`](https://github.com/educationwarehouse/edwh-uptime-plugin/commit/36e2d6abd9fb08970c184df93025883c325e1dd7))

## v0.2.1 (2024-01-25)

### Fix

* ImportError: No module named 'termcolor._types' ([`24aa55f`](https://github.com/educationwarehouse/edwh-uptime-plugin/commit/24aa55f069ee2970a17788c37ff1437e14d93d11))

## v0.2.0 (2024-01-25)

### Documentation

* Explained how to use it as a library ([`23646c6`](https://github.com/educationwarehouse/edwh-uptime-plugin/commit/23646c62246102f6dbc72e849842d621632fd368))

## v0.1.1 (2024-01-25)

### Fix

* **autoadd:** Add flag in .env to prevent asking the same question again ([`e6d5894`](https://github.com/educationwarehouse/edwh-uptime-plugin/commit/e6d58946b4e2e4f88557e1daec5c4cf2c5754e82))

## v0.1.0 (2024-01-25)

### Feature

* Add --fmt to output as JSON or YAML for most relevant cases ([`2ce4c17`](https://github.com/educationwarehouse/edwh-uptime-plugin/commit/2ce4c17ed4cdc6fb465ac50eeeedefa83b18458b))
* Started on pytest but free tier api is limited to 10 req/min ([`1a1099a`](https://github.com/educationwarehouse/edwh-uptime-plugin/commit/1a1099a2954229ea2a1bed7e25fd342c2149da44))
* Add edit and reset monitor; added docstrings ([`3a21c27`](https://github.com/educationwarehouse/edwh-uptime-plugin/commit/3a21c270f8ddfce8218abc6a6b19808f2be99ce7))
* Initial version with some endpoints implemented ([`856b589`](https://github.com/educationwarehouse/edwh-uptime-plugin/commit/856b5891fde5e773c986f43d34abbb38fe87d2ef))

### Documentation

* Added more basic info ([`f9c0089`](https://github.com/educationwarehouse/edwh-uptime-plugin/commit/f9c008935f736daec63627dc94088c393c99bd88))