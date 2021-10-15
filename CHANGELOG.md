# Changelog

All notable changes to this project will be documented in this file. See [standard-version](https://github.com/conventional-changelog/standard-version) for commit guidelines.

### [0.2.4](https://github.com/djdembeck/Audnexus.bundle/compare/v0.2.3...v0.2.4) (2021-10-15)


### Bug Fixes

* :children_crossing: handle http errors and exponential backoff ([8964fe4](https://github.com/djdembeck/Audnexus.bundle/commit/8964fe4c2771b39db8a81369d148475eb6160529))
* **author-search:** :ambulance: add greater weight to author name accuracy ([c7ba7b7](https://github.com/djdembeck/Audnexus.bundle/commit/c7ba7b76ebdb3e12b2ef1b50b1403c5369466fda))
* **author-search:** :bug: contributor stripping wasn't working properly. Fixes [#23](https://github.com/djdembeck/Audnexus.bundle/issues/23) ([72f464e](https://github.com/djdembeck/Audnexus.bundle/commit/72f464e18fb91309f3de009854fba8a3f5d86004))
* **author-search:** :bug: handle search failure when no artist tag is available but title is (manual search) ([f399442](https://github.com/djdembeck/Audnexus.bundle/commit/f39944288b803eeb08653cea883b9016019a6acd))
* **author-search:** :children_crossing: do basic author name cleanup prior to running search, to improve search success ([5869c7e](https://github.com/djdembeck/Audnexus.bundle/commit/5869c7ed4390c45d722278c7ef212c2a84e1980f))
* **author-search:** :children_crossing: if all authors are contributors use the first ([988ea27](https://github.com/djdembeck/Audnexus.bundle/commit/988ea276360a5a3378af83530a2f8850525a54cf))

### [0.2.3](https://github.com/djdembeck/Audnexus.bundle/compare/v0.2.2...v0.2.3) (2021-10-09)


### Features

* **settings:** :triangular_flag_on_post: new toggles: store author as mood tag and sort author by last name ([aee2d26](https://github.com/djdembeck/Audnexus.bundle/commit/aee2d26a7231019368a52a779d91c6bcbb2383eb))


### Bug Fixes

* **author-update:** :bug: single name authors would have sort applied erroneously ([80e2554](https://github.com/djdembeck/Audnexus.bundle/commit/80e25540da47846fd3ffc5fbed13e49480ece1ac))

### [0.2.2](https://github.com/djdembeck/Audnexus.bundle/compare/v0.2.1...v0.2.2) (2021-10-08)


### Bug Fixes

* **album-search:** :recycle: improve scoring accuracy on books with multiple authors ([319e16f](https://github.com/djdembeck/Audnexus.bundle/commit/319e16f9faf3fd551ab627a0cdb4ac4ceb3d9010))

### [0.2.1](https://github.com/djdembeck/Audnexus.bundle/compare/v0.2.0...v0.2.1) (2021-10-06)


### Features

* :art: improve handling of authors as contributors ([beb20f6](https://github.com/djdembeck/Audnexus.bundle/commit/beb20f66b7a474ad08aa0eab9bc8d8fb7f95af4e))
* **album-update:** :sparkles: use subtitle in Plex title where available ([4ff1654](https://github.com/djdembeck/Audnexus.bundle/commit/4ff1654286998fa48ffa785a5f2829511a24dee2))
* **search:** :sparkles: add asin search/extraction for authors and albums ([52062eb](https://github.com/djdembeck/Audnexus.bundle/commit/52062ebc2b389e68c75bc436b4f4193fbd480ecb))


### Bug Fixes

* **author-search:** :goal_net: handle unknown artist properly. fixes [#11](https://github.com/djdembeck/Audnexus.bundle/issues/11) ([499c753](https://github.com/djdembeck/Audnexus.bundle/commit/499c7534e185f95a77f2f7af522c35f8fc3dc952))

## [0.2.0](https://github.com/djdembeck/Audnexus.bundle/compare/v0.1.1...v0.2.0) (2021-10-04)


### Features

* :building_construction: add author support ([a18cda6](https://github.com/djdembeck/Audnexus.bundle/commit/a18cda64aed4cf3b90d41dc0c695af7e38725142))
* **author-search:** :sparkles: search/upgrade multi-author entries to single author entries ([e5d70dd](https://github.com/djdembeck/Audnexus.bundle/commit/e5d70ddcbb2b263c1a2dd6bf075b1628fb0c7d18))
* **author-update:** :sparkles: set author sort name ([e6e616b](https://github.com/djdembeck/Audnexus.bundle/commit/e6e616b683bcee62e67ba770b17417881a03453b))
* **update:** :sparkles: utilize tag list instead of 2 genre system ([7cd863f](https://github.com/djdembeck/Audnexus.bundle/commit/7cd863f5101d64ef2715390ba84b52379194eb8d))


### Bug Fixes

* :bug: fix case where no genres exist. fixes [#7](https://github.com/djdembeck/Audnexus.bundle/issues/7) ([2a017e9](https://github.com/djdembeck/Audnexus.bundle/commit/2a017e9bce4fa08013a4538ec7d732a122bc6c00))
* :bug: only request thumb when it exists ([498bbb3](https://github.com/djdembeck/Audnexus.bundle/commit/498bbb37d69b321b90a33d7849c7164fbd8721e9))

### 0.1.1 (2021-09-29)


### Features

* **search:** :children_crossing: fallback to keyword search for manual search ([8a400ec](https://github.com/djdembeck/Audnexus.bundle/commit/8a400ecac5fb0c5dbd46e03cd2381ecd2002dec1))
* **search:** :sparkles: rewrite search with pure API ([995b423](https://github.com/djdembeck/Audnexus.bundle/commit/995b423b66a804870411e3bf8156dbe82ab72622))


### Bug Fixes

* :bug: fix version variable name ([ee618dc](https://github.com/djdembeck/Audnexus.bundle/commit/ee618dcc212b0477bb60de15c624910cf9951ddd))
* :bug: only support us region for now ([a48f398](https://github.com/djdembeck/Audnexus.bundle/commit/a48f398a0f3b8000e1b115d0aae0fb5f4a7937e7))
* :bug: remove trailing line break ([faaa980](https://github.com/djdembeck/Audnexus.bundle/commit/faaa980ef986b506aaea44e1bad9fac0a3158fbe))
* **search:** :ambulance: fix albums with no album name matching to 'none' album name ([54fddc6](https://github.com/djdembeck/Audnexus.bundle/commit/54fddc6caf303adb7a62e98ac19472f0cfef3cd6))
* **search:** :ambulance: return True by default on pre check ([ddf3cfa](https://github.com/djdembeck/Audnexus.bundle/commit/ddf3cfaccfb76795b7e7212e984e60b21133e30e))
* **search:** :bug: fix library language scoring comparison ([772860f](https://github.com/djdembeck/Audnexus.bundle/commit/772860fa61b2440de7a2e8cf5a2958e1740df111))
* **search:** :bug: Only append results which have valid keys ([2361406](https://github.com/djdembeck/Audnexus.bundle/commit/2361406703f4dd49a47211350a46807cb97094bd))
* **update:** :bug: properly filter series in album sort ([9859012](https://github.com/djdembeck/Audnexus.bundle/commit/9859012468b3640f4aaa17941fc405171390b46b))
* **update:** :bug: set thumb to blank, in case api returns no thumb ([3f06e92](https://github.com/djdembeck/Audnexus.bundle/commit/3f06e9293280367cf8605d993f5966271e2493e6))

## 0.1.0 (2021-09-28)


### Features

* **search:** :sparkles: rewrite search with pure API ([995b423](https://github.com/djdembeck/Audnexus.bundle/commit/995b423b66a804870411e3bf8156dbe82ab72622))


### Bug Fixes

* :bug: only support us region for now ([a48f398](https://github.com/djdembeck/Audnexus.bundle/commit/a48f398a0f3b8000e1b115d0aae0fb5f4a7937e7))
* :bug: remove trailing line break ([faaa980](https://github.com/djdembeck/Audnexus.bundle/commit/faaa980ef986b506aaea44e1bad9fac0a3158fbe))
* **search:** :bug: Only append results which have valid keys ([2361406](https://github.com/djdembeck/Audnexus.bundle/commit/2361406703f4dd49a47211350a46807cb97094bd))
* **update:** :bug: set thumb to blank, in case api returns no thumb ([3f06e92](https://github.com/djdembeck/Audnexus.bundle/commit/3f06e9293280367cf8605d993f5966271e2493e6))
