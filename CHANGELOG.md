# Changelog

## [2.19.0](https://github.com/aergaroth/openjobseu/compare/v2.18.0...v2.19.0) (2026-03-31)


### Features

* **ingestion:** add description cleaning before job identity computation ([b9864ae](https://github.com/aergaroth/openjobseu/commit/b9864ae601d4798523924c265af9e9104169a223))

## [2.18.0](https://github.com/aergaroth/openjobseu/compare/v2.17.0...v2.18.0) (2026-03-31)


### Features

* **geo:** enhance geo classification for APAC and LatAm regions, add regression tests ([f7434a9](https://github.com/aergaroth/openjobseu/commit/f7434a9055dca42a735ebbbae076127b93085878))

## [2.17.0](https://github.com/aergaroth/openjobseu/compare/v2.16.0...v2.17.0) (2026-03-31)


### Features

* add market statistics export functionality ([a88ee36](https://github.com/aergaroth/openjobseu/commit/a88ee368f8434fdca931eb039afde7521cc4716e))
* enhance geo classification logic for global roles and non-EU regions ([ef99a44](https://github.com/aergaroth/openjobseu/commit/ef99a442a5e4a711efc423fcffa39688479e34af))


### Bug Fixes

* correct typos in non-EU scope title phrases and update .gitignore to include CLAUDE.md ([6ed31ef](https://github.com/aergaroth/openjobseu/commit/6ed31ef51bfbb92c893ff670854e4f60fb8dfb86))

## [2.16.0](https://github.com/aergaroth/openjobseu/compare/v2.15.0...v2.16.0) (2026-03-30)


### Features

* enhance frontend with improved layout, accessibility, and testing ([85be557](https://github.com/aergaroth/openjobseu/commit/85be557aa2490f2c6369083e1351026f821078c6))

## [2.15.0](https://github.com/aergaroth/openjobseu/compare/v2.14.0...v2.15.0) (2026-03-30)


### Features

* add new strong signals for US-based roles in geo data classifiers ([1fa2f9f](https://github.com/aergaroth/openjobseu/commit/1fa2f9f7152040a6fb293e9e9317b2f4d27b691e))
* enhance deployment workflow with post-deploy smoke tests and service URL retrieval ([1fa2f9f](https://github.com/aergaroth/openjobseu/commit/1fa2f9f7152040a6fb293e9e9317b2f4d27b691e))
* enhance post-deploy smoke test with OIDC token support for authentication ([ab0f583](https://github.com/aergaroth/openjobseu/commit/ab0f5836be59a5074b24f0818a313ecad5460ebb))
* implement post-deploy smoke check script for application health verification ([b82f316](https://github.com/aergaroth/openjobseu/commit/b82f316d5a94179d37484a8ea79db68d06c813d8))
* update hard geo patterns to include new USA-based role signals ([1fa2f9f](https://github.com/aergaroth/openjobseu/commit/1fa2f9f7152040a6fb293e9e9317b2f4d27b691e))


### Bug Fixes

* add authentication headers to health check request ([9217fdd](https://github.com/aergaroth/openjobseu/commit/9217fdda88c2c18df9ab44c6c724d058adee5588))
* correct token audience key in authentication step ([38027fc](https://github.com/aergaroth/openjobseu/commit/38027fce0f03e42cb109528503ef7b635a3a446a))
* enhance health check with retry logic for service readiness ([c49f82b](https://github.com/aergaroth/openjobseu/commit/c49f82bb94a0adc194fe08d0d998e62959cc2a56))
* refactor authentication step and streamline post-deploy smoke test execution ([61c601c](https://github.com/aergaroth/openjobseu/commit/61c601c2dce386715b6f6935e368cba640fd3af7))
* update smoke test dependencies and remove redundant steps in deployment workflow ([fe3925e](https://github.com/aergaroth/openjobseu/commit/fe3925ee0b6575b9c998882e68a0d1c2d7778331))

## [2.14.0](https://github.com/aergaroth/openjobseu/compare/v2.13.0...v2.14.0) (2026-03-29)


### Features

* enhance job feed UI with filters and improved layout ([c567297](https://github.com/aergaroth/openjobseu/commit/c567297f9187f468e9bac898caae3f89b1e7d640))

## [2.13.0](https://github.com/aergaroth/openjobseu/compare/v2.12.0...v2.13.0) (2026-03-29)


### Features

* **geo:** enhance non-EU classification with scope title phrase handling ([045b644](https://github.com/aergaroth/openjobseu/commit/045b644416f796fd0e2805c86dd62dde1564a983))

## [2.12.0](https://github.com/aergaroth/openjobseu/compare/v2.11.1...v2.12.0) (2026-03-29)


### Features

* enhance backfill process to handle missing provider; add tests for skipped companies ([9007e59](https://github.com/aergaroth/openjobseu/commit/9007e596db9c441ef236bdcc8aada4a680db492b))
* implement backfill processes for salary, department, and compliance data; enhance maintenance pipeline logging ([7f888b6](https://github.com/aergaroth/openjobseu/commit/7f888b663feb80ab72a00377876c01834f2f51ce))

## [2.11.1](https://github.com/aergaroth/openjobseu/compare/v2.11.0...v2.11.1) (2026-03-29)


### Bug Fixes

* update job rendering logic to use filter function after fetching jobs ([9e263f1](https://github.com/aergaroth/openjobseu/commit/9e263f177570dbde314e59a998ea567662807681))

## [2.11.0](https://github.com/aergaroth/openjobseu/compare/v2.10.1...v2.11.0) (2026-03-29)


### Features

* enhance job feed UI and functionality with search filter and improved layout ([098078e](https://github.com/aergaroth/openjobseu/commit/098078eb37eb610db6be1486c189a37e0bbd72f9))

## [2.10.1](https://github.com/aergaroth/openjobseu/compare/v2.10.0...v2.10.1) (2026-03-28)


### Bug Fixes

* change non_eu countries to lower case ([40f5c20](https://github.com/aergaroth/openjobseu/commit/40f5c202e668c3695e8d786a3d8ab79b16428845))
* Expand geo_data with additional countries ([0cc9a9e](https://github.com/aergaroth/openjobseu/commit/0cc9a9ee80c1ce55cd1919a7cf8b7ca307fd62da))

## [2.10.0](https://github.com/aergaroth/openjobseu/compare/v2.9.0...v2.10.0) (2026-03-28)


### Features

* **cleaning:** enhance HTML cleaning and encoding functions ([f59d969](https://github.com/aergaroth/openjobseu/commit/f59d969ec06b53ef547fd863fb52c9722b22ddf5))


### Bug Fixes

* **cleaning:** format regex patterns for HTML cleaning consistency ([1a08922](https://github.com/aergaroth/openjobseu/commit/1a089223564ec1af99aa4aa65a224d7ddc115fa8))

## [2.9.0](https://github.com/aergaroth/openjobseu/compare/v2.8.0...v2.9.0) (2026-03-28)


### Features

* Add logging and enhance HTML cleaning in cleaning module; introduce new test cases for cleaning functions ([2267078](https://github.com/aergaroth/openjobseu/commit/2267078902d6a3fa8e1e43bc6200d7d4e4eca890))

## [2.8.0](https://github.com/aergaroth/openjobseu/compare/v2.7.0...v2.8.0) (2026-03-27)


### Features

* Enhance task management with logging and new discovery endpoints ([2b750e2](https://github.com/aergaroth/openjobseu/commit/2b750e298186dfa10f3ef0d40e733a07cd5d2732))

## [2.7.0](https://github.com/aergaroth/openjobseu/compare/v2.6.0...v2.7.0) (2026-03-27)


### Features

* **tests:** add comprehensive tests for Cloud Tasks and Google Search functionality ([02bbd97](https://github.com/aergaroth/openjobseu/commit/02bbd97481397141e57a2a53ba2052fd88c48a89))
* **tests:** skip local Docker management for PostgreSQL in GitHub Actions ([ebcc4b0](https://github.com/aergaroth/openjobseu/commit/ebcc4b0a60bd9168c78c4a54b7fe1c459e376ef8))


### Bug Fixes

* **Dockerfile:** update base image to use public ECR for Python 3.13-slim ([0da0b4d](https://github.com/aergaroth/openjobseu/commit/0da0b4d3def33fea5a8afd303ecbecb7b801dc75))

## [2.6.0](https://github.com/aergaroth/openjobseu/compare/v2.5.0...v2.6.0) (2026-03-27)


### Features

* **scheduler:** add ping ingestion and discovery jobs with health check ([00f7b89](https://github.com/aergaroth/openjobseu/commit/00f7b8985f70187697de508e3c6cdc08b9cd5d19))

## [2.5.0](https://github.com/aergaroth/openjobseu/compare/v2.4.1...v2.5.0) (2026-03-26)


### Features

* enhance text cleaning with boilerplate removal and markdown artifact handling ([760a485](https://github.com/aergaroth/openjobseu/commit/760a485a894d342fdbba0edf9b576adfcb7241fd))

## [2.4.1](https://github.com/aergaroth/openjobseu/compare/v2.4.0...v2.4.1) (2026-03-25)


### Bug Fixes

* **classifiers:** prevent orphaned substrings using word boundaries ([d1659e9](https://github.com/aergaroth/openjobseu/commit/d1659e9f323a8ec7f57837ead1a35cc67fcb6759))

## [2.4.0](https://github.com/aergaroth/openjobseu/compare/v2.3.1...v2.4.0) (2026-03-25)


### Features

* Add RemoteClass and GeoClass enums for job categorization ([35b22e5](https://github.com/aergaroth/openjobseu/commit/35b22e59ad55dd3e645e2d7a378f8247767d1c7f))

## [2.3.1](https://github.com/aergaroth/openjobseu/compare/v2.3.0...v2.3.1) (2026-03-24)


### Bug Fixes

* **compliance-engine-and-classifiers:** enhance geo and remote classification logic for mixed regions and title handling ([446936b](https://github.com/aergaroth/openjobseu/commit/446936bc387e246260fc04110339d4ca40a165b8))

## [2.3.0](https://github.com/aergaroth/openjobseu/compare/v2.2.2...v2.3.0) (2026-03-23)


### Features

* add workflow to sync changes from main to develop ([c4d1956](https://github.com/aergaroth/openjobseu/commit/c4d19568bd066c737d36f2f082263c1e9bdf596e))
* add workflow to sync changes from main to develop ([db6e33f](https://github.com/aergaroth/openjobseu/commit/db6e33f882c06c1b29239343c21460affa086c14))

## [2.2.2](https://github.com/aergaroth/openjobseu/compare/v2.2.1...v2.2.2) (2026-03-23)


### Bug Fixes

* change release type to simple and remove release-please manifest ([4775262](https://github.com/aergaroth/openjobseu/commit/4775262d4d3113119c5980c471ca7d856d27ca9b))
* change release type to simple and remove release-please manifest ([da00b48](https://github.com/aergaroth/openjobseu/commit/da00b48a55ef82a6c569dd8e8640bf735e94627e))

## [2.2.1](https://github.com/aergaroth/openjobseu/compare/v2.2.0...v2.2.1) (2026-03-23)


### Bug Fixes

* update frontend asset publishing to use vars for bucket reference ([f65f57d](https://github.com/aergaroth/openjobseu/commit/f65f57d7a06d46fa972a1f4c6b1643989794d49f))
* update frontend asset publishing to use vars for bucket reference ([2a434d1](https://github.com/aergaroth/openjobseu/commit/2a434d1f0c9b74b0dd10c6216cb4ace38e32633b))

## [2.2.0](https://github.com/aergaroth/openjobseu/compare/v2.1.0...v2.2.0) (2026-03-23)


### Features

* migrate github actions auth to gcp wif ([ad0c115](https://github.com/aergaroth/openjobseu/commit/ad0c11576c89afca091665ad32c9db83c2ead29f))
* migrate GitHub Actions auth to GCP Workload Identity Federation ([3f46e63](https://github.com/aergaroth/openjobseu/commit/3f46e6347f666ff4a605e4bd0f08a595dbfb7c00))


### Bug Fixes

* update service account references to use dynamic email ([8d34cd3](https://github.com/aergaroth/openjobseu/commit/8d34cd330d3a1ff0e1eda92f599403be69cf5869))
* update version ([17a6a55](https://github.com/aergaroth/openjobseu/commit/17a6a55129fa4727da34a05a5a0112291767517b))

## [2.1.0](https://github.com/aergaroth/openjobseu/compare/v2.0.1...v2.1.0) (2026-03-23)


### Features

* Restrict Cloud Run invoker and enhance frontend asset publishing ([#80](https://github.com/aergaroth/openjobseu/issues/80)) ([4a073e8](https://github.com/aergaroth/openjobseu/commit/4a073e8b398416499cac97fade95ea04c959bdab))

## [2.0.1](https://github.com/aergaroth/openjobseu/compare/v2.0.0...v2.0.1) (2026-03-23)


### Bug Fixes

* **performance:** optimize frontend exporter and enforce least privilege model ([a6e1d72](https://github.com/aergaroth/openjobseu/commit/a6e1d72693fb2925c5a90e2535a60de43bb4a105))
* **security:** enforce fail-fast for OAuth configs in non-local environments ([4880b34](https://github.com/aergaroth/openjobseu/commit/4880b34c6d1bacb9d1c26b0f217bce7fca019ad6))
* **security:** enforce strict TLS verification in careers crawler ([a7369fb](https://github.com/aergaroth/openjobseu/commit/a7369fb3405795d14bfcd0ea807b3652fb806e61))


### Documentation

* update architecture and security matrix to reflect strict policies ([c9010ef](https://github.com/aergaroth/openjobseu/commit/c9010efdffa370f2216e43b4b20253853e8235cf))

## [2.0.0](https://github.com/aergaroth/openjobseu/compare/v1.0.0...v2.0.0) (2026-03-22)


### ⚠ BREAKING CHANGES

* legacy adapters, v2/v3 policy modules, and old normalization worker paths were removed in favor of the new OpenJobsEU 2.0 structure.

### Features

* **a6.1:** extract company name from RSS titles when missing ([92c7140](https://github.com/aergaroth/openjobseu/commit/92c7140cc2a4dbb56997f5c10859beb0a681bed5))
* add advanced filtering to jobs read API ([e53af30](https://github.com/aergaroth/openjobseu/commit/e53af3008ff8d8247b27477f08c7a891d678e90e))
* add audit companies endpoint with filters ([3641e86](https://github.com/aergaroth/openjobseu/commit/3641e86b00ada6394cb8d4e12db40b849f6f552c))
* add availability checker with ttl-based status transitions ([dec1d80](https://github.com/aergaroth/openjobseu/commit/dec1d806fceb25ada3d160ee9d606895dde177c4))
* add availability checking to rss tick worker ([7c2426d](https://github.com/aergaroth/openjobseu/commit/7c2426d4592cc057d9a14af8cfb1ba3898ea747f))
* add BASE_URL environment variable and update OIDC audience in Cloud Scheduler jobs ([e148170](https://github.com/aergaroth/openjobseu/commit/e1481701e76afaffa3b625ffc515b1001cd1d847))
* add canonical job ID computation and related database updates for job reposting ([af5d92f](https://github.com/aergaroth/openjobseu/commit/af5d92f34a6e7e3f70a34ab8270fb2b3671c23da))
* add CHANGELOG and protect_develop workflow ([f41f296](https://github.com/aergaroth/openjobseu/commit/f41f296b8d7929e26a19fb6a542c96da15743dee))
* add commit message validation workflow using Commitizen ([27113c9](https://github.com/aergaroth/openjobseu/commit/27113c93e373c2bca08059a047f46bd22460e0f4))
* Add companies API endpoint and enhance discovery processes ([47a9289](https://github.com/aergaroth/openjobseu/commit/47a92896bce73b64629be0f1eb93b3f4285472ae))
* add compliance backfill script and fix JSON serialization in DB logic ([51203bb](https://github.com/aergaroth/openjobseu/commit/51203bbff010b46afce6adab86acaed3d356b4b4))
* add compliance score and status to policy application logic ([0f7239e](https://github.com/aergaroth/openjobseu/commit/0f7239e6eafa3043f694d1b32f4d74c117e82a35))
* add compliance stats endpoints and update frontend to display 7-day compliance metricsupdate audit_tool and api for compliance statistics ([adf5fc3](https://github.com/aergaroth/openjobseu/commit/adf5fc31a6bf74a507230d082326d0eced98d983))
* add docker-compose for local development workflow ([d03964c](https://github.com/aergaroth/openjobseu/commit/d03964c8b0c2c2c1e1fd60e9467b3da41d747f1c))
* add dockerfile for reproducible test environment ([908aa48](https://github.com/aergaroth/openjobseu/commit/908aa48378b776fb26fb0f932e3a865776915325))
* add example ingestion source with normalization and tests ([cf13d87](https://github.com/aergaroth/openjobseu/commit/cf13d87b8dcca27d2394c1366b2e299500592b6b))
* Add full sync script for tick endpoint with retry mechanism ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* add geo_data module and enhance remote signals with new options ([831b12d](https://github.com/aergaroth/openjobseu/commit/831b12d4ac4a8fc68403e1a607444f21d81a1fbe))
* add geo_data module and enhance remote signals with new options ([fd15599](https://github.com/aergaroth/openjobseu/commit/fd15599d4d09ba6aa4b5b6c7911a6862aa29f05c))
* add Google OAuth secrets and allowed email configuration to Terraform apply ([df097b6](https://github.com/aergaroth/openjobseu/commit/df097b6dd790bfa64ea79c21b6d04f48b9055d07))
* add Google Secret Manager resources for API keys and update variables for Google API key and CSE ID ([e98c1d0](https://github.com/aergaroth/openjobseu/commit/e98c1d07212c4b8fc12c47a2fe8a604ab1c99a5b))
* add IF NOT EXISTS clause to job taxonomy and dataset indexes ([012dcf5](https://github.com/aergaroth/openjobseu/commit/012dcf5efd4e8c13302ab6c996fdeacd755bddbb))
* add initial migration for job indexes ([bea6288](https://github.com/aergaroth/openjobseu/commit/bea6288120861952f20537b848f532724fee7d3e))
* add job preview endpoint and enhance audit panel with new features ([18a20fc](https://github.com/aergaroth/openjobseu/commit/18a20fc86281dd3cc5451af6c4e1198e93091d0a))
* add lifecycle rules for job expiration ([b00dce2](https://github.com/aergaroth/openjobseu/commit/b00dce21fbaa8c530878fe19cc22a4fef4ef9b2c))
* Add limit parameter to internal tick endpoint for controlled processing ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* add minimal runtime with health endpoints ([0b3ae4e](https://github.com/aergaroth/openjobseu/commit/0b3ae4e31f7f10ca078de59819a496a981e0bd84))
* add minimal runtime with health endpoints ([9ee481a](https://github.com/aergaroth/openjobseu/commit/9ee481a390cc82b9df032b46b3b1f4d726d11369))
* add non-EU classification logic and corresponding tests for geo_v3 ([cc50627](https://github.com/aergaroth/openjobseu/commit/cc50627449cc1b5da2b0046264400bd5ae3db165))
* add performance timing to careers discovery process ([cfe4eec](https://github.com/aergaroth/openjobseu/commit/cfe4eec7b76eadaacd4a83e8af217a5e0d84fbef))
* add Personio and Recruitee adapters for job fetching and processing ([b9f4ab1](https://github.com/aergaroth/openjobseu/commit/b9f4ab1305b0cddfa21eed89383e80c51c594981))
* add planned features section to roadmap with dataset API and analytics ([837e5b1](https://github.com/aergaroth/openjobseu/commit/837e5b1441513c9835d269339a3ad3de5aa3216b))
* add rss ingestion with dev-only local fallback ([a2a36cc](https://github.com/aergaroth/openjobseu/commit/a2a36cc990cee37ccf4a382aa247b56f4dbf1a7b))
* add salary backfill endpoint and refactor audit registry ([508b5f0](https://github.com/aergaroth/openjobseu/commit/508b5f05de4f06537078f4a4c17bc649fb4519e3))
* add scheduler heartbeat and internal tick endpoint ([b4109f1](https://github.com/aergaroth/openjobseu/commit/b4109f1b5026d4e25b44bee6fb71b3b83e16eec9))
* add scheduler heartbeat and runtime tick endpoint ([8c7fd10](https://github.com/aergaroth/openjobseu/commit/8c7fd10a772997ce972a3df5ff92af4a36aafa7c))
* add sqlite persistence for ingested jobs ([4d36a25](https://github.com/aergaroth/openjobseu/commit/4d36a25087cc82192e2c4e03cc0b38f512581b9c))
* add test for rejected job not inserting compliance report without job ID ([08e4d7f](https://github.com/aergaroth/openjobseu/commit/08e4d7f6e1b2f849db4b9c0cde4c0e7f2261727b))
* add unit tests for job fetching and lifecycle pipeline execution ([6994cc8](https://github.com/aergaroth/openjobseu/commit/6994cc854c302df97e1221b84469c2e2b8f1e875))
* added example test and __init__.py for modules ([6bacb89](https://github.com/aergaroth/openjobseu/commit/6bacb8957ec6a2a366fefca672c51b4fce66f07f))
* added simple frontend ([e21c418](https://github.com/aergaroth/openjobseu/commit/e21c418e1e5388f53e12676690df9d4bf347398c))
* **api:** add public /jobs/feed ([b57c40b](https://github.com/aergaroth/openjobseu/commit/b57c40bab51a62afbd9efdfd22e7c2e00ecab264))
* **api:** filter feed by minimum compliance score ([83e9636](https://github.com/aergaroth/openjobseu/commit/83e96364e9315089cd69cb7fe109bfe82ebc25b3))
* **ats/greenhouse:** add INCREMENTAL_FETCH control to adapter ([9809812](https://github.com/aergaroth/openjobseu/commit/980981256687dd1f0727fb75c75bd27ea0ef2162))
* **ats:** standardize adapter interfaces and add registry registration ([ecd148b](https://github.com/aergaroth/openjobseu/commit/ecd148b9626e786d215b62f498ed21d72fd73adf))
* **ats:** standardize adapter interfaces and add registry registration ([cb9f129](https://github.com/aergaroth/openjobseu/commit/cb9f129bd7f0eeef705dca65b8d1e9ad03921b16))
* **audit panel:** add cached static endpoints and ATS actions ([b292d11](https://github.com/aergaroth/openjobseu/commit/b292d111bd4746b0fe09a251d9ddc446f1eef2c6))
* **audit:** add safeLoadAtsHealth to async data loading ([69a4a61](https://github.com/aergaroth/openjobseu/commit/69a4a61162a3ae4ee496020b1d266ecd3f48fa8c))
* **audit:** rename Offer Audit Panel to Admin Audit Panel and add new backfill options ([848fc46](https://github.com/aergaroth/openjobseu/commit/848fc46e301269acce5873f815c373d6f41458ed))
* **audit:** update test to reflect renaming of Offer Audit Panel to Admin Audit Panel ([77df720](https://github.com/aergaroth/openjobseu/commit/77df720fd133c07708b51a6aab0a3e10a50d8536))
* **auth:** add email whitelist and improve OAuth configuration handling ([6109dbd](https://github.com/aergaroth/openjobseu/commit/6109dbdddbcae11b08275a453aeaa694afffebb1))
* **careers_crawler:** Update to use requests.Response type and explicit URL/text extraction ([6f640a4](https://github.com/aergaroth/openjobseu/commit/6f640a4e4f182fc9e71db052c0cf0e33dc2f3268))
* **careers_crawler:** Update to use requests.Response type and explicit URL/text extraction ([6c6faa3](https://github.com/aergaroth/openjobseu/commit/6c6faa3ddb4bb8fa69888dbddd0cd22af542437d))
* changed tick formatting, added metrics for employer ingestion, update docs ([48b20c9](https://github.com/aergaroth/openjobseu/commit/48b20c95a47a85c0ceb219ee6ef593e6c15d6fb0))
* complete compliance resolution in ingestion and populate compliance_reports table ([a14aa68](https://github.com/aergaroth/openjobseu/commit/a14aa6810c429490a9fe6dfe4a2c3e231b8fe008))
* compliance decision trace, unique reports and backfill script ([0cf16a7](https://github.com/aergaroth/openjobseu/commit/0cf16a7fa4e65f61e9eabec71ca39a5666816c9f))
* **compliance:** replace resolver with normalized decision matrix ([573f44b](https://github.com/aergaroth/openjobseu/commit/573f44ba65d7cc191de6eb2f7a7102b110580f80))
* **compliance:** update remote class normalization and scoring logic ([4a05705](https://github.com/aergaroth/openjobseu/commit/4a057055b5d42acdd1957f72f63360551a783f81))
* conditionally persist compliance report for canonical jobs only ([10a3c37](https://github.com/aergaroth/openjobseu/commit/10a3c37ba411c7738e6642d2c6e5cc8b85c830ac))
* consolidate architecture documentation and add system map ([1ba215a](https://github.com/aergaroth/openjobseu/commit/1ba215af856b158cd082c2a24393e7c3dcfa877e))
* Create scripts for auditing HTML leftovers and description sanity checks ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* decouple Cloud Tasks handlers and implement time-budgeting ([749152b](https://github.com/aergaroth/openjobseu/commit/749152b022fdb8c4ea388bcd847ad1bc75ff5f67))
* **discovery:** enhance error handling in probe_ats function ([e00f971](https://github.com/aergaroth/openjobseu/commit/e00f97127b5323de2640c9e020ad8fd0a230e280))
* Enable incremental fetch for Greenhouse adapter and refine job enrichment logic based on compliance status ([10fac4c](https://github.com/aergaroth/openjobseu/commit/10fac4c86ac4cdc7a5ad9aaaf8d6c39727117fc1))
* enhance ATS adapters, discovery pipeline, and secure Audit UI ([4bc467b](https://github.com/aergaroth/openjobseu/commit/4bc467bbafcc7770c4fdbc407c78e1e641915220))
* enhance ATS adapters, discovery pipeline, and secure Audit UI ([8039b2c](https://github.com/aergaroth/openjobseu/commit/8039b2c90167a32837ea775e92e4fa04c6afcd61))
* Enhance ATS ingestion and canonical model with taxonomy ([55f64ef](https://github.com/aergaroth/openjobseu/commit/55f64ef38f4a20a70c9889174a5e7c69d9b075c2))
* enhance ATS integration with batching and sync status updates ([1567d2d](https://github.com/aergaroth/openjobseu/commit/1567d2d2f44bb0a1c0059c9ff1a70e90f9239b7c))
* enhance discovery pipeline with new metrics and update filtering logic ([190722f](https://github.com/aergaroth/openjobseu/commit/190722fcbc0a7294e3a3eb2d13641afb89d5ebcc))
* enhance discovery processes and improve Cloud Run configurations ([dff5944](https://github.com/aergaroth/openjobseu/commit/dff59449e6ac3c3c5fdb5c533ad0570af90ba761))
* enhance error handling in Cloud Tasks and clean up headers for task creation ([85f11ca](https://github.com/aergaroth/openjobseu/commit/85f11cad2bfc7767fffcc309e290df7575284851))
* Enhance geo data classification with major cities mapping to EU countries ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* enhance job description assembly and cleaning across ATS adapters ([51b61f3](https://github.com/aergaroth/openjobseu/commit/51b61f331aeb44fd630fcdb399317c91a446d8ff))
* enhance job description handling and add Greenhouse adapter support in vie_job_from_feed.py script ([d350de8](https://github.com/aergaroth/openjobseu/commit/d350de8e6be8509cde69e2c67265fc6b32f17ac3))
* enhance job location extraction and salary parsing logic ([52c4cc6](https://github.com/aergaroth/openjobseu/commit/52c4cc6f9f9d13fcd2b1e04f68f3ba91a6ac39bb))
* Enhance job search functionality with GIN indexing and fuzzy search support ([3831279](https://github.com/aergaroth/openjobseu/commit/38312798f92ef01548eaf95344eb3d0966aa53ba))
* enhance remote classification logic and add new test cases for home-based scopes ([acca94e](https://github.com/aergaroth/openjobseu/commit/acca94ee75dac26c8c2eb494bc2df5efac35e09c))
* Enhance salary extraction and currency mapping ([73876f6](https://github.com/aergaroth/openjobseu/commit/73876f6b37d4ec7edca80445de0612b0becdd285))
* enhance SmartRecruiters adapter with improved job probing and error handling ([064cd97](https://github.com/aergaroth/openjobseu/commit/064cd97ebc87068e5ef66137a8172bad5e8fc816))
* enhance task statistics display with improved JSON formatting and styling ([94cd0ac](https://github.com/aergaroth/openjobseu/commit/94cd0ac1dead77ba1aaf7a326310587d6ca3040e))
* expose visible jobs as new + active in read API ([a7e68db](https://github.com/aergaroth/openjobseu/commit/a7e68db0603cd02107b0e70a5387d45ab999d351))
* extend job lifecycle with NEW status and TTL rules ([9e91944](https://github.com/aergaroth/openjobseu/commit/9e91944ef38d03c9594356512192182280097457))
* **frontend:** add minimal static feed table ([1b56b61](https://github.com/aergaroth/openjobseu/commit/1b56b615eddc5e62e5b66c2c490331b3a14c4b85))
* implement BASE_URL for task handler URLs and enhance error handling for Cloud Tasks ([e80563e](https://github.com/aergaroth/openjobseu/commit/e80563e10696a43a7f228d3c9c07209d306d81e6))
* Implement CI/CD workflows for development and production ([65b7c70](https://github.com/aergaroth/openjobseu/commit/65b7c70eefee6d62da60a14f9298ae176e90bb10))
* Implement employer ingestion limit configuration for better resource management ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* implement geo classification logic and add unit tests for geo_v3 ([4cf3ab0](https://github.com/aergaroth/openjobseu/commit/4cf3ab0202de026c49cb9d6e3eaf9439aa2fa8cb))
* implement incremental fetch logic across ATS adapters and update ingestion process ([5e55c49](https://github.com/aergaroth/openjobseu/commit/5e55c49f1b38a32e5381b1a3124137e7d7b44ca6))
* implement internal secret authentication for internal access and update tests ([849886d](https://github.com/aergaroth/openjobseu/commit/849886d05230f69c3460d388bea5c87b38499bcc))
* implement job probing functionality in ATS adapters and discovery pipeline ([2948fd7](https://github.com/aergaroth/openjobseu/commit/2948fd7fe4113dc08b77ca025ef466c791ca72d1))
* implement market metrics worker and related database schema updates ([a19c15c](https://github.com/aergaroth/openjobseu/commit/a19c15c6cd0afa3889d59bd1f908bd9096fb3cd1))
* implement pagination state updates in job loading function ([cc0f9c5](https://github.com/aergaroth/openjobseu/commit/cc0f9c57a2813f9c4f438c5afe3c6fdc174547d1))
* implement pagination state updates in job loading function ([b161702](https://github.com/aergaroth/openjobseu/commit/b16170288e74093f637abadb6cfe4218487a901e))
* Implement salary extraction and transparency detection ([6470c9a](https://github.com/aergaroth/openjobseu/commit/6470c9a4bd7c5018945672801a87d2614f700591))
* implement SmartRecruiters adapter and integrate into discovery pipeline ([44fc76b](https://github.com/aergaroth/openjobseu/commit/44fc76ba04b3275d8695eb472ebb31fb00a15ab3))
* Implement task cancellation and progress tracking in async operations ([6aa19a1](https://github.com/aergaroth/openjobseu/commit/6aa19a1ce5d5b734d68607ed6d48a0643ec0f94b))
* implement user authentication with OAuth and session management, enhance discovery pipeline with metrics, and improve audit panel UI ([3a667c3](https://github.com/aergaroth/openjobseu/commit/3a667c3f840c30a4cce554895d483b3a4d9872b3))
* improve career URL guessing logic and add URL validation ([fdba95f](https://github.com/aergaroth/openjobseu/commit/fdba95f6db8a2ac13ea2439893647c1206a0af23))
* Improve salary extraction logic and currency mapping ([f47d634](https://github.com/aergaroth/openjobseu/commit/f47d6348371ee71ca432ed690172bfcae7ff9d00))
* improve salary parsingand canonical identity handling ([1ec454a](https://github.com/aergaroth/openjobseu/commit/1ec454a4481167fa513106ae8b4bcfe4177f9c96))
* ingest local job source during scheduler tick ([19cb3c4](https://github.com/aergaroth/openjobseu/commit/19cb3c41e6ab42e1f140f8d8c98b1bf5a4d45c89))
* **ingestion:** add employer greenhouse pipeline and unify policy/audit model handling ([3518926](https://github.com/aergaroth/openjobseu/commit/351892655a84d4b7bd612f0dcdabeb23ecd2a54c))
* **ingestion:** add RemoteOK ingestion with standalone normalization ([c77e562](https://github.com/aergaroth/openjobseu/commit/c77e562a85d2800b990ad11460a4d965ed422ce7))
* **ingestion:** add stable job identity and policy version tracking ([f8a3b77](https://github.com/aergaroth/openjobseu/commit/f8a3b77551c804a0b4972c5b08ca17b5c9b05040))
* **ingestion:** fetch multiple WeWorkRemotely RSS categories with dedup ([6adadd6](https://github.com/aergaroth/openjobseu/commit/6adadd62e5b3c1b86c82f3633885aa58d036d173))
* **ingestion:** implement incremental ATS sync with last_sync_at tracking ([135f328](https://github.com/aergaroth/openjobseu/commit/135f328ffca34f0a898ebdd906606b7d09f179af))
* integrate dorking discovery into pipeline and add Google Secret Manager for API keys ([209866f](https://github.com/aergaroth/openjobseu/commit/209866f62588420aef37ae7e0e3137f7e3873e39))
* introduce geo_classifier v3 and shadow_employer_compliance_script ([482320f](https://github.com/aergaroth/openjobseu/commit/482320ffdf45ff8ddbf55bf758b31ec6ebe9cb5d))
* Introduce spam pattern detection in HTML cleaning utility ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* introduce tick worker skeleton for scheduled processing ([cbd4256](https://github.com/aergaroth/openjobseu/commit/cbd425640d8f4ceb150935a46309d9d4e7a619d9))
* **logging:** structured tick metrics and per-source ingestion summaries ([bfb20b5](https://github.com/aergaroth/openjobseu/commit/bfb20b506e8ad357c0bb4d4568cc3afc9e089ee4))
* **logging:** update JsonLogFormatter to use 'severity' and handle serialization errors gracefully ([bda56af](https://github.com/aergaroth/openjobseu/commit/bda56afb43b83972b2fc55ebce34a11613fe000f))
* **main:** enhance CORS configuration and add security headers middleware ([bda56af](https://github.com/aergaroth/openjobseu/commit/bda56afb43b83972b2fc55ebce34a11613fe000f))
* migrate storage from SQLite to PostgreSQL (Neon) + stabilize Cloud Run runtime ([0cc11fa](https://github.com/aergaroth/openjobseu/commit/0cc11fa82b83f72a31833ae29e409a8b51e62958))
* move employer ingestion to v3 policy, turn off weworkremotely and remoteok sources (paywalls) ([173b94a](https://github.com/aergaroth/openjobseu/commit/173b94afd6fae259c866546e1b8e9faaa5a7fb63))
* **normalization:** add Remotive job normalizer and tests ([460aa8f](https://github.com/aergaroth/openjobseu/commit/460aa8f16eaa0e097a2482ac204b8215919da8d1))
* **normalization:** add WeWorkRemotely normalizer and tests ([2fb982b](https://github.com/aergaroth/openjobseu/commit/2fb982bf37d67250c950fbac6eebca45bd2deefa))
* **observability:** policy audit log + improved Cloud Run log clarity ([ac2ff11](https://github.com/aergaroth/openjobseu/commit/ac2ff117ca54635210506deb23a5e2ee54d8f0e2))
* **observability:** policy reason metrics + structured tick output ([0a2556a](https://github.com/aergaroth/openjobseu/commit/0a2556a1dede3cde1dab81db02f68cd5e5ec6d74))
* optimize compliance score query and add feed optimal index ([f27ecc0](https://github.com/aergaroth/openjobseu/commit/f27ecc0b486295b6e49c7bfa4ac7421c18bd34d6))
* **pipeline:** persist policy flags and add compliance resolution step ([f83dd1d](https://github.com/aergaroth/openjobseu/commit/f83dd1d98c07dc645cf24d66a2f943ac9abe607c))
* **policy-v2:** add deterministic geo classifier and geo signal data ([375c488](https://github.com/aergaroth/openjobseu/commit/375c48885a277025964bd91d5dcff1366c519c01))
* **policy-v2:** introduce remote classifier and metrics wiring ([2fcecb9](https://github.com/aergaroth/openjobseu/commit/2fcecb9f759a250cba393ca4adc2fc67965e7833))
* **policy:** introduce policy v1 and global enforcement (remote purity + geo restrictions) ([fee8e3f](https://github.com/aergaroth/openjobseu/commit/fee8e3fed792de048fbb2f0472bc70af6afb59e7))
* refactor employer ingestion process with modular functions and enhanced metrics tracking ([9100545](https://github.com/aergaroth/openjobseu/commit/9100545a73643c76c37e9754350f20c0429c4726))
* refactor ingestion logic by removing legacy adapters and scripts, and enhance local job loading functionality ([acaf7fc](https://github.com/aergaroth/openjobseu/commit/acaf7fcf30e9a9b71ba083443490acd7e5ac8ace))
* Refactor job lifecycle and availability status ([2716301](https://github.com/aergaroth/openjobseu/commit/27163015dc3e23c5993678d7c78bf5a4df0fd6f8))
* Refactor salary extraction logic and introduce currency handling ([741f2b3](https://github.com/aergaroth/openjobseu/commit/741f2b333e89b1e6881ad84e1450ac3de6b2b2dc))
* Refactor task management and introduce frontend export functionality ([9e95c8d](https://github.com/aergaroth/openjobseu/commit/9e95c8d4d17fe94b44df89b0ff35b2da00163ec7))
* release OpenJobsEU 2.0 with modular ATS/compliance refactor ([a450632](https://github.com/aergaroth/openjobseu/commit/a450632d7ed7aa62ebb26cd8ac93895980922100))
* remove most literals from runtime to domain defined ([7fcfdc1](https://github.com/aergaroth/openjobseu/commit/7fcfdc122840d87f5d86c68e3ccc9f2fd2bd20d6))
* Rename columns in salary_parsing_cases for clarity and consistency ([fe2d81d](https://github.com/aergaroth/openjobseu/commit/fe2d81d4e8bbf8c6497e3225bf408cfc70471998))
* **runtime:** extend ingestion pipeline with additional source ([71599f4](https://github.com/aergaroth/openjobseu/commit/71599f4e94d6504f0a4d39dfbf783156b8a5d9e8))
* **runtime:** migrate OpenJobsEU from SQLite to PostgreSQL ([d7ce5e9](https://github.com/aergaroth/openjobseu/commit/d7ce5e9417448b7a594abe96bc916b0fb9daad05))
* **snapshot:** add job snapshots table and implement snapshotting on job updates ([856acaa](https://github.com/aergaroth/openjobseu/commit/856acaa52f2d0a0cb8c23f1841707a78796175e4))
* **storage:** derive/persist remote+geo classes and bootstrap missing compliance ([66dabb3](https://github.com/aergaroth/openjobseu/commit/66dabb309d2d3f332dc588443683f0e2832c2bc4))
* **storage:** migrate storage layer from SQLite to PostgreSQL ([6a9b616](https://github.com/aergaroth/openjobseu/commit/6a9b6163ae2d8be21fd6f4e0381840ae75cd0900))
* **taxonomy:** implement job taxonomy classification and quality scoring ([66409a7](https://github.com/aergaroth/openjobseu/commit/66409a7c7dcd4f7988d415c6954011cd9fa62c6d))
* **tests:** enhance test coverage and structure across various modules ([388e039](https://github.com/aergaroth/openjobseu/commit/388e039ab7b59452b019bf1df05f632d9cc21698))
* **tick-dev:** add authorization header for gcloud commands and improve error handling ([510040a](https://github.com/aergaroth/openjobseu/commit/510040a2af02993b51959377bbcbd7d689db557e))
* update access requirements for discovery and backfill endpoints ([fd50a50](https://github.com/aergaroth/openjobseu/commit/fd50a50089d769c4a1e334bdefb43fba43e9cbd6))
* update normalize function to accept Any type and ensure string conversion ([4f2106f](https://github.com/aergaroth/openjobseu/commit/4f2106f55ef62f709fd38a84b4d4ae28d9c66daf))
* use BASE_URL environment variable for tick handler URL construction ([3d9ec13](https://github.com/aergaroth/openjobseu/commit/3d9ec13b82263ea54da4fc5d2aeaf2f3ea3747bc))


### Bug Fixes

* add IF NOT EXISTS to ALTER TABLE and CREATE INDEX statements in migration scripts ([af1d63f](https://github.com/aergaroth/openjobseu/commit/af1d63f4978ac9f8c7c88886e672bf6a2b69bdae))
* add missing token for PR in release-please.yml ([083a039](https://github.com/aergaroth/openjobseu/commit/083a0399d0102e9d639d6aaf40185870f3e7566c))
* add target-branch to release-please.yml and define project metadata in pyproject.toml ([a111fe6](https://github.com/aergaroth/openjobseu/commit/a111fe62be8991b8e302257ba94804a1ee927c31))
* added required envs ([8c33335](https://github.com/aergaroth/openjobseu/commit/8c3333565be4a1ddb5a2cef7a9a583093c1f1322))
* **alembic:** safely enable pg_trgm extension with error handling for permissions ([bda56af](https://github.com/aergaroth/openjobseu/commit/bda56afb43b83972b2fc55ebce34a11613fe000f))
* align image tagging between build and Cloud Run deploy ([4a8816f](https://github.com/aergaroth/openjobseu/commit/4a8816f2e283fc6dbf8786eeca8ef8a6610a011b))
* **api:** imports after use ([fdbe873](https://github.com/aergaroth/openjobseu/commit/fdbe8736e3da7c3c8a38d28fbc7cb86d2a307a01))
* **api:** register CORS middleware after app initialization ([f096a74](https://github.com/aergaroth/openjobseu/commit/f096a741785e7dad6cbb9377343ab2a9aedc9dd9))
* **auth:** refine OAuth scope to include only 'openid' and 'email' ([bda56af](https://github.com/aergaroth/openjobseu/commit/bda56afb43b83972b2fc55ebce34a11613fe000f))
* change old (v2) remote mappings ([48eceb2](https://github.com/aergaroth/openjobseu/commit/48eceb250ea3bba24ba48d3b3555aaf6c72ed7be))
* change remote mappings ([4548a72](https://github.com/aergaroth/openjobseu/commit/4548a72d305e1c8b92327fdccf6bebda2f99302a))
* cleanup actions in logs - remove unused from post_ingestion ([667a4f2](https://github.com/aergaroth/openjobseu/commit/667a4f26534d7b39ccffbd9807a40c927e895c7d))
* **cloudrun:** keep listener up while DB bootstrap retries in background ([473ea90](https://github.com/aergaroth/openjobseu/commit/473ea90b500e852839d7172c4cf9d52318144e7b))
* correct dict unpacking in scheduler tick response ([f460b7a](https://github.com/aergaroth/openjobseu/commit/f460b7adce9e8e240fa40cc3581446feb5858196))
* Correct indentation in ATSAdapter constructor and update session headers ([810ea27](https://github.com/aergaroth/openjobseu/commit/810ea27e8a7cefcdc8e35f1bf3453358bc6a2305))
* correct runtime dependencies in requirements ([e80a9dd](https://github.com/aergaroth/openjobseu/commit/e80a9ddec8fb758609070a1e8b34e905c3fef759))
* corrected bucket name ([d6828fd](https://github.com/aergaroth/openjobseu/commit/d6828fd47fa019b1f9266cfeb3c441951dc0ecf8))
* corrected bucket name, after tests ([f19f0fe](https://github.com/aergaroth/openjobseu/commit/f19f0fe00747a3acca8cf625ab188400e07d1f0f))
* **cors:** enable OPTIONS method for public feed ([c8b8e86](https://github.com/aergaroth/openjobseu/commit/c8b8e8681e052e0fd4c3ce0a658709885e7b0474))
* debuging for GCP secrets ([60572c0](https://github.com/aergaroth/openjobseu/commit/60572c03e6d437b91e7bcb6aa5acb8edccf22701))
* disable SSL warnings and update requests to ignore certificate verification ([30943e1](https://github.com/aergaroth/openjobseu/commit/30943e19badb7cdbfae364426ce479929ea52f1d))
* enforce text response format for tick-dev endpoint ([1cf6350](https://github.com/aergaroth/openjobseu/commit/1cf63508a26575191effbcf13b885925d8c08a47))
* ensure ALTER TABLE statements check for existence of job_snapshots ([365676d](https://github.com/aergaroth/openjobseu/commit/365676da4ca5e3e68b387a377572e28ed54fc07e))
* ensure ALTER TABLE statements check for existence of job_snapshots ([14636b3](https://github.com/aergaroth/openjobseu/commit/14636b3422f0cd6bc7a8b9079e95233ae9961e85))
* **frontend:** align feed preview with public jobs/feed v1 contract ([f84cb4e](https://github.com/aergaroth/openjobseu/commit/f84cb4ec6827e52e9ee494c767964d88ad9a467d))
* **frontend:** correct feed JSON contract ([b7fcde3](https://github.com/aergaroth/openjobseu/commit/b7fcde35dfa9738717a19dd53176fc658f021fb9))
* **frontend:** move inline styles to external stylesheet (CSP-safe) ([a98ea17](https://github.com/aergaroth/openjobseu/commit/a98ea178765dc8c339604f6b2cccf7319caebefb))
* handle millisecond timestamps in normalize_source_datetime function ([4dfa4f0](https://github.com/aergaroth/openjobseu/commit/4dfa4f09a793b15e805e5fd280e2cca66f7ca9eb))
* handle response types in run_tick_from_audit endpoint ([ffa7631](https://github.com/aergaroth/openjobseu/commit/ffa763145e4e24b514f2ff60adc4d9a5117776c4))
* import DB helpers in availability and lifecycle pipelines ([c867e87](https://github.com/aergaroth/openjobseu/commit/c867e87c2b5990276df07b84afda302e28bc3957))
* increase memory limit for Cloud Run service to 1024Mi and remove unused merge.py file ([492b4b1](https://github.com/aergaroth/openjobseu/commit/492b4b1a7be771b8d597d29d4b6c843b0884a6ed))
* indentation int tick.py ([43c75af](https://github.com/aergaroth/openjobseu/commit/43c75afd8dbfdf086cc69c4c626b25dd8479498e))
* **ingestion:** align RemoteOkApiAdapter class name with imports ([b8c5e21](https://github.com/aergaroth/openjobseu/commit/b8c5e21787813c7650fbaa51dedc81216642ce3d))
* **ingestion:** Log unhandled exceptions during employer ingestion ([aa6ab85](https://github.com/aergaroth/openjobseu/commit/aa6ab85c4cd37f1474f037203216d659178df9a8))
* initialize db before tests ([fce9f9b](https://github.com/aergaroth/openjobseu/commit/fce9f9b2879e39d1ff2513393b3b9f7d21692141))
* **logging:** standardize logger name in backfill compliance and salary modules ([e3eddc2](https://github.com/aergaroth/openjobseu/commit/e3eddc22ba41d9a164c475feb7902063b7153e31))
* **logging:** update json formatter test to assert 'severity' instead of 'level' ([0c79e2b](https://github.com/aergaroth/openjobseu/commit/0c79e2bc2400b0bd26433c5b68e2f38da13b7492))
* make ttl-based stale status effective in availability checker ([a833344](https://github.com/aergaroth/openjobseu/commit/a833344bbd3a61800b08c11282d615cdbebb7e70))
* **migrations:** remove pgcrypto dependency for Neon compatibility ([772a930](https://github.com/aergaroth/openjobseu/commit/772a93032ab3b419be886ea97c54c6d4aba9b5f5))
* missed collon in internal.py ([a79a807](https://github.com/aergaroth/openjobseu/commit/a79a80776811daa0617be1e385c0026e33c4371c))
* missing requirements ([0145258](https://github.com/aergaroth/openjobseu/commit/0145258d9ad6357b9d47de85dd4637b5d8f90076))
* move normalization to valid layer and added test to avoid messing normalization with adapters ([994116e](https://github.com/aergaroth/openjobseu/commit/994116e4e09d60f62604c5f038071120c937cc78))
* move service_account to templane for newer provider ([67b056d](https://github.com/aergaroth/openjobseu/commit/67b056dbf8afede54081994921c47e3e064cd306))
* moved RSS_URL from worker to adapter ([d00ef38](https://github.com/aergaroth/openjobseu/commit/d00ef384b79088f20ff27b0901ffa707aa5f013e))
* **policy:** adjust geo detection + harden feed audit script ([b8eb53a](https://github.com/aergaroth/openjobseu/commit/b8eb53aa28d2e3d27ec68baf1e4281f32d3c7cf8))
* provide TF_VARS for workflow ([097a242](https://github.com/aergaroth/openjobseu/commit/097a2425914d36c306c18a6c9e71e23808d718ea))
* refactor import statements and enhance test coverage for maintenance pipeline ([b464344](https://github.com/aergaroth/openjobseu/commit/b4643448c563588c2818531a2ed44ba45a46528e))
* remove old (unused) helper ([660391c](https://github.com/aergaroth/openjobseu/commit/660391c2508122b5cf8a8f51162677da7023b95b))
* remove unused taskName extra field from logs ([6a0027a](https://github.com/aergaroth/openjobseu/commit/6a0027a8276826dfb69b97af825b9c7fdb368bc6))
* removed post_ingestion() call arg. - refactored previously ([7293e39](https://github.com/aergaroth/openjobseu/commit/7293e398fdfb46f403ebb78d5be6722180621440))
* renamed field in DB in exmaple test ([6fc8398](https://github.com/aergaroth/openjobseu/commit/6fc8398d660cede5c7fcf4fef3624c2c24f21279))
* resolve cron storm, UI FOUC, and CI validation errors ([0f50273](https://github.com/aergaroth/openjobseu/commit/0f50273ef0d77f8965cb29909000ba5ee0286b36))
* **salary_extraction, db_migration:** Correct salary max calculation and update salary field types ([c4332c0](https://github.com/aergaroth/openjobseu/commit/c4332c023062a54e73b681aace43771f26d5c1c2))
* secure ingestion worker, check if compliance is initiated before apply, secure policy engine ([6f99079](https://github.com/aergaroth/openjobseu/commit/6f99079c11c86c5808c8d023da60f1e6c948fc5a))
* **startup:** fail fast when DB bootstrap or migrations fail ([8a94e73](https://github.com/aergaroth/openjobseu/commit/8a94e73777521a0532caf085356b9339cadee740))
* **storage:** initialize sqlite schema on app startup ([7cb0f13](https://github.com/aergaroth/openjobseu/commit/7cb0f13d852ca15ae411110d857e7877abb3db1b))
* **storage:** resolve sqlite db path at runtime to fix CI tests ([0e916dd](https://github.com/aergaroth/openjobseu/commit/0e916ddb263c146efc43f7bacbbf16cafcda1edd))
* **tests:** update ingestion mock to return adapter instance ([bf59f87](https://github.com/aergaroth/openjobseu/commit/bf59f870d40f132ce6b7f4ec1dc718a121f01603))
* tick orchestration: ([7f65db5](https://github.com/aergaroth/openjobseu/commit/7f65db5a1d107f0be3ae901b7182bed5edd636a2))
* tick-dev.sh script could be run in other shell than bash ([3b62888](https://github.com/aergaroth/openjobseu/commit/3b628886971adcdd57648b353025827932cf3e9a))
* **tick:** render source metrics for flat ingestion payload format ([483db24](https://github.com/aergaroth/openjobseu/commit/483db24f48a307b2e64f65017ead07a8ba3e2ba0))
* typo - space afer backslash ([4095e58](https://github.com/aergaroth/openjobseu/commit/4095e583c44474ba30270fe154ba58a060c827e3))
* typo - space afer backslash ([219554c](https://github.com/aergaroth/openjobseu/commit/219554c04fe4ec470064d00d49b70b40829b35c3))
* typo in requirements.txt ([b51dc40](https://github.com/aergaroth/openjobseu/commit/b51dc409ad82ae900289b97e8062f75c429e5e62))
* update Alembic stamp revision to specific commit for database migration ([9e9b702](https://github.com/aergaroth/openjobseu/commit/9e9b702a42128512ff88613dd380bd1a07b94919))
* update Alembic stamp revision to specific commit for database migration ([147839e](https://github.com/aergaroth/openjobseu/commit/147839eb4f4e8a973d2d036c53d502283c8a4447))
* update branch from main to develop in release-please.yml and add release-please manifest ([574d557](https://github.com/aergaroth/openjobseu/commit/574d55717680ec781202191ff0776bcbf5d7e0ff))
* update comment in Dockerfile ([9f3a482](https://github.com/aergaroth/openjobseu/commit/9f3a4828d0cb5d708737d23470b002be23fcdd61))
* update commit-check workflow to validate commit messages using Commitizen ([ec4c5fa](https://github.com/aergaroth/openjobseu/commit/ec4c5fa0562597426d7a38f6182af5a2b08ed1fb))
* update conditional for build-deploy-dev job to exclude main branch in pull requests ([5ed063a](https://github.com/aergaroth/openjobseu/commit/5ed063a7141309386339a2dd6b5ac3ba86c01e2b))
* update job processing to handle rejected jobs and adjust compliance reporting ([625f230](https://github.com/aergaroth/openjobseu/commit/625f230a161a1ba290a2137feb774fae39987c98))
* update missing logg info for employer ingestion ([5af2e1e](https://github.com/aergaroth/openjobseu/commit/5af2e1e2e730ee9ea0d38aedfbeec0bdc1feffc5))
* update pull request conditions for dev and prod workflows to improve branch handling ([e82f2e0](https://github.com/aergaroth/openjobseu/commit/e82f2e04a1b22d1f2ad74c539bdd9df97fe4e38c))
* Update README badge and refactor ATSAdapter for requests session ([8ab5239](https://github.com/aergaroth/openjobseu/commit/8ab523927237ed6312fc1d71533df0f497f4d71a))


### Documentation

* add ci status badge ([8f34612](https://github.com/aergaroth/openjobseu/commit/8f346120895479bb67ccebd993accff00252e6d6))
* add content quality & policy v1 milestone to roadmap ([f9fb2c1](https://github.com/aergaroth/openjobseu/commit/f9fb2c1df7f220428ddd6bc4aa6a4c23bf9aa1b7))
* add system architecture and design rationale ([0440aaa](https://github.com/aergaroth/openjobseu/commit/0440aaabcb34532a9b6d4ae1c018e78abf524029))
* added hint in ARCHITECTURE.md ([1bb8df1](https://github.com/aergaroth/openjobseu/commit/1bb8df1785db22e07f21a25c4981234959de8c25))
* added short hit for Terraform .tfvars file ([c2d45a6](https://github.com/aergaroth/openjobseu/commit/c2d45a62dc3bf22b4be295a834020e576f47ff09))
* added site url ([c7195da](https://github.com/aergaroth/openjobseu/commit/c7195dadefc906d87865695e86be3a320edc70aa))
* align project documentation with current MVP implementation ([24edc13](https://github.com/aergaroth/openjobseu/commit/24edc13f737a641f968f600730abe8eed5972890))
* canonical model to match current state ([599e7ce](https://github.com/aergaroth/openjobseu/commit/599e7ce5a434de843d40890aa606d33d3dbfad66))
* clarify procject direction ([f8c682a](https://github.com/aergaroth/openjobseu/commit/f8c682a2f36d934d03afe6842c1482df9b0894e8))
* clean up roadmap after MVP v1 completion ([ba7ba32](https://github.com/aergaroth/openjobseu/commit/ba7ba3259feb6ede5ca67c4e30f9fc2b57bd3471))
* current state in ROADMAP ([3b671fd](https://github.com/aergaroth/openjobseu/commit/3b671fd795ab869bf4de85a4f1a875e1c7a5df05))
* define canonical job model and lifecycle ([9726adf](https://github.com/aergaroth/openjobseu/commit/9726adf235c02ec15e26fa62fbf676d6e9b91771))
* edit architecture, to match the current state ([9225fd7](https://github.com/aergaroth/openjobseu/commit/9225fd7603601d60383426c80bc288be51fa834e))
* Example source information ([25d83df](https://github.com/aergaroth/openjobseu/commit/25d83df202a74c0f2ed546483c29dda7c68e6866))
* fix badge to point to prod environment ([47dbe9f](https://github.com/aergaroth/openjobseu/commit/47dbe9fcb90b127786614f7e840f054af35dc643))
* fix typo ([9aa9fe0](https://github.com/aergaroth/openjobseu/commit/9aa9fe06e90078e393bf7cfc5006c89b12876efd))
* refresh ROADMAP ([9612da5](https://github.com/aergaroth/openjobseu/commit/9612da50931cb25e16dc7f0b23e6c52e0b1ec216))
* resize architecture diagram ([5f34b03](https://github.com/aergaroth/openjobseu/commit/5f34b03a396862ff724eb5ac0e87488d9edcd055))
* sync documentation with current runtime ([351c28c](https://github.com/aergaroth/openjobseu/commit/351c28c89690be06ef0423e1d47e9e2dc7c3378c))
* synchronize architecture, system map and roadmap ([5a33fda](https://github.com/aergaroth/openjobseu/commit/5a33fda1a7b24d280793020ded4263df97b7dc3d))
* update architecture diagram API naming ([2850311](https://github.com/aergaroth/openjobseu/commit/28503113650a5de2a44dd2b77bcf756fe2575fc1))
* Update architecture documentation to reflect new internal endpoint parameters ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* update documentation to match current state ([d543e42](https://github.com/aergaroth/openjobseu/commit/d543e422c86cd4df9fc1107f299532cafa7360f8))
* Update documentation to match the current state of project. ([4c50ade](https://github.com/aergaroth/openjobseu/commit/4c50ade91aa089288af1534492ea16f6e26042a1))
* update README and roadmap after A7 completion ([e5dc640](https://github.com/aergaroth/openjobseu/commit/e5dc64083dc881740c4aced5a7ba38bd1f0885a6))
* update README and roadmap after lifecycle and read API ([ee303d5](https://github.com/aergaroth/openjobseu/commit/ee303d58a2a1fec5667827d2520a06a44751fff5))
* update README with current architecture and ingestion flow ([6b04008](https://github.com/aergaroth/openjobseu/commit/6b04008d436dcff1caa8680585e0807cd73bdf0e))
* update README, ARCHITECTURE, CANONICAL_MODEL, COMPLIANCE, DATA_SOURCES, and ROADMAP for clarity and consistency ([679999f](https://github.com/aergaroth/openjobseu/commit/679999f6741706f39e2e7edb935d51417ee32e6c))

## [1.0.0](https://github.com/aergaroth/openjobseu/compare/v0.3.0...v1.0.0) (2026-03-22)


### ⚠ BREAKING CHANGES

* legacy adapters, v2/v3 policy modules, and old normalization worker paths were removed in favor of the new OpenJobsEU 2.0 structure.

### Features

* **a6.1:** extract company name from RSS titles when missing ([92c7140](https://github.com/aergaroth/openjobseu/commit/92c7140cc2a4dbb56997f5c10859beb0a681bed5))
* add advanced filtering to jobs read API ([e53af30](https://github.com/aergaroth/openjobseu/commit/e53af3008ff8d8247b27477f08c7a891d678e90e))
* add audit companies endpoint with filters ([3641e86](https://github.com/aergaroth/openjobseu/commit/3641e86b00ada6394cb8d4e12db40b849f6f552c))
* add availability checker with ttl-based status transitions ([dec1d80](https://github.com/aergaroth/openjobseu/commit/dec1d806fceb25ada3d160ee9d606895dde177c4))
* add availability checking to rss tick worker ([7c2426d](https://github.com/aergaroth/openjobseu/commit/7c2426d4592cc057d9a14af8cfb1ba3898ea747f))
* add BASE_URL environment variable and update OIDC audience in Cloud Scheduler jobs ([e148170](https://github.com/aergaroth/openjobseu/commit/e1481701e76afaffa3b625ffc515b1001cd1d847))
* add canonical job ID computation and related database updates for job reposting ([af5d92f](https://github.com/aergaroth/openjobseu/commit/af5d92f34a6e7e3f70a34ab8270fb2b3671c23da))
* add CHANGELOG and protect_develop workflow ([f41f296](https://github.com/aergaroth/openjobseu/commit/f41f296b8d7929e26a19fb6a542c96da15743dee))
* add commit message validation workflow using Commitizen ([27113c9](https://github.com/aergaroth/openjobseu/commit/27113c93e373c2bca08059a047f46bd22460e0f4))
* Add companies API endpoint and enhance discovery processes ([47a9289](https://github.com/aergaroth/openjobseu/commit/47a92896bce73b64629be0f1eb93b3f4285472ae))
* add compliance backfill script and fix JSON serialization in DB logic ([51203bb](https://github.com/aergaroth/openjobseu/commit/51203bbff010b46afce6adab86acaed3d356b4b4))
* add compliance score and status to policy application logic ([0f7239e](https://github.com/aergaroth/openjobseu/commit/0f7239e6eafa3043f694d1b32f4d74c117e82a35))
* add compliance stats endpoints and update frontend to display 7-day compliance metricsupdate audit_tool and api for compliance statistics ([adf5fc3](https://github.com/aergaroth/openjobseu/commit/adf5fc31a6bf74a507230d082326d0eced98d983))
* add docker-compose for local development workflow ([d03964c](https://github.com/aergaroth/openjobseu/commit/d03964c8b0c2c2c1e1fd60e9467b3da41d747f1c))
* add dockerfile for reproducible test environment ([908aa48](https://github.com/aergaroth/openjobseu/commit/908aa48378b776fb26fb0f932e3a865776915325))
* add example ingestion source with normalization and tests ([cf13d87](https://github.com/aergaroth/openjobseu/commit/cf13d87b8dcca27d2394c1366b2e299500592b6b))
* Add full sync script for tick endpoint with retry mechanism ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* add geo_data module and enhance remote signals with new options ([831b12d](https://github.com/aergaroth/openjobseu/commit/831b12d4ac4a8fc68403e1a607444f21d81a1fbe))
* add geo_data module and enhance remote signals with new options ([fd15599](https://github.com/aergaroth/openjobseu/commit/fd15599d4d09ba6aa4b5b6c7911a6862aa29f05c))
* add Google OAuth secrets and allowed email configuration to Terraform apply ([df097b6](https://github.com/aergaroth/openjobseu/commit/df097b6dd790bfa64ea79c21b6d04f48b9055d07))
* add Google Secret Manager resources for API keys and update variables for Google API key and CSE ID ([e98c1d0](https://github.com/aergaroth/openjobseu/commit/e98c1d07212c4b8fc12c47a2fe8a604ab1c99a5b))
* add IF NOT EXISTS clause to job taxonomy and dataset indexes ([012dcf5](https://github.com/aergaroth/openjobseu/commit/012dcf5efd4e8c13302ab6c996fdeacd755bddbb))
* add initial migration for job indexes ([bea6288](https://github.com/aergaroth/openjobseu/commit/bea6288120861952f20537b848f532724fee7d3e))
* add job preview endpoint and enhance audit panel with new features ([18a20fc](https://github.com/aergaroth/openjobseu/commit/18a20fc86281dd3cc5451af6c4e1198e93091d0a))
* add lifecycle rules for job expiration ([b00dce2](https://github.com/aergaroth/openjobseu/commit/b00dce21fbaa8c530878fe19cc22a4fef4ef9b2c))
* Add limit parameter to internal tick endpoint for controlled processing ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* add minimal runtime with health endpoints ([0b3ae4e](https://github.com/aergaroth/openjobseu/commit/0b3ae4e31f7f10ca078de59819a496a981e0bd84))
* add minimal runtime with health endpoints ([9ee481a](https://github.com/aergaroth/openjobseu/commit/9ee481a390cc82b9df032b46b3b1f4d726d11369))
* add non-EU classification logic and corresponding tests for geo_v3 ([cc50627](https://github.com/aergaroth/openjobseu/commit/cc50627449cc1b5da2b0046264400bd5ae3db165))
* add performance timing to careers discovery process ([cfe4eec](https://github.com/aergaroth/openjobseu/commit/cfe4eec7b76eadaacd4a83e8af217a5e0d84fbef))
* add Personio and Recruitee adapters for job fetching and processing ([b9f4ab1](https://github.com/aergaroth/openjobseu/commit/b9f4ab1305b0cddfa21eed89383e80c51c594981))
* add planned features section to roadmap with dataset API and analytics ([837e5b1](https://github.com/aergaroth/openjobseu/commit/837e5b1441513c9835d269339a3ad3de5aa3216b))
* add rss ingestion with dev-only local fallback ([a2a36cc](https://github.com/aergaroth/openjobseu/commit/a2a36cc990cee37ccf4a382aa247b56f4dbf1a7b))
* add salary backfill endpoint and refactor audit registry ([508b5f0](https://github.com/aergaroth/openjobseu/commit/508b5f05de4f06537078f4a4c17bc649fb4519e3))
* add scheduler heartbeat and internal tick endpoint ([b4109f1](https://github.com/aergaroth/openjobseu/commit/b4109f1b5026d4e25b44bee6fb71b3b83e16eec9))
* add scheduler heartbeat and runtime tick endpoint ([8c7fd10](https://github.com/aergaroth/openjobseu/commit/8c7fd10a772997ce972a3df5ff92af4a36aafa7c))
* add sqlite persistence for ingested jobs ([4d36a25](https://github.com/aergaroth/openjobseu/commit/4d36a25087cc82192e2c4e03cc0b38f512581b9c))
* add test for rejected job not inserting compliance report without job ID ([08e4d7f](https://github.com/aergaroth/openjobseu/commit/08e4d7f6e1b2f849db4b9c0cde4c0e7f2261727b))
* add unit tests for job fetching and lifecycle pipeline execution ([6994cc8](https://github.com/aergaroth/openjobseu/commit/6994cc854c302df97e1221b84469c2e2b8f1e875))
* added example test and __init__.py for modules ([6bacb89](https://github.com/aergaroth/openjobseu/commit/6bacb8957ec6a2a366fefca672c51b4fce66f07f))
* added simple frontend ([e21c418](https://github.com/aergaroth/openjobseu/commit/e21c418e1e5388f53e12676690df9d4bf347398c))
* **api:** add public /jobs/feed ([b57c40b](https://github.com/aergaroth/openjobseu/commit/b57c40bab51a62afbd9efdfd22e7c2e00ecab264))
* **api:** filter feed by minimum compliance score ([83e9636](https://github.com/aergaroth/openjobseu/commit/83e96364e9315089cd69cb7fe109bfe82ebc25b3))
* **ats/greenhouse:** add INCREMENTAL_FETCH control to adapter ([9809812](https://github.com/aergaroth/openjobseu/commit/980981256687dd1f0727fb75c75bd27ea0ef2162))
* **ats:** standardize adapter interfaces and add registry registration ([ecd148b](https://github.com/aergaroth/openjobseu/commit/ecd148b9626e786d215b62f498ed21d72fd73adf))
* **ats:** standardize adapter interfaces and add registry registration ([cb9f129](https://github.com/aergaroth/openjobseu/commit/cb9f129bd7f0eeef705dca65b8d1e9ad03921b16))
* **audit panel:** add cached static endpoints and ATS actions ([b292d11](https://github.com/aergaroth/openjobseu/commit/b292d111bd4746b0fe09a251d9ddc446f1eef2c6))
* **audit:** add safeLoadAtsHealth to async data loading ([69a4a61](https://github.com/aergaroth/openjobseu/commit/69a4a61162a3ae4ee496020b1d266ecd3f48fa8c))
* **audit:** rename Offer Audit Panel to Admin Audit Panel and add new backfill options ([848fc46](https://github.com/aergaroth/openjobseu/commit/848fc46e301269acce5873f815c373d6f41458ed))
* **audit:** update test to reflect renaming of Offer Audit Panel to Admin Audit Panel ([77df720](https://github.com/aergaroth/openjobseu/commit/77df720fd133c07708b51a6aab0a3e10a50d8536))
* **auth:** add email whitelist and improve OAuth configuration handling ([6109dbd](https://github.com/aergaroth/openjobseu/commit/6109dbdddbcae11b08275a453aeaa694afffebb1))
* **careers_crawler:** Update to use requests.Response type and explicit URL/text extraction ([6f640a4](https://github.com/aergaroth/openjobseu/commit/6f640a4e4f182fc9e71db052c0cf0e33dc2f3268))
* **careers_crawler:** Update to use requests.Response type and explicit URL/text extraction ([6c6faa3](https://github.com/aergaroth/openjobseu/commit/6c6faa3ddb4bb8fa69888dbddd0cd22af542437d))
* changed tick formatting, added metrics for employer ingestion, update docs ([48b20c9](https://github.com/aergaroth/openjobseu/commit/48b20c95a47a85c0ceb219ee6ef593e6c15d6fb0))
* complete compliance resolution in ingestion and populate compliance_reports table ([a14aa68](https://github.com/aergaroth/openjobseu/commit/a14aa6810c429490a9fe6dfe4a2c3e231b8fe008))
* compliance decision trace, unique reports and backfill script ([0cf16a7](https://github.com/aergaroth/openjobseu/commit/0cf16a7fa4e65f61e9eabec71ca39a5666816c9f))
* **compliance:** replace resolver with normalized decision matrix ([573f44b](https://github.com/aergaroth/openjobseu/commit/573f44ba65d7cc191de6eb2f7a7102b110580f80))
* **compliance:** update remote class normalization and scoring logic ([4a05705](https://github.com/aergaroth/openjobseu/commit/4a057055b5d42acdd1957f72f63360551a783f81))
* conditionally persist compliance report for canonical jobs only ([10a3c37](https://github.com/aergaroth/openjobseu/commit/10a3c37ba411c7738e6642d2c6e5cc8b85c830ac))
* consolidate architecture documentation and add system map ([1ba215a](https://github.com/aergaroth/openjobseu/commit/1ba215af856b158cd082c2a24393e7c3dcfa877e))
* Create scripts for auditing HTML leftovers and description sanity checks ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* decouple Cloud Tasks handlers and implement time-budgeting ([749152b](https://github.com/aergaroth/openjobseu/commit/749152b022fdb8c4ea388bcd847ad1bc75ff5f67))
* **discovery:** enhance error handling in probe_ats function ([e00f971](https://github.com/aergaroth/openjobseu/commit/e00f97127b5323de2640c9e020ad8fd0a230e280))
* Enable incremental fetch for Greenhouse adapter and refine job enrichment logic based on compliance status ([10fac4c](https://github.com/aergaroth/openjobseu/commit/10fac4c86ac4cdc7a5ad9aaaf8d6c39727117fc1))
* enhance ATS adapters, discovery pipeline, and secure Audit UI ([4bc467b](https://github.com/aergaroth/openjobseu/commit/4bc467bbafcc7770c4fdbc407c78e1e641915220))
* enhance ATS adapters, discovery pipeline, and secure Audit UI ([8039b2c](https://github.com/aergaroth/openjobseu/commit/8039b2c90167a32837ea775e92e4fa04c6afcd61))
* Enhance ATS ingestion and canonical model with taxonomy ([55f64ef](https://github.com/aergaroth/openjobseu/commit/55f64ef38f4a20a70c9889174a5e7c69d9b075c2))
* enhance ATS integration with batching and sync status updates ([1567d2d](https://github.com/aergaroth/openjobseu/commit/1567d2d2f44bb0a1c0059c9ff1a70e90f9239b7c))
* enhance discovery pipeline with new metrics and update filtering logic ([190722f](https://github.com/aergaroth/openjobseu/commit/190722fcbc0a7294e3a3eb2d13641afb89d5ebcc))
* enhance discovery processes and improve Cloud Run configurations ([dff5944](https://github.com/aergaroth/openjobseu/commit/dff59449e6ac3c3c5fdb5c533ad0570af90ba761))
* enhance error handling in Cloud Tasks and clean up headers for task creation ([85f11ca](https://github.com/aergaroth/openjobseu/commit/85f11cad2bfc7767fffcc309e290df7575284851))
* Enhance geo data classification with major cities mapping to EU countries ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* enhance job description assembly and cleaning across ATS adapters ([51b61f3](https://github.com/aergaroth/openjobseu/commit/51b61f331aeb44fd630fcdb399317c91a446d8ff))
* enhance job description handling and add Greenhouse adapter support in vie_job_from_feed.py script ([d350de8](https://github.com/aergaroth/openjobseu/commit/d350de8e6be8509cde69e2c67265fc6b32f17ac3))
* enhance job location extraction and salary parsing logic ([52c4cc6](https://github.com/aergaroth/openjobseu/commit/52c4cc6f9f9d13fcd2b1e04f68f3ba91a6ac39bb))
* Enhance job search functionality with GIN indexing and fuzzy search support ([3831279](https://github.com/aergaroth/openjobseu/commit/38312798f92ef01548eaf95344eb3d0966aa53ba))
* enhance remote classification logic and add new test cases for home-based scopes ([acca94e](https://github.com/aergaroth/openjobseu/commit/acca94ee75dac26c8c2eb494bc2df5efac35e09c))
* Enhance salary extraction and currency mapping ([73876f6](https://github.com/aergaroth/openjobseu/commit/73876f6b37d4ec7edca80445de0612b0becdd285))
* enhance SmartRecruiters adapter with improved job probing and error handling ([064cd97](https://github.com/aergaroth/openjobseu/commit/064cd97ebc87068e5ef66137a8172bad5e8fc816))
* enhance task statistics display with improved JSON formatting and styling ([94cd0ac](https://github.com/aergaroth/openjobseu/commit/94cd0ac1dead77ba1aaf7a326310587d6ca3040e))
* expose visible jobs as new + active in read API ([a7e68db](https://github.com/aergaroth/openjobseu/commit/a7e68db0603cd02107b0e70a5387d45ab999d351))
* extend job lifecycle with NEW status and TTL rules ([9e91944](https://github.com/aergaroth/openjobseu/commit/9e91944ef38d03c9594356512192182280097457))
* **frontend:** add minimal static feed table ([1b56b61](https://github.com/aergaroth/openjobseu/commit/1b56b615eddc5e62e5b66c2c490331b3a14c4b85))
* implement BASE_URL for task handler URLs and enhance error handling for Cloud Tasks ([e80563e](https://github.com/aergaroth/openjobseu/commit/e80563e10696a43a7f228d3c9c07209d306d81e6))
* Implement CI/CD workflows for development and production ([65b7c70](https://github.com/aergaroth/openjobseu/commit/65b7c70eefee6d62da60a14f9298ae176e90bb10))
* Implement employer ingestion limit configuration for better resource management ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* implement geo classification logic and add unit tests for geo_v3 ([4cf3ab0](https://github.com/aergaroth/openjobseu/commit/4cf3ab0202de026c49cb9d6e3eaf9439aa2fa8cb))
* implement incremental fetch logic across ATS adapters and update ingestion process ([5e55c49](https://github.com/aergaroth/openjobseu/commit/5e55c49f1b38a32e5381b1a3124137e7d7b44ca6))
* implement internal secret authentication for internal access and update tests ([849886d](https://github.com/aergaroth/openjobseu/commit/849886d05230f69c3460d388bea5c87b38499bcc))
* implement job probing functionality in ATS adapters and discovery pipeline ([2948fd7](https://github.com/aergaroth/openjobseu/commit/2948fd7fe4113dc08b77ca025ef466c791ca72d1))
* implement market metrics worker and related database schema updates ([a19c15c](https://github.com/aergaroth/openjobseu/commit/a19c15c6cd0afa3889d59bd1f908bd9096fb3cd1))
* implement pagination state updates in job loading function ([cc0f9c5](https://github.com/aergaroth/openjobseu/commit/cc0f9c57a2813f9c4f438c5afe3c6fdc174547d1))
* implement pagination state updates in job loading function ([b161702](https://github.com/aergaroth/openjobseu/commit/b16170288e74093f637abadb6cfe4218487a901e))
* Implement salary extraction and transparency detection ([6470c9a](https://github.com/aergaroth/openjobseu/commit/6470c9a4bd7c5018945672801a87d2614f700591))
* implement SmartRecruiters adapter and integrate into discovery pipeline ([44fc76b](https://github.com/aergaroth/openjobseu/commit/44fc76ba04b3275d8695eb472ebb31fb00a15ab3))
* Implement task cancellation and progress tracking in async operations ([6aa19a1](https://github.com/aergaroth/openjobseu/commit/6aa19a1ce5d5b734d68607ed6d48a0643ec0f94b))
* implement user authentication with OAuth and session management, enhance discovery pipeline with metrics, and improve audit panel UI ([3a667c3](https://github.com/aergaroth/openjobseu/commit/3a667c3f840c30a4cce554895d483b3a4d9872b3))
* improve career URL guessing logic and add URL validation ([fdba95f](https://github.com/aergaroth/openjobseu/commit/fdba95f6db8a2ac13ea2439893647c1206a0af23))
* Improve salary extraction logic and currency mapping ([f47d634](https://github.com/aergaroth/openjobseu/commit/f47d6348371ee71ca432ed690172bfcae7ff9d00))
* improve salary parsingand canonical identity handling ([1ec454a](https://github.com/aergaroth/openjobseu/commit/1ec454a4481167fa513106ae8b4bcfe4177f9c96))
* ingest local job source during scheduler tick ([19cb3c4](https://github.com/aergaroth/openjobseu/commit/19cb3c41e6ab42e1f140f8d8c98b1bf5a4d45c89))
* **ingestion:** add employer greenhouse pipeline and unify policy/audit model handling ([3518926](https://github.com/aergaroth/openjobseu/commit/351892655a84d4b7bd612f0dcdabeb23ecd2a54c))
* **ingestion:** add RemoteOK ingestion with standalone normalization ([c77e562](https://github.com/aergaroth/openjobseu/commit/c77e562a85d2800b990ad11460a4d965ed422ce7))
* **ingestion:** add stable job identity and policy version tracking ([f8a3b77](https://github.com/aergaroth/openjobseu/commit/f8a3b77551c804a0b4972c5b08ca17b5c9b05040))
* **ingestion:** fetch multiple WeWorkRemotely RSS categories with dedup ([6adadd6](https://github.com/aergaroth/openjobseu/commit/6adadd62e5b3c1b86c82f3633885aa58d036d173))
* **ingestion:** implement incremental ATS sync with last_sync_at tracking ([135f328](https://github.com/aergaroth/openjobseu/commit/135f328ffca34f0a898ebdd906606b7d09f179af))
* integrate dorking discovery into pipeline and add Google Secret Manager for API keys ([209866f](https://github.com/aergaroth/openjobseu/commit/209866f62588420aef37ae7e0e3137f7e3873e39))
* introduce geo_classifier v3 and shadow_employer_compliance_script ([482320f](https://github.com/aergaroth/openjobseu/commit/482320ffdf45ff8ddbf55bf758b31ec6ebe9cb5d))
* Introduce spam pattern detection in HTML cleaning utility ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* introduce tick worker skeleton for scheduled processing ([cbd4256](https://github.com/aergaroth/openjobseu/commit/cbd425640d8f4ceb150935a46309d9d4e7a619d9))
* **logging:** structured tick metrics and per-source ingestion summaries ([bfb20b5](https://github.com/aergaroth/openjobseu/commit/bfb20b506e8ad357c0bb4d4568cc3afc9e089ee4))
* **logging:** update JsonLogFormatter to use 'severity' and handle serialization errors gracefully ([bda56af](https://github.com/aergaroth/openjobseu/commit/bda56afb43b83972b2fc55ebce34a11613fe000f))
* **main:** enhance CORS configuration and add security headers middleware ([bda56af](https://github.com/aergaroth/openjobseu/commit/bda56afb43b83972b2fc55ebce34a11613fe000f))
* migrate storage from SQLite to PostgreSQL (Neon) + stabilize Cloud Run runtime ([0cc11fa](https://github.com/aergaroth/openjobseu/commit/0cc11fa82b83f72a31833ae29e409a8b51e62958))
* move employer ingestion to v3 policy, turn off weworkremotely and remoteok sources (paywalls) ([173b94a](https://github.com/aergaroth/openjobseu/commit/173b94afd6fae259c866546e1b8e9faaa5a7fb63))
* **normalization:** add Remotive job normalizer and tests ([460aa8f](https://github.com/aergaroth/openjobseu/commit/460aa8f16eaa0e097a2482ac204b8215919da8d1))
* **normalization:** add WeWorkRemotely normalizer and tests ([2fb982b](https://github.com/aergaroth/openjobseu/commit/2fb982bf37d67250c950fbac6eebca45bd2deefa))
* **observability:** policy audit log + improved Cloud Run log clarity ([ac2ff11](https://github.com/aergaroth/openjobseu/commit/ac2ff117ca54635210506deb23a5e2ee54d8f0e2))
* **observability:** policy reason metrics + structured tick output ([0a2556a](https://github.com/aergaroth/openjobseu/commit/0a2556a1dede3cde1dab81db02f68cd5e5ec6d74))
* optimize compliance score query and add feed optimal index ([f27ecc0](https://github.com/aergaroth/openjobseu/commit/f27ecc0b486295b6e49c7bfa4ac7421c18bd34d6))
* **pipeline:** persist policy flags and add compliance resolution step ([f83dd1d](https://github.com/aergaroth/openjobseu/commit/f83dd1d98c07dc645cf24d66a2f943ac9abe607c))
* **policy-v2:** add deterministic geo classifier and geo signal data ([375c488](https://github.com/aergaroth/openjobseu/commit/375c48885a277025964bd91d5dcff1366c519c01))
* **policy-v2:** introduce remote classifier and metrics wiring ([2fcecb9](https://github.com/aergaroth/openjobseu/commit/2fcecb9f759a250cba393ca4adc2fc67965e7833))
* **policy:** introduce policy v1 and global enforcement (remote purity + geo restrictions) ([fee8e3f](https://github.com/aergaroth/openjobseu/commit/fee8e3fed792de048fbb2f0472bc70af6afb59e7))
* refactor employer ingestion process with modular functions and enhanced metrics tracking ([9100545](https://github.com/aergaroth/openjobseu/commit/9100545a73643c76c37e9754350f20c0429c4726))
* refactor ingestion logic by removing legacy adapters and scripts, and enhance local job loading functionality ([acaf7fc](https://github.com/aergaroth/openjobseu/commit/acaf7fcf30e9a9b71ba083443490acd7e5ac8ace))
* Refactor job lifecycle and availability status ([2716301](https://github.com/aergaroth/openjobseu/commit/27163015dc3e23c5993678d7c78bf5a4df0fd6f8))
* Refactor salary extraction logic and introduce currency handling ([741f2b3](https://github.com/aergaroth/openjobseu/commit/741f2b333e89b1e6881ad84e1450ac3de6b2b2dc))
* Refactor task management and introduce frontend export functionality ([9e95c8d](https://github.com/aergaroth/openjobseu/commit/9e95c8d4d17fe94b44df89b0ff35b2da00163ec7))
* release OpenJobsEU 2.0 with modular ATS/compliance refactor ([a450632](https://github.com/aergaroth/openjobseu/commit/a450632d7ed7aa62ebb26cd8ac93895980922100))
* remove most literals from runtime to domain defined ([7fcfdc1](https://github.com/aergaroth/openjobseu/commit/7fcfdc122840d87f5d86c68e3ccc9f2fd2bd20d6))
* Rename columns in salary_parsing_cases for clarity and consistency ([fe2d81d](https://github.com/aergaroth/openjobseu/commit/fe2d81d4e8bbf8c6497e3225bf408cfc70471998))
* **runtime:** extend ingestion pipeline with additional source ([71599f4](https://github.com/aergaroth/openjobseu/commit/71599f4e94d6504f0a4d39dfbf783156b8a5d9e8))
* **runtime:** migrate OpenJobsEU from SQLite to PostgreSQL ([d7ce5e9](https://github.com/aergaroth/openjobseu/commit/d7ce5e9417448b7a594abe96bc916b0fb9daad05))
* **snapshot:** add job snapshots table and implement snapshotting on job updates ([856acaa](https://github.com/aergaroth/openjobseu/commit/856acaa52f2d0a0cb8c23f1841707a78796175e4))
* **storage:** derive/persist remote+geo classes and bootstrap missing compliance ([66dabb3](https://github.com/aergaroth/openjobseu/commit/66dabb309d2d3f332dc588443683f0e2832c2bc4))
* **storage:** migrate storage layer from SQLite to PostgreSQL ([6a9b616](https://github.com/aergaroth/openjobseu/commit/6a9b6163ae2d8be21fd6f4e0381840ae75cd0900))
* **taxonomy:** implement job taxonomy classification and quality scoring ([66409a7](https://github.com/aergaroth/openjobseu/commit/66409a7c7dcd4f7988d415c6954011cd9fa62c6d))
* **tests:** enhance test coverage and structure across various modules ([388e039](https://github.com/aergaroth/openjobseu/commit/388e039ab7b59452b019bf1df05f632d9cc21698))
* **tick-dev:** add authorization header for gcloud commands and improve error handling ([510040a](https://github.com/aergaroth/openjobseu/commit/510040a2af02993b51959377bbcbd7d689db557e))
* update access requirements for discovery and backfill endpoints ([fd50a50](https://github.com/aergaroth/openjobseu/commit/fd50a50089d769c4a1e334bdefb43fba43e9cbd6))
* update normalize function to accept Any type and ensure string conversion ([4f2106f](https://github.com/aergaroth/openjobseu/commit/4f2106f55ef62f709fd38a84b4d4ae28d9c66daf))
* use BASE_URL environment variable for tick handler URL construction ([3d9ec13](https://github.com/aergaroth/openjobseu/commit/3d9ec13b82263ea54da4fc5d2aeaf2f3ea3747bc))


### Bug Fixes

* add IF NOT EXISTS to ALTER TABLE and CREATE INDEX statements in migration scripts ([af1d63f](https://github.com/aergaroth/openjobseu/commit/af1d63f4978ac9f8c7c88886e672bf6a2b69bdae))
* add missing token for PR in release-please.yml ([083a039](https://github.com/aergaroth/openjobseu/commit/083a0399d0102e9d639d6aaf40185870f3e7566c))
* add target-branch to release-please.yml and define project metadata in pyproject.toml ([a111fe6](https://github.com/aergaroth/openjobseu/commit/a111fe62be8991b8e302257ba94804a1ee927c31))
* added required envs ([8c33335](https://github.com/aergaroth/openjobseu/commit/8c3333565be4a1ddb5a2cef7a9a583093c1f1322))
* **alembic:** safely enable pg_trgm extension with error handling for permissions ([bda56af](https://github.com/aergaroth/openjobseu/commit/bda56afb43b83972b2fc55ebce34a11613fe000f))
* align image tagging between build and Cloud Run deploy ([4a8816f](https://github.com/aergaroth/openjobseu/commit/4a8816f2e283fc6dbf8786eeca8ef8a6610a011b))
* **api:** imports after use ([fdbe873](https://github.com/aergaroth/openjobseu/commit/fdbe8736e3da7c3c8a38d28fbc7cb86d2a307a01))
* **api:** register CORS middleware after app initialization ([f096a74](https://github.com/aergaroth/openjobseu/commit/f096a741785e7dad6cbb9377343ab2a9aedc9dd9))
* **auth:** refine OAuth scope to include only 'openid' and 'email' ([bda56af](https://github.com/aergaroth/openjobseu/commit/bda56afb43b83972b2fc55ebce34a11613fe000f))
* change old (v2) remote mappings ([48eceb2](https://github.com/aergaroth/openjobseu/commit/48eceb250ea3bba24ba48d3b3555aaf6c72ed7be))
* change remote mappings ([4548a72](https://github.com/aergaroth/openjobseu/commit/4548a72d305e1c8b92327fdccf6bebda2f99302a))
* cleanup actions in logs - remove unused from post_ingestion ([667a4f2](https://github.com/aergaroth/openjobseu/commit/667a4f26534d7b39ccffbd9807a40c927e895c7d))
* **cloudrun:** keep listener up while DB bootstrap retries in background ([473ea90](https://github.com/aergaroth/openjobseu/commit/473ea90b500e852839d7172c4cf9d52318144e7b))
* correct dict unpacking in scheduler tick response ([f460b7a](https://github.com/aergaroth/openjobseu/commit/f460b7adce9e8e240fa40cc3581446feb5858196))
* Correct indentation in ATSAdapter constructor and update session headers ([810ea27](https://github.com/aergaroth/openjobseu/commit/810ea27e8a7cefcdc8e35f1bf3453358bc6a2305))
* correct runtime dependencies in requirements ([e80a9dd](https://github.com/aergaroth/openjobseu/commit/e80a9ddec8fb758609070a1e8b34e905c3fef759))
* corrected bucket name ([d6828fd](https://github.com/aergaroth/openjobseu/commit/d6828fd47fa019b1f9266cfeb3c441951dc0ecf8))
* corrected bucket name, after tests ([f19f0fe](https://github.com/aergaroth/openjobseu/commit/f19f0fe00747a3acca8cf625ab188400e07d1f0f))
* **cors:** enable OPTIONS method for public feed ([c8b8e86](https://github.com/aergaroth/openjobseu/commit/c8b8e8681e052e0fd4c3ce0a658709885e7b0474))
* debuging for GCP secrets ([60572c0](https://github.com/aergaroth/openjobseu/commit/60572c03e6d437b91e7bcb6aa5acb8edccf22701))
* disable SSL warnings and update requests to ignore certificate verification ([30943e1](https://github.com/aergaroth/openjobseu/commit/30943e19badb7cdbfae364426ce479929ea52f1d))
* enforce text response format for tick-dev endpoint ([1cf6350](https://github.com/aergaroth/openjobseu/commit/1cf63508a26575191effbcf13b885925d8c08a47))
* ensure ALTER TABLE statements check for existence of job_snapshots ([365676d](https://github.com/aergaroth/openjobseu/commit/365676da4ca5e3e68b387a377572e28ed54fc07e))
* ensure ALTER TABLE statements check for existence of job_snapshots ([14636b3](https://github.com/aergaroth/openjobseu/commit/14636b3422f0cd6bc7a8b9079e95233ae9961e85))
* **frontend:** align feed preview with public jobs/feed v1 contract ([f84cb4e](https://github.com/aergaroth/openjobseu/commit/f84cb4ec6827e52e9ee494c767964d88ad9a467d))
* **frontend:** correct feed JSON contract ([b7fcde3](https://github.com/aergaroth/openjobseu/commit/b7fcde35dfa9738717a19dd53176fc658f021fb9))
* **frontend:** move inline styles to external stylesheet (CSP-safe) ([a98ea17](https://github.com/aergaroth/openjobseu/commit/a98ea178765dc8c339604f6b2cccf7319caebefb))
* handle millisecond timestamps in normalize_source_datetime function ([4dfa4f0](https://github.com/aergaroth/openjobseu/commit/4dfa4f09a793b15e805e5fd280e2cca66f7ca9eb))
* handle response types in run_tick_from_audit endpoint ([ffa7631](https://github.com/aergaroth/openjobseu/commit/ffa763145e4e24b514f2ff60adc4d9a5117776c4))
* import DB helpers in availability and lifecycle pipelines ([c867e87](https://github.com/aergaroth/openjobseu/commit/c867e87c2b5990276df07b84afda302e28bc3957))
* increase memory limit for Cloud Run service to 1024Mi and remove unused merge.py file ([492b4b1](https://github.com/aergaroth/openjobseu/commit/492b4b1a7be771b8d597d29d4b6c843b0884a6ed))
* indentation int tick.py ([43c75af](https://github.com/aergaroth/openjobseu/commit/43c75afd8dbfdf086cc69c4c626b25dd8479498e))
* **ingestion:** align RemoteOkApiAdapter class name with imports ([b8c5e21](https://github.com/aergaroth/openjobseu/commit/b8c5e21787813c7650fbaa51dedc81216642ce3d))
* **ingestion:** Log unhandled exceptions during employer ingestion ([aa6ab85](https://github.com/aergaroth/openjobseu/commit/aa6ab85c4cd37f1474f037203216d659178df9a8))
* initialize db before tests ([fce9f9b](https://github.com/aergaroth/openjobseu/commit/fce9f9b2879e39d1ff2513393b3b9f7d21692141))
* **logging:** standardize logger name in backfill compliance and salary modules ([e3eddc2](https://github.com/aergaroth/openjobseu/commit/e3eddc22ba41d9a164c475feb7902063b7153e31))
* **logging:** update json formatter test to assert 'severity' instead of 'level' ([0c79e2b](https://github.com/aergaroth/openjobseu/commit/0c79e2bc2400b0bd26433c5b68e2f38da13b7492))
* make ttl-based stale status effective in availability checker ([a833344](https://github.com/aergaroth/openjobseu/commit/a833344bbd3a61800b08c11282d615cdbebb7e70))
* **migrations:** remove pgcrypto dependency for Neon compatibility ([772a930](https://github.com/aergaroth/openjobseu/commit/772a93032ab3b419be886ea97c54c6d4aba9b5f5))
* missed collon in internal.py ([a79a807](https://github.com/aergaroth/openjobseu/commit/a79a80776811daa0617be1e385c0026e33c4371c))
* missing requirements ([0145258](https://github.com/aergaroth/openjobseu/commit/0145258d9ad6357b9d47de85dd4637b5d8f90076))
* move normalization to valid layer and added test to avoid messing normalization with adapters ([994116e](https://github.com/aergaroth/openjobseu/commit/994116e4e09d60f62604c5f038071120c937cc78))
* move service_account to templane for newer provider ([67b056d](https://github.com/aergaroth/openjobseu/commit/67b056dbf8afede54081994921c47e3e064cd306))
* moved RSS_URL from worker to adapter ([d00ef38](https://github.com/aergaroth/openjobseu/commit/d00ef384b79088f20ff27b0901ffa707aa5f013e))
* **policy:** adjust geo detection + harden feed audit script ([b8eb53a](https://github.com/aergaroth/openjobseu/commit/b8eb53aa28d2e3d27ec68baf1e4281f32d3c7cf8))
* provide TF_VARS for workflow ([097a242](https://github.com/aergaroth/openjobseu/commit/097a2425914d36c306c18a6c9e71e23808d718ea))
* refactor import statements and enhance test coverage for maintenance pipeline ([b464344](https://github.com/aergaroth/openjobseu/commit/b4643448c563588c2818531a2ed44ba45a46528e))
* remove old (unused) helper ([660391c](https://github.com/aergaroth/openjobseu/commit/660391c2508122b5cf8a8f51162677da7023b95b))
* remove unused taskName extra field from logs ([6a0027a](https://github.com/aergaroth/openjobseu/commit/6a0027a8276826dfb69b97af825b9c7fdb368bc6))
* removed post_ingestion() call arg. - refactored previously ([7293e39](https://github.com/aergaroth/openjobseu/commit/7293e398fdfb46f403ebb78d5be6722180621440))
* renamed field in DB in exmaple test ([6fc8398](https://github.com/aergaroth/openjobseu/commit/6fc8398d660cede5c7fcf4fef3624c2c24f21279))
* resolve cron storm, UI FOUC, and CI validation errors ([0f50273](https://github.com/aergaroth/openjobseu/commit/0f50273ef0d77f8965cb29909000ba5ee0286b36))
* **salary_extraction, db_migration:** Correct salary max calculation and update salary field types ([c4332c0](https://github.com/aergaroth/openjobseu/commit/c4332c023062a54e73b681aace43771f26d5c1c2))
* secure ingestion worker, check if compliance is initiated before apply, secure policy engine ([6f99079](https://github.com/aergaroth/openjobseu/commit/6f99079c11c86c5808c8d023da60f1e6c948fc5a))
* **startup:** fail fast when DB bootstrap or migrations fail ([8a94e73](https://github.com/aergaroth/openjobseu/commit/8a94e73777521a0532caf085356b9339cadee740))
* **storage:** initialize sqlite schema on app startup ([7cb0f13](https://github.com/aergaroth/openjobseu/commit/7cb0f13d852ca15ae411110d857e7877abb3db1b))
* **storage:** resolve sqlite db path at runtime to fix CI tests ([0e916dd](https://github.com/aergaroth/openjobseu/commit/0e916ddb263c146efc43f7bacbbf16cafcda1edd))
* **tests:** update ingestion mock to return adapter instance ([bf59f87](https://github.com/aergaroth/openjobseu/commit/bf59f870d40f132ce6b7f4ec1dc718a121f01603))
* tick orchestration: ([7f65db5](https://github.com/aergaroth/openjobseu/commit/7f65db5a1d107f0be3ae901b7182bed5edd636a2))
* tick-dev.sh script could be run in other shell than bash ([3b62888](https://github.com/aergaroth/openjobseu/commit/3b628886971adcdd57648b353025827932cf3e9a))
* **tick:** render source metrics for flat ingestion payload format ([483db24](https://github.com/aergaroth/openjobseu/commit/483db24f48a307b2e64f65017ead07a8ba3e2ba0))
* typo - space afer backslash ([4095e58](https://github.com/aergaroth/openjobseu/commit/4095e583c44474ba30270fe154ba58a060c827e3))
* typo - space afer backslash ([219554c](https://github.com/aergaroth/openjobseu/commit/219554c04fe4ec470064d00d49b70b40829b35c3))
* typo in requirements.txt ([b51dc40](https://github.com/aergaroth/openjobseu/commit/b51dc409ad82ae900289b97e8062f75c429e5e62))
* update Alembic stamp revision to specific commit for database migration ([9e9b702](https://github.com/aergaroth/openjobseu/commit/9e9b702a42128512ff88613dd380bd1a07b94919))
* update Alembic stamp revision to specific commit for database migration ([147839e](https://github.com/aergaroth/openjobseu/commit/147839eb4f4e8a973d2d036c53d502283c8a4447))
* update branch from main to develop in release-please.yml and add release-please manifest ([574d557](https://github.com/aergaroth/openjobseu/commit/574d55717680ec781202191ff0776bcbf5d7e0ff))
* update comment in Dockerfile ([9f3a482](https://github.com/aergaroth/openjobseu/commit/9f3a4828d0cb5d708737d23470b002be23fcdd61))
* update commit-check workflow to validate commit messages using Commitizen ([ec4c5fa](https://github.com/aergaroth/openjobseu/commit/ec4c5fa0562597426d7a38f6182af5a2b08ed1fb))
* update conditional for build-deploy-dev job to exclude main branch in pull requests ([5ed063a](https://github.com/aergaroth/openjobseu/commit/5ed063a7141309386339a2dd6b5ac3ba86c01e2b))
* update job processing to handle rejected jobs and adjust compliance reporting ([625f230](https://github.com/aergaroth/openjobseu/commit/625f230a161a1ba290a2137feb774fae39987c98))
* update missing logg info for employer ingestion ([5af2e1e](https://github.com/aergaroth/openjobseu/commit/5af2e1e2e730ee9ea0d38aedfbeec0bdc1feffc5))
* update pull request conditions for dev and prod workflows to improve branch handling ([e82f2e0](https://github.com/aergaroth/openjobseu/commit/e82f2e04a1b22d1f2ad74c539bdd9df97fe4e38c))
* Update README badge and refactor ATSAdapter for requests session ([8ab5239](https://github.com/aergaroth/openjobseu/commit/8ab523927237ed6312fc1d71533df0f497f4d71a))


### Documentation

* add ci status badge ([8f34612](https://github.com/aergaroth/openjobseu/commit/8f346120895479bb67ccebd993accff00252e6d6))
* add content quality & policy v1 milestone to roadmap ([f9fb2c1](https://github.com/aergaroth/openjobseu/commit/f9fb2c1df7f220428ddd6bc4aa6a4c23bf9aa1b7))
* add system architecture and design rationale ([0440aaa](https://github.com/aergaroth/openjobseu/commit/0440aaabcb34532a9b6d4ae1c018e78abf524029))
* added hint in ARCHITECTURE.md ([1bb8df1](https://github.com/aergaroth/openjobseu/commit/1bb8df1785db22e07f21a25c4981234959de8c25))
* added short hit for Terraform .tfvars file ([c2d45a6](https://github.com/aergaroth/openjobseu/commit/c2d45a62dc3bf22b4be295a834020e576f47ff09))
* added site url ([c7195da](https://github.com/aergaroth/openjobseu/commit/c7195dadefc906d87865695e86be3a320edc70aa))
* align project documentation with current MVP implementation ([24edc13](https://github.com/aergaroth/openjobseu/commit/24edc13f737a641f968f600730abe8eed5972890))
* canonical model to match current state ([599e7ce](https://github.com/aergaroth/openjobseu/commit/599e7ce5a434de843d40890aa606d33d3dbfad66))
* clarify procject direction ([f8c682a](https://github.com/aergaroth/openjobseu/commit/f8c682a2f36d934d03afe6842c1482df9b0894e8))
* clean up roadmap after MVP v1 completion ([ba7ba32](https://github.com/aergaroth/openjobseu/commit/ba7ba3259feb6ede5ca67c4e30f9fc2b57bd3471))
* current state in ROADMAP ([3b671fd](https://github.com/aergaroth/openjobseu/commit/3b671fd795ab869bf4de85a4f1a875e1c7a5df05))
* define canonical job model and lifecycle ([9726adf](https://github.com/aergaroth/openjobseu/commit/9726adf235c02ec15e26fa62fbf676d6e9b91771))
* edit architecture, to match the current state ([9225fd7](https://github.com/aergaroth/openjobseu/commit/9225fd7603601d60383426c80bc288be51fa834e))
* Example source information ([25d83df](https://github.com/aergaroth/openjobseu/commit/25d83df202a74c0f2ed546483c29dda7c68e6866))
* fix badge to point to prod environment ([47dbe9f](https://github.com/aergaroth/openjobseu/commit/47dbe9fcb90b127786614f7e840f054af35dc643))
* fix typo ([9aa9fe0](https://github.com/aergaroth/openjobseu/commit/9aa9fe06e90078e393bf7cfc5006c89b12876efd))
* refresh ROADMAP ([9612da5](https://github.com/aergaroth/openjobseu/commit/9612da50931cb25e16dc7f0b23e6c52e0b1ec216))
* resize architecture diagram ([5f34b03](https://github.com/aergaroth/openjobseu/commit/5f34b03a396862ff724eb5ac0e87488d9edcd055))
* sync documentation with current runtime ([351c28c](https://github.com/aergaroth/openjobseu/commit/351c28c89690be06ef0423e1d47e9e2dc7c3378c))
* synchronize architecture, system map and roadmap ([5a33fda](https://github.com/aergaroth/openjobseu/commit/5a33fda1a7b24d280793020ded4263df97b7dc3d))
* update architecture diagram API naming ([2850311](https://github.com/aergaroth/openjobseu/commit/28503113650a5de2a44dd2b77bcf756fe2575fc1))
* Update architecture documentation to reflect new internal endpoint parameters ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* update documentation to match current state ([d543e42](https://github.com/aergaroth/openjobseu/commit/d543e422c86cd4df9fc1107f299532cafa7360f8))
* Update documentation to match the current state of project. ([4c50ade](https://github.com/aergaroth/openjobseu/commit/4c50ade91aa089288af1534492ea16f6e26042a1))
* update README and roadmap after A7 completion ([e5dc640](https://github.com/aergaroth/openjobseu/commit/e5dc64083dc881740c4aced5a7ba38bd1f0885a6))
* update README and roadmap after lifecycle and read API ([ee303d5](https://github.com/aergaroth/openjobseu/commit/ee303d58a2a1fec5667827d2520a06a44751fff5))
* update README with current architecture and ingestion flow ([6b04008](https://github.com/aergaroth/openjobseu/commit/6b04008d436dcff1caa8680585e0807cd73bdf0e))
* update README, ARCHITECTURE, CANONICAL_MODEL, COMPLIANCE, DATA_SOURCES, and ROADMAP for clarity and consistency ([679999f](https://github.com/aergaroth/openjobseu/commit/679999f6741706f39e2e7edb935d51417ee32e6c))

## [0.3.0](https://github.com/aergaroth/openjobseu/compare/v0.2.0...v0.3.0) (2026-03-22)


### Features

* decouple Cloud Tasks handlers and implement time-budgeting ([749152b](https://github.com/aergaroth/openjobseu/commit/749152b022fdb8c4ea388bcd847ad1bc75ff5f67))


### Bug Fixes

* resolve cron storm, UI FOUC, and CI validation errors ([0f50273](https://github.com/aergaroth/openjobseu/commit/0f50273ef0d77f8965cb29909000ba5ee0286b36))


### Documentation

* synchronize architecture, system map and roadmap ([5a33fda](https://github.com/aergaroth/openjobseu/commit/5a33fda1a7b24d280793020ded4263df97b7dc3d))

## [0.2.0](https://github.com/aergaroth/openjobseu/compare/v0.1.0...v0.2.0) (2026-03-22)


### Features

* add commit message validation workflow using Commitizen ([27113c9](https://github.com/aergaroth/openjobseu/commit/27113c93e373c2bca08059a047f46bd22460e0f4))


### Bug Fixes

* update commit-check workflow to validate commit messages using Commitizen ([ec4c5fa](https://github.com/aergaroth/openjobseu/commit/ec4c5fa0562597426d7a38f6182af5a2b08ed1fb))

## 0.1.0 (2026-03-22)


### ⚠ BREAKING CHANGES

* legacy adapters, v2/v3 policy modules, and old normalization worker paths were removed in favor of the new OpenJobsEU 2.0 structure.

### Features

* **a6.1:** extract company name from RSS titles when missing ([92c7140](https://github.com/aergaroth/openjobseu/commit/92c7140cc2a4dbb56997f5c10859beb0a681bed5))
* add advanced filtering to jobs read API ([e53af30](https://github.com/aergaroth/openjobseu/commit/e53af3008ff8d8247b27477f08c7a891d678e90e))
* add audit companies endpoint with filters ([3641e86](https://github.com/aergaroth/openjobseu/commit/3641e86b00ada6394cb8d4e12db40b849f6f552c))
* add availability checker with ttl-based status transitions ([dec1d80](https://github.com/aergaroth/openjobseu/commit/dec1d806fceb25ada3d160ee9d606895dde177c4))
* add availability checking to rss tick worker ([7c2426d](https://github.com/aergaroth/openjobseu/commit/7c2426d4592cc057d9a14af8cfb1ba3898ea747f))
* add BASE_URL environment variable and update OIDC audience in Cloud Scheduler jobs ([e148170](https://github.com/aergaroth/openjobseu/commit/e1481701e76afaffa3b625ffc515b1001cd1d847))
* add canonical job ID computation and related database updates for job reposting ([af5d92f](https://github.com/aergaroth/openjobseu/commit/af5d92f34a6e7e3f70a34ab8270fb2b3671c23da))
* add CHANGELOG and protect_develop workflow ([f41f296](https://github.com/aergaroth/openjobseu/commit/f41f296b8d7929e26a19fb6a542c96da15743dee))
* Add companies API endpoint and enhance discovery processes ([47a9289](https://github.com/aergaroth/openjobseu/commit/47a92896bce73b64629be0f1eb93b3f4285472ae))
* add compliance backfill script and fix JSON serialization in DB logic ([51203bb](https://github.com/aergaroth/openjobseu/commit/51203bbff010b46afce6adab86acaed3d356b4b4))
* add compliance score and status to policy application logic ([0f7239e](https://github.com/aergaroth/openjobseu/commit/0f7239e6eafa3043f694d1b32f4d74c117e82a35))
* add compliance stats endpoints and update frontend to display 7-day compliance metricsupdate audit_tool and api for compliance statistics ([adf5fc3](https://github.com/aergaroth/openjobseu/commit/adf5fc31a6bf74a507230d082326d0eced98d983))
* add docker-compose for local development workflow ([d03964c](https://github.com/aergaroth/openjobseu/commit/d03964c8b0c2c2c1e1fd60e9467b3da41d747f1c))
* add dockerfile for reproducible test environment ([908aa48](https://github.com/aergaroth/openjobseu/commit/908aa48378b776fb26fb0f932e3a865776915325))
* add example ingestion source with normalization and tests ([cf13d87](https://github.com/aergaroth/openjobseu/commit/cf13d87b8dcca27d2394c1366b2e299500592b6b))
* Add full sync script for tick endpoint with retry mechanism ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* add geo_data module and enhance remote signals with new options ([fd15599](https://github.com/aergaroth/openjobseu/commit/fd15599d4d09ba6aa4b5b6c7911a6862aa29f05c))
* add Google OAuth secrets and allowed email configuration to Terraform apply ([df097b6](https://github.com/aergaroth/openjobseu/commit/df097b6dd790bfa64ea79c21b6d04f48b9055d07))
* add Google Secret Manager resources for API keys and update variables for Google API key and CSE ID ([e98c1d0](https://github.com/aergaroth/openjobseu/commit/e98c1d07212c4b8fc12c47a2fe8a604ab1c99a5b))
* add IF NOT EXISTS clause to job taxonomy and dataset indexes ([012dcf5](https://github.com/aergaroth/openjobseu/commit/012dcf5efd4e8c13302ab6c996fdeacd755bddbb))
* add initial migration for job indexes ([bea6288](https://github.com/aergaroth/openjobseu/commit/bea6288120861952f20537b848f532724fee7d3e))
* add job preview endpoint and enhance audit panel with new features ([18a20fc](https://github.com/aergaroth/openjobseu/commit/18a20fc86281dd3cc5451af6c4e1198e93091d0a))
* add lifecycle rules for job expiration ([b00dce2](https://github.com/aergaroth/openjobseu/commit/b00dce21fbaa8c530878fe19cc22a4fef4ef9b2c))
* Add limit parameter to internal tick endpoint for controlled processing ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* add minimal runtime with health endpoints ([0b3ae4e](https://github.com/aergaroth/openjobseu/commit/0b3ae4e31f7f10ca078de59819a496a981e0bd84))
* add minimal runtime with health endpoints ([9ee481a](https://github.com/aergaroth/openjobseu/commit/9ee481a390cc82b9df032b46b3b1f4d726d11369))
* add non-EU classification logic and corresponding tests for geo_v3 ([cc50627](https://github.com/aergaroth/openjobseu/commit/cc50627449cc1b5da2b0046264400bd5ae3db165))
* add performance timing to careers discovery process ([cfe4eec](https://github.com/aergaroth/openjobseu/commit/cfe4eec7b76eadaacd4a83e8af217a5e0d84fbef))
* add Personio and Recruitee adapters for job fetching and processing ([b9f4ab1](https://github.com/aergaroth/openjobseu/commit/b9f4ab1305b0cddfa21eed89383e80c51c594981))
* add planned features section to roadmap with dataset API and analytics ([837e5b1](https://github.com/aergaroth/openjobseu/commit/837e5b1441513c9835d269339a3ad3de5aa3216b))
* add rss ingestion with dev-only local fallback ([a2a36cc](https://github.com/aergaroth/openjobseu/commit/a2a36cc990cee37ccf4a382aa247b56f4dbf1a7b))
* add salary backfill endpoint and refactor audit registry ([508b5f0](https://github.com/aergaroth/openjobseu/commit/508b5f05de4f06537078f4a4c17bc649fb4519e3))
* add scheduler heartbeat and internal tick endpoint ([b4109f1](https://github.com/aergaroth/openjobseu/commit/b4109f1b5026d4e25b44bee6fb71b3b83e16eec9))
* add scheduler heartbeat and runtime tick endpoint ([8c7fd10](https://github.com/aergaroth/openjobseu/commit/8c7fd10a772997ce972a3df5ff92af4a36aafa7c))
* add sqlite persistence for ingested jobs ([4d36a25](https://github.com/aergaroth/openjobseu/commit/4d36a25087cc82192e2c4e03cc0b38f512581b9c))
* add test for rejected job not inserting compliance report without job ID ([08e4d7f](https://github.com/aergaroth/openjobseu/commit/08e4d7f6e1b2f849db4b9c0cde4c0e7f2261727b))
* add unit tests for job fetching and lifecycle pipeline execution ([6994cc8](https://github.com/aergaroth/openjobseu/commit/6994cc854c302df97e1221b84469c2e2b8f1e875))
* added example test and __init__.py for modules ([6bacb89](https://github.com/aergaroth/openjobseu/commit/6bacb8957ec6a2a366fefca672c51b4fce66f07f))
* added simple frontend ([e21c418](https://github.com/aergaroth/openjobseu/commit/e21c418e1e5388f53e12676690df9d4bf347398c))
* **api:** add public /jobs/feed ([b57c40b](https://github.com/aergaroth/openjobseu/commit/b57c40bab51a62afbd9efdfd22e7c2e00ecab264))
* **api:** filter feed by minimum compliance score ([83e9636](https://github.com/aergaroth/openjobseu/commit/83e96364e9315089cd69cb7fe109bfe82ebc25b3))
* **ats/greenhouse:** add INCREMENTAL_FETCH control to adapter ([9809812](https://github.com/aergaroth/openjobseu/commit/980981256687dd1f0727fb75c75bd27ea0ef2162))
* **ats:** standardize adapter interfaces and add registry registration ([cb9f129](https://github.com/aergaroth/openjobseu/commit/cb9f129bd7f0eeef705dca65b8d1e9ad03921b16))
* **audit panel:** add cached static endpoints and ATS actions ([b292d11](https://github.com/aergaroth/openjobseu/commit/b292d111bd4746b0fe09a251d9ddc446f1eef2c6))
* **audit:** add safeLoadAtsHealth to async data loading ([69a4a61](https://github.com/aergaroth/openjobseu/commit/69a4a61162a3ae4ee496020b1d266ecd3f48fa8c))
* **audit:** rename Offer Audit Panel to Admin Audit Panel and add new backfill options ([848fc46](https://github.com/aergaroth/openjobseu/commit/848fc46e301269acce5873f815c373d6f41458ed))
* **audit:** update test to reflect renaming of Offer Audit Panel to Admin Audit Panel ([77df720](https://github.com/aergaroth/openjobseu/commit/77df720fd133c07708b51a6aab0a3e10a50d8536))
* **auth:** add email whitelist and improve OAuth configuration handling ([6109dbd](https://github.com/aergaroth/openjobseu/commit/6109dbdddbcae11b08275a453aeaa694afffebb1))
* **careers_crawler:** Update to use requests.Response type and explicit URL/text extraction ([6f640a4](https://github.com/aergaroth/openjobseu/commit/6f640a4e4f182fc9e71db052c0cf0e33dc2f3268))
* **careers_crawler:** Update to use requests.Response type and explicit URL/text extraction ([6c6faa3](https://github.com/aergaroth/openjobseu/commit/6c6faa3ddb4bb8fa69888dbddd0cd22af542437d))
* changed tick formatting, added metrics for employer ingestion, update docs ([48b20c9](https://github.com/aergaroth/openjobseu/commit/48b20c95a47a85c0ceb219ee6ef593e6c15d6fb0))
* complete compliance resolution in ingestion and populate compliance_reports table ([a14aa68](https://github.com/aergaroth/openjobseu/commit/a14aa6810c429490a9fe6dfe4a2c3e231b8fe008))
* compliance decision trace, unique reports and backfill script ([0cf16a7](https://github.com/aergaroth/openjobseu/commit/0cf16a7fa4e65f61e9eabec71ca39a5666816c9f))
* **compliance:** replace resolver with normalized decision matrix ([573f44b](https://github.com/aergaroth/openjobseu/commit/573f44ba65d7cc191de6eb2f7a7102b110580f80))
* **compliance:** update remote class normalization and scoring logic ([4a05705](https://github.com/aergaroth/openjobseu/commit/4a057055b5d42acdd1957f72f63360551a783f81))
* conditionally persist compliance report for canonical jobs only ([10a3c37](https://github.com/aergaroth/openjobseu/commit/10a3c37ba411c7738e6642d2c6e5cc8b85c830ac))
* consolidate architecture documentation and add system map ([1ba215a](https://github.com/aergaroth/openjobseu/commit/1ba215af856b158cd082c2a24393e7c3dcfa877e))
* Create scripts for auditing HTML leftovers and description sanity checks ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* **discovery:** enhance error handling in probe_ats function ([e00f971](https://github.com/aergaroth/openjobseu/commit/e00f97127b5323de2640c9e020ad8fd0a230e280))
* Enable incremental fetch for Greenhouse adapter and refine job enrichment logic based on compliance status ([10fac4c](https://github.com/aergaroth/openjobseu/commit/10fac4c86ac4cdc7a5ad9aaaf8d6c39727117fc1))
* enhance ATS adapters, discovery pipeline, and secure Audit UI ([4bc467b](https://github.com/aergaroth/openjobseu/commit/4bc467bbafcc7770c4fdbc407c78e1e641915220))
* enhance ATS adapters, discovery pipeline, and secure Audit UI ([8039b2c](https://github.com/aergaroth/openjobseu/commit/8039b2c90167a32837ea775e92e4fa04c6afcd61))
* Enhance ATS ingestion and canonical model with taxonomy ([55f64ef](https://github.com/aergaroth/openjobseu/commit/55f64ef38f4a20a70c9889174a5e7c69d9b075c2))
* enhance ATS integration with batching and sync status updates ([1567d2d](https://github.com/aergaroth/openjobseu/commit/1567d2d2f44bb0a1c0059c9ff1a70e90f9239b7c))
* enhance discovery pipeline with new metrics and update filtering logic ([190722f](https://github.com/aergaroth/openjobseu/commit/190722fcbc0a7294e3a3eb2d13641afb89d5ebcc))
* enhance discovery processes and improve Cloud Run configurations ([dff5944](https://github.com/aergaroth/openjobseu/commit/dff59449e6ac3c3c5fdb5c533ad0570af90ba761))
* enhance error handling in Cloud Tasks and clean up headers for task creation ([85f11ca](https://github.com/aergaroth/openjobseu/commit/85f11cad2bfc7767fffcc309e290df7575284851))
* Enhance geo data classification with major cities mapping to EU countries ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* enhance job description assembly and cleaning across ATS adapters ([51b61f3](https://github.com/aergaroth/openjobseu/commit/51b61f331aeb44fd630fcdb399317c91a446d8ff))
* enhance job description handling and add Greenhouse adapter support in vie_job_from_feed.py script ([d350de8](https://github.com/aergaroth/openjobseu/commit/d350de8e6be8509cde69e2c67265fc6b32f17ac3))
* enhance job location extraction and salary parsing logic ([52c4cc6](https://github.com/aergaroth/openjobseu/commit/52c4cc6f9f9d13fcd2b1e04f68f3ba91a6ac39bb))
* Enhance job search functionality with GIN indexing and fuzzy search support ([3831279](https://github.com/aergaroth/openjobseu/commit/38312798f92ef01548eaf95344eb3d0966aa53ba))
* enhance remote classification logic and add new test cases for home-based scopes ([acca94e](https://github.com/aergaroth/openjobseu/commit/acca94ee75dac26c8c2eb494bc2df5efac35e09c))
* Enhance salary extraction and currency mapping ([73876f6](https://github.com/aergaroth/openjobseu/commit/73876f6b37d4ec7edca80445de0612b0becdd285))
* enhance SmartRecruiters adapter with improved job probing and error handling ([064cd97](https://github.com/aergaroth/openjobseu/commit/064cd97ebc87068e5ef66137a8172bad5e8fc816))
* enhance task statistics display with improved JSON formatting and styling ([94cd0ac](https://github.com/aergaroth/openjobseu/commit/94cd0ac1dead77ba1aaf7a326310587d6ca3040e))
* expose visible jobs as new + active in read API ([a7e68db](https://github.com/aergaroth/openjobseu/commit/a7e68db0603cd02107b0e70a5387d45ab999d351))
* extend job lifecycle with NEW status and TTL rules ([9e91944](https://github.com/aergaroth/openjobseu/commit/9e91944ef38d03c9594356512192182280097457))
* **frontend:** add minimal static feed table ([1b56b61](https://github.com/aergaroth/openjobseu/commit/1b56b615eddc5e62e5b66c2c490331b3a14c4b85))
* implement BASE_URL for task handler URLs and enhance error handling for Cloud Tasks ([e80563e](https://github.com/aergaroth/openjobseu/commit/e80563e10696a43a7f228d3c9c07209d306d81e6))
* Implement CI/CD workflows for development and production ([65b7c70](https://github.com/aergaroth/openjobseu/commit/65b7c70eefee6d62da60a14f9298ae176e90bb10))
* Implement employer ingestion limit configuration for better resource management ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* implement geo classification logic and add unit tests for geo_v3 ([4cf3ab0](https://github.com/aergaroth/openjobseu/commit/4cf3ab0202de026c49cb9d6e3eaf9439aa2fa8cb))
* implement incremental fetch logic across ATS adapters and update ingestion process ([5e55c49](https://github.com/aergaroth/openjobseu/commit/5e55c49f1b38a32e5381b1a3124137e7d7b44ca6))
* implement internal secret authentication for internal access and update tests ([849886d](https://github.com/aergaroth/openjobseu/commit/849886d05230f69c3460d388bea5c87b38499bcc))
* implement job probing functionality in ATS adapters and discovery pipeline ([2948fd7](https://github.com/aergaroth/openjobseu/commit/2948fd7fe4113dc08b77ca025ef466c791ca72d1))
* implement market metrics worker and related database schema updates ([a19c15c](https://github.com/aergaroth/openjobseu/commit/a19c15c6cd0afa3889d59bd1f908bd9096fb3cd1))
* implement pagination state updates in job loading function ([b161702](https://github.com/aergaroth/openjobseu/commit/b16170288e74093f637abadb6cfe4218487a901e))
* Implement salary extraction and transparency detection ([6470c9a](https://github.com/aergaroth/openjobseu/commit/6470c9a4bd7c5018945672801a87d2614f700591))
* implement SmartRecruiters adapter and integrate into discovery pipeline ([44fc76b](https://github.com/aergaroth/openjobseu/commit/44fc76ba04b3275d8695eb472ebb31fb00a15ab3))
* Implement task cancellation and progress tracking in async operations ([6aa19a1](https://github.com/aergaroth/openjobseu/commit/6aa19a1ce5d5b734d68607ed6d48a0643ec0f94b))
* implement user authentication with OAuth and session management, enhance discovery pipeline with metrics, and improve audit panel UI ([3a667c3](https://github.com/aergaroth/openjobseu/commit/3a667c3f840c30a4cce554895d483b3a4d9872b3))
* improve career URL guessing logic and add URL validation ([fdba95f](https://github.com/aergaroth/openjobseu/commit/fdba95f6db8a2ac13ea2439893647c1206a0af23))
* Improve salary extraction logic and currency mapping ([f47d634](https://github.com/aergaroth/openjobseu/commit/f47d6348371ee71ca432ed690172bfcae7ff9d00))
* improve salary parsingand canonical identity handling ([1ec454a](https://github.com/aergaroth/openjobseu/commit/1ec454a4481167fa513106ae8b4bcfe4177f9c96))
* ingest local job source during scheduler tick ([19cb3c4](https://github.com/aergaroth/openjobseu/commit/19cb3c41e6ab42e1f140f8d8c98b1bf5a4d45c89))
* **ingestion:** add employer greenhouse pipeline and unify policy/audit model handling ([3518926](https://github.com/aergaroth/openjobseu/commit/351892655a84d4b7bd612f0dcdabeb23ecd2a54c))
* **ingestion:** add RemoteOK ingestion with standalone normalization ([c77e562](https://github.com/aergaroth/openjobseu/commit/c77e562a85d2800b990ad11460a4d965ed422ce7))
* **ingestion:** add stable job identity and policy version tracking ([f8a3b77](https://github.com/aergaroth/openjobseu/commit/f8a3b77551c804a0b4972c5b08ca17b5c9b05040))
* **ingestion:** fetch multiple WeWorkRemotely RSS categories with dedup ([6adadd6](https://github.com/aergaroth/openjobseu/commit/6adadd62e5b3c1b86c82f3633885aa58d036d173))
* **ingestion:** implement incremental ATS sync with last_sync_at tracking ([135f328](https://github.com/aergaroth/openjobseu/commit/135f328ffca34f0a898ebdd906606b7d09f179af))
* integrate dorking discovery into pipeline and add Google Secret Manager for API keys ([209866f](https://github.com/aergaroth/openjobseu/commit/209866f62588420aef37ae7e0e3137f7e3873e39))
* introduce geo_classifier v3 and shadow_employer_compliance_script ([482320f](https://github.com/aergaroth/openjobseu/commit/482320ffdf45ff8ddbf55bf758b31ec6ebe9cb5d))
* Introduce spam pattern detection in HTML cleaning utility ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* introduce tick worker skeleton for scheduled processing ([cbd4256](https://github.com/aergaroth/openjobseu/commit/cbd425640d8f4ceb150935a46309d9d4e7a619d9))
* **logging:** structured tick metrics and per-source ingestion summaries ([bfb20b5](https://github.com/aergaroth/openjobseu/commit/bfb20b506e8ad357c0bb4d4568cc3afc9e089ee4))
* **logging:** update JsonLogFormatter to use 'severity' and handle serialization errors gracefully ([bda56af](https://github.com/aergaroth/openjobseu/commit/bda56afb43b83972b2fc55ebce34a11613fe000f))
* **main:** enhance CORS configuration and add security headers middleware ([bda56af](https://github.com/aergaroth/openjobseu/commit/bda56afb43b83972b2fc55ebce34a11613fe000f))
* move employer ingestion to v3 policy, turn off weworkremotely and remoteok sources (paywalls) ([173b94a](https://github.com/aergaroth/openjobseu/commit/173b94afd6fae259c866546e1b8e9faaa5a7fb63))
* **normalization:** add Remotive job normalizer and tests ([460aa8f](https://github.com/aergaroth/openjobseu/commit/460aa8f16eaa0e097a2482ac204b8215919da8d1))
* **normalization:** add WeWorkRemotely normalizer and tests ([2fb982b](https://github.com/aergaroth/openjobseu/commit/2fb982bf37d67250c950fbac6eebca45bd2deefa))
* **observability:** policy audit log + improved Cloud Run log clarity ([ac2ff11](https://github.com/aergaroth/openjobseu/commit/ac2ff117ca54635210506deb23a5e2ee54d8f0e2))
* **observability:** policy reason metrics + structured tick output ([0a2556a](https://github.com/aergaroth/openjobseu/commit/0a2556a1dede3cde1dab81db02f68cd5e5ec6d74))
* optimize compliance score query and add feed optimal index ([f27ecc0](https://github.com/aergaroth/openjobseu/commit/f27ecc0b486295b6e49c7bfa4ac7421c18bd34d6))
* **pipeline:** persist policy flags and add compliance resolution step ([f83dd1d](https://github.com/aergaroth/openjobseu/commit/f83dd1d98c07dc645cf24d66a2f943ac9abe607c))
* **policy-v2:** add deterministic geo classifier and geo signal data ([375c488](https://github.com/aergaroth/openjobseu/commit/375c48885a277025964bd91d5dcff1366c519c01))
* **policy-v2:** introduce remote classifier and metrics wiring ([2fcecb9](https://github.com/aergaroth/openjobseu/commit/2fcecb9f759a250cba393ca4adc2fc67965e7833))
* **policy:** introduce policy v1 and global enforcement (remote purity + geo restrictions) ([fee8e3f](https://github.com/aergaroth/openjobseu/commit/fee8e3fed792de048fbb2f0472bc70af6afb59e7))
* refactor employer ingestion process with modular functions and enhanced metrics tracking ([9100545](https://github.com/aergaroth/openjobseu/commit/9100545a73643c76c37e9754350f20c0429c4726))
* refactor ingestion logic by removing legacy adapters and scripts, and enhance local job loading functionality ([acaf7fc](https://github.com/aergaroth/openjobseu/commit/acaf7fcf30e9a9b71ba083443490acd7e5ac8ace))
* Refactor job lifecycle and availability status ([2716301](https://github.com/aergaroth/openjobseu/commit/27163015dc3e23c5993678d7c78bf5a4df0fd6f8))
* Refactor salary extraction logic and introduce currency handling ([741f2b3](https://github.com/aergaroth/openjobseu/commit/741f2b333e89b1e6881ad84e1450ac3de6b2b2dc))
* Refactor task management and introduce frontend export functionality ([9e95c8d](https://github.com/aergaroth/openjobseu/commit/9e95c8d4d17fe94b44df89b0ff35b2da00163ec7))
* release OpenJobsEU 2.0 with modular ATS/compliance refactor ([a450632](https://github.com/aergaroth/openjobseu/commit/a450632d7ed7aa62ebb26cd8ac93895980922100))
* remove most literals from runtime to domain defined ([7fcfdc1](https://github.com/aergaroth/openjobseu/commit/7fcfdc122840d87f5d86c68e3ccc9f2fd2bd20d6))
* Rename columns in salary_parsing_cases for clarity and consistency ([fe2d81d](https://github.com/aergaroth/openjobseu/commit/fe2d81d4e8bbf8c6497e3225bf408cfc70471998))
* **runtime:** extend ingestion pipeline with additional source ([71599f4](https://github.com/aergaroth/openjobseu/commit/71599f4e94d6504f0a4d39dfbf783156b8a5d9e8))
* **runtime:** migrate OpenJobsEU from SQLite to PostgreSQL ([d7ce5e9](https://github.com/aergaroth/openjobseu/commit/d7ce5e9417448b7a594abe96bc916b0fb9daad05))
* **snapshot:** add job snapshots table and implement snapshotting on job updates ([856acaa](https://github.com/aergaroth/openjobseu/commit/856acaa52f2d0a0cb8c23f1841707a78796175e4))
* **storage:** derive/persist remote+geo classes and bootstrap missing compliance ([66dabb3](https://github.com/aergaroth/openjobseu/commit/66dabb309d2d3f332dc588443683f0e2832c2bc4))
* **storage:** migrate storage layer from SQLite to PostgreSQL ([6a9b616](https://github.com/aergaroth/openjobseu/commit/6a9b6163ae2d8be21fd6f4e0381840ae75cd0900))
* **taxonomy:** implement job taxonomy classification and quality scoring ([66409a7](https://github.com/aergaroth/openjobseu/commit/66409a7c7dcd4f7988d415c6954011cd9fa62c6d))
* **tests:** enhance test coverage and structure across various modules ([388e039](https://github.com/aergaroth/openjobseu/commit/388e039ab7b59452b019bf1df05f632d9cc21698))
* **tick-dev:** add authorization header for gcloud commands and improve error handling ([510040a](https://github.com/aergaroth/openjobseu/commit/510040a2af02993b51959377bbcbd7d689db557e))
* update access requirements for discovery and backfill endpoints ([fd50a50](https://github.com/aergaroth/openjobseu/commit/fd50a50089d769c4a1e334bdefb43fba43e9cbd6))
* update normalize function to accept Any type and ensure string conversion ([4f2106f](https://github.com/aergaroth/openjobseu/commit/4f2106f55ef62f709fd38a84b4d4ae28d9c66daf))
* use BASE_URL environment variable for tick handler URL construction ([3d9ec13](https://github.com/aergaroth/openjobseu/commit/3d9ec13b82263ea54da4fc5d2aeaf2f3ea3747bc))


### Bug Fixes

* add IF NOT EXISTS to ALTER TABLE and CREATE INDEX statements in migration scripts ([af1d63f](https://github.com/aergaroth/openjobseu/commit/af1d63f4978ac9f8c7c88886e672bf6a2b69bdae))
* add missing token for PR in release-please.yml ([083a039](https://github.com/aergaroth/openjobseu/commit/083a0399d0102e9d639d6aaf40185870f3e7566c))
* add target-branch to release-please.yml and define project metadata in pyproject.toml ([a111fe6](https://github.com/aergaroth/openjobseu/commit/a111fe62be8991b8e302257ba94804a1ee927c31))
* added required envs ([8c33335](https://github.com/aergaroth/openjobseu/commit/8c3333565be4a1ddb5a2cef7a9a583093c1f1322))
* **alembic:** safely enable pg_trgm extension with error handling for permissions ([bda56af](https://github.com/aergaroth/openjobseu/commit/bda56afb43b83972b2fc55ebce34a11613fe000f))
* align image tagging between build and Cloud Run deploy ([4a8816f](https://github.com/aergaroth/openjobseu/commit/4a8816f2e283fc6dbf8786eeca8ef8a6610a011b))
* **api:** imports after use ([fdbe873](https://github.com/aergaroth/openjobseu/commit/fdbe8736e3da7c3c8a38d28fbc7cb86d2a307a01))
* **api:** register CORS middleware after app initialization ([f096a74](https://github.com/aergaroth/openjobseu/commit/f096a741785e7dad6cbb9377343ab2a9aedc9dd9))
* **auth:** refine OAuth scope to include only 'openid' and 'email' ([bda56af](https://github.com/aergaroth/openjobseu/commit/bda56afb43b83972b2fc55ebce34a11613fe000f))
* change old (v2) remote mappings ([48eceb2](https://github.com/aergaroth/openjobseu/commit/48eceb250ea3bba24ba48d3b3555aaf6c72ed7be))
* change remote mappings ([4548a72](https://github.com/aergaroth/openjobseu/commit/4548a72d305e1c8b92327fdccf6bebda2f99302a))
* cleanup actions in logs - remove unused from post_ingestion ([667a4f2](https://github.com/aergaroth/openjobseu/commit/667a4f26534d7b39ccffbd9807a40c927e895c7d))
* **cloudrun:** keep listener up while DB bootstrap retries in background ([473ea90](https://github.com/aergaroth/openjobseu/commit/473ea90b500e852839d7172c4cf9d52318144e7b))
* correct dict unpacking in scheduler tick response ([f460b7a](https://github.com/aergaroth/openjobseu/commit/f460b7adce9e8e240fa40cc3581446feb5858196))
* Correct indentation in ATSAdapter constructor and update session headers ([810ea27](https://github.com/aergaroth/openjobseu/commit/810ea27e8a7cefcdc8e35f1bf3453358bc6a2305))
* correct runtime dependencies in requirements ([e80a9dd](https://github.com/aergaroth/openjobseu/commit/e80a9ddec8fb758609070a1e8b34e905c3fef759))
* corrected bucket name ([d6828fd](https://github.com/aergaroth/openjobseu/commit/d6828fd47fa019b1f9266cfeb3c441951dc0ecf8))
* corrected bucket name, after tests ([f19f0fe](https://github.com/aergaroth/openjobseu/commit/f19f0fe00747a3acca8cf625ab188400e07d1f0f))
* **cors:** enable OPTIONS method for public feed ([c8b8e86](https://github.com/aergaroth/openjobseu/commit/c8b8e8681e052e0fd4c3ce0a658709885e7b0474))
* debuging for GCP secrets ([60572c0](https://github.com/aergaroth/openjobseu/commit/60572c03e6d437b91e7bcb6aa5acb8edccf22701))
* disable SSL warnings and update requests to ignore certificate verification ([30943e1](https://github.com/aergaroth/openjobseu/commit/30943e19badb7cdbfae364426ce479929ea52f1d))
* enforce text response format for tick-dev endpoint ([1cf6350](https://github.com/aergaroth/openjobseu/commit/1cf63508a26575191effbcf13b885925d8c08a47))
* ensure ALTER TABLE statements check for existence of job_snapshots ([14636b3](https://github.com/aergaroth/openjobseu/commit/14636b3422f0cd6bc7a8b9079e95233ae9961e85))
* **frontend:** align feed preview with public jobs/feed v1 contract ([f84cb4e](https://github.com/aergaroth/openjobseu/commit/f84cb4ec6827e52e9ee494c767964d88ad9a467d))
* **frontend:** correct feed JSON contract ([b7fcde3](https://github.com/aergaroth/openjobseu/commit/b7fcde35dfa9738717a19dd53176fc658f021fb9))
* **frontend:** move inline styles to external stylesheet (CSP-safe) ([a98ea17](https://github.com/aergaroth/openjobseu/commit/a98ea178765dc8c339604f6b2cccf7319caebefb))
* handle millisecond timestamps in normalize_source_datetime function ([4dfa4f0](https://github.com/aergaroth/openjobseu/commit/4dfa4f09a793b15e805e5fd280e2cca66f7ca9eb))
* handle response types in run_tick_from_audit endpoint ([ffa7631](https://github.com/aergaroth/openjobseu/commit/ffa763145e4e24b514f2ff60adc4d9a5117776c4))
* import DB helpers in availability and lifecycle pipelines ([c867e87](https://github.com/aergaroth/openjobseu/commit/c867e87c2b5990276df07b84afda302e28bc3957))
* increase memory limit for Cloud Run service to 1024Mi and remove unused merge.py file ([492b4b1](https://github.com/aergaroth/openjobseu/commit/492b4b1a7be771b8d597d29d4b6c843b0884a6ed))
* indentation int tick.py ([43c75af](https://github.com/aergaroth/openjobseu/commit/43c75afd8dbfdf086cc69c4c626b25dd8479498e))
* **ingestion:** align RemoteOkApiAdapter class name with imports ([b8c5e21](https://github.com/aergaroth/openjobseu/commit/b8c5e21787813c7650fbaa51dedc81216642ce3d))
* **ingestion:** Log unhandled exceptions during employer ingestion ([aa6ab85](https://github.com/aergaroth/openjobseu/commit/aa6ab85c4cd37f1474f037203216d659178df9a8))
* initialize db before tests ([fce9f9b](https://github.com/aergaroth/openjobseu/commit/fce9f9b2879e39d1ff2513393b3b9f7d21692141))
* **logging:** standardize logger name in backfill compliance and salary modules ([e3eddc2](https://github.com/aergaroth/openjobseu/commit/e3eddc22ba41d9a164c475feb7902063b7153e31))
* **logging:** update json formatter test to assert 'severity' instead of 'level' ([0c79e2b](https://github.com/aergaroth/openjobseu/commit/0c79e2bc2400b0bd26433c5b68e2f38da13b7492))
* make ttl-based stale status effective in availability checker ([a833344](https://github.com/aergaroth/openjobseu/commit/a833344bbd3a61800b08c11282d615cdbebb7e70))
* **migrations:** remove pgcrypto dependency for Neon compatibility ([772a930](https://github.com/aergaroth/openjobseu/commit/772a93032ab3b419be886ea97c54c6d4aba9b5f5))
* missed collon in internal.py ([a79a807](https://github.com/aergaroth/openjobseu/commit/a79a80776811daa0617be1e385c0026e33c4371c))
* missing requirements ([0145258](https://github.com/aergaroth/openjobseu/commit/0145258d9ad6357b9d47de85dd4637b5d8f90076))
* move normalization to valid layer and added test to avoid messing normalization with adapters ([994116e](https://github.com/aergaroth/openjobseu/commit/994116e4e09d60f62604c5f038071120c937cc78))
* move service_account to templane for newer provider ([67b056d](https://github.com/aergaroth/openjobseu/commit/67b056dbf8afede54081994921c47e3e064cd306))
* moved RSS_URL from worker to adapter ([d00ef38](https://github.com/aergaroth/openjobseu/commit/d00ef384b79088f20ff27b0901ffa707aa5f013e))
* **policy:** adjust geo detection + harden feed audit script ([b8eb53a](https://github.com/aergaroth/openjobseu/commit/b8eb53aa28d2e3d27ec68baf1e4281f32d3c7cf8))
* provide TF_VARS for workflow ([097a242](https://github.com/aergaroth/openjobseu/commit/097a2425914d36c306c18a6c9e71e23808d718ea))
* refactor import statements and enhance test coverage for maintenance pipeline ([b464344](https://github.com/aergaroth/openjobseu/commit/b4643448c563588c2818531a2ed44ba45a46528e))
* remove old (unused) helper ([660391c](https://github.com/aergaroth/openjobseu/commit/660391c2508122b5cf8a8f51162677da7023b95b))
* remove unused taskName extra field from logs ([6a0027a](https://github.com/aergaroth/openjobseu/commit/6a0027a8276826dfb69b97af825b9c7fdb368bc6))
* removed post_ingestion() call arg. - refactored previously ([7293e39](https://github.com/aergaroth/openjobseu/commit/7293e398fdfb46f403ebb78d5be6722180621440))
* renamed field in DB in exmaple test ([6fc8398](https://github.com/aergaroth/openjobseu/commit/6fc8398d660cede5c7fcf4fef3624c2c24f21279))
* **salary_extraction, db_migration:** Correct salary max calculation and update salary field types ([c4332c0](https://github.com/aergaroth/openjobseu/commit/c4332c023062a54e73b681aace43771f26d5c1c2))
* secure ingestion worker, check if compliance is initiated before apply, secure policy engine ([6f99079](https://github.com/aergaroth/openjobseu/commit/6f99079c11c86c5808c8d023da60f1e6c948fc5a))
* **startup:** fail fast when DB bootstrap or migrations fail ([8a94e73](https://github.com/aergaroth/openjobseu/commit/8a94e73777521a0532caf085356b9339cadee740))
* **storage:** initialize sqlite schema on app startup ([7cb0f13](https://github.com/aergaroth/openjobseu/commit/7cb0f13d852ca15ae411110d857e7877abb3db1b))
* **storage:** resolve sqlite db path at runtime to fix CI tests ([0e916dd](https://github.com/aergaroth/openjobseu/commit/0e916ddb263c146efc43f7bacbbf16cafcda1edd))
* **tests:** update ingestion mock to return adapter instance ([bf59f87](https://github.com/aergaroth/openjobseu/commit/bf59f870d40f132ce6b7f4ec1dc718a121f01603))
* tick orchestration: ([7f65db5](https://github.com/aergaroth/openjobseu/commit/7f65db5a1d107f0be3ae901b7182bed5edd636a2))
* tick-dev.sh script could be run in other shell than bash ([3b62888](https://github.com/aergaroth/openjobseu/commit/3b628886971adcdd57648b353025827932cf3e9a))
* **tick:** render source metrics for flat ingestion payload format ([483db24](https://github.com/aergaroth/openjobseu/commit/483db24f48a307b2e64f65017ead07a8ba3e2ba0))
* typo - space afer backslash ([219554c](https://github.com/aergaroth/openjobseu/commit/219554c04fe4ec470064d00d49b70b40829b35c3))
* typo in requirements.txt ([b51dc40](https://github.com/aergaroth/openjobseu/commit/b51dc409ad82ae900289b97e8062f75c429e5e62))
* update Alembic stamp revision to specific commit for database migration ([147839e](https://github.com/aergaroth/openjobseu/commit/147839eb4f4e8a973d2d036c53d502283c8a4447))
* update branch from main to develop in release-please.yml and add release-please manifest ([574d557](https://github.com/aergaroth/openjobseu/commit/574d55717680ec781202191ff0776bcbf5d7e0ff))
* update comment in Dockerfile ([9f3a482](https://github.com/aergaroth/openjobseu/commit/9f3a4828d0cb5d708737d23470b002be23fcdd61))
* update conditional for build-deploy-dev job to exclude main branch in pull requests ([5ed063a](https://github.com/aergaroth/openjobseu/commit/5ed063a7141309386339a2dd6b5ac3ba86c01e2b))
* update job processing to handle rejected jobs and adjust compliance reporting ([625f230](https://github.com/aergaroth/openjobseu/commit/625f230a161a1ba290a2137feb774fae39987c98))
* update missing logg info for employer ingestion ([5af2e1e](https://github.com/aergaroth/openjobseu/commit/5af2e1e2e730ee9ea0d38aedfbeec0bdc1feffc5))
* update pull request conditions for dev and prod workflows to improve branch handling ([e82f2e0](https://github.com/aergaroth/openjobseu/commit/e82f2e04a1b22d1f2ad74c539bdd9df97fe4e38c))
* Update README badge and refactor ATSAdapter for requests session ([8ab5239](https://github.com/aergaroth/openjobseu/commit/8ab523927237ed6312fc1d71533df0f497f4d71a))


### Documentation

* add ci status badge ([8f34612](https://github.com/aergaroth/openjobseu/commit/8f346120895479bb67ccebd993accff00252e6d6))
* add content quality & policy v1 milestone to roadmap ([f9fb2c1](https://github.com/aergaroth/openjobseu/commit/f9fb2c1df7f220428ddd6bc4aa6a4c23bf9aa1b7))
* add system architecture and design rationale ([0440aaa](https://github.com/aergaroth/openjobseu/commit/0440aaabcb34532a9b6d4ae1c018e78abf524029))
* added hint in ARCHITECTURE.md ([1bb8df1](https://github.com/aergaroth/openjobseu/commit/1bb8df1785db22e07f21a25c4981234959de8c25))
* added short hit for Terraform .tfvars file ([c2d45a6](https://github.com/aergaroth/openjobseu/commit/c2d45a62dc3bf22b4be295a834020e576f47ff09))
* added site url ([c7195da](https://github.com/aergaroth/openjobseu/commit/c7195dadefc906d87865695e86be3a320edc70aa))
* align project documentation with current MVP implementation ([24edc13](https://github.com/aergaroth/openjobseu/commit/24edc13f737a641f968f600730abe8eed5972890))
* canonical model to match current state ([599e7ce](https://github.com/aergaroth/openjobseu/commit/599e7ce5a434de843d40890aa606d33d3dbfad66))
* clarify procject direction ([f8c682a](https://github.com/aergaroth/openjobseu/commit/f8c682a2f36d934d03afe6842c1482df9b0894e8))
* clean up roadmap after MVP v1 completion ([ba7ba32](https://github.com/aergaroth/openjobseu/commit/ba7ba3259feb6ede5ca67c4e30f9fc2b57bd3471))
* current state in ROADMAP ([3b671fd](https://github.com/aergaroth/openjobseu/commit/3b671fd795ab869bf4de85a4f1a875e1c7a5df05))
* define canonical job model and lifecycle ([9726adf](https://github.com/aergaroth/openjobseu/commit/9726adf235c02ec15e26fa62fbf676d6e9b91771))
* edit architecture, to match the current state ([9225fd7](https://github.com/aergaroth/openjobseu/commit/9225fd7603601d60383426c80bc288be51fa834e))
* Example source information ([25d83df](https://github.com/aergaroth/openjobseu/commit/25d83df202a74c0f2ed546483c29dda7c68e6866))
* fix badge to point to prod environment ([47dbe9f](https://github.com/aergaroth/openjobseu/commit/47dbe9fcb90b127786614f7e840f054af35dc643))
* fix typo ([9aa9fe0](https://github.com/aergaroth/openjobseu/commit/9aa9fe06e90078e393bf7cfc5006c89b12876efd))
* refresh ROADMAP ([9612da5](https://github.com/aergaroth/openjobseu/commit/9612da50931cb25e16dc7f0b23e6c52e0b1ec216))
* resize architecture diagram ([5f34b03](https://github.com/aergaroth/openjobseu/commit/5f34b03a396862ff724eb5ac0e87488d9edcd055))
* sync documentation with current runtime ([351c28c](https://github.com/aergaroth/openjobseu/commit/351c28c89690be06ef0423e1d47e9e2dc7c3378c))
* update architecture diagram API naming ([2850311](https://github.com/aergaroth/openjobseu/commit/28503113650a5de2a44dd2b77bcf756fe2575fc1))
* Update architecture documentation to reflect new internal endpoint parameters ([2911758](https://github.com/aergaroth/openjobseu/commit/2911758c13cff54bb4b89bebfc9cf6e5d998bbfd))
* update documentation to match current state ([d543e42](https://github.com/aergaroth/openjobseu/commit/d543e422c86cd4df9fc1107f299532cafa7360f8))
* Update documentation to match the current state of project. ([4c50ade](https://github.com/aergaroth/openjobseu/commit/4c50ade91aa089288af1534492ea16f6e26042a1))
* update README and roadmap after A7 completion ([e5dc640](https://github.com/aergaroth/openjobseu/commit/e5dc64083dc881740c4aced5a7ba38bd1f0885a6))
* update README and roadmap after lifecycle and read API ([ee303d5](https://github.com/aergaroth/openjobseu/commit/ee303d58a2a1fec5667827d2520a06a44751fff5))
* update README with current architecture and ingestion flow ([6b04008](https://github.com/aergaroth/openjobseu/commit/6b04008d436dcff1caa8680585e0807cd73bdf0e))
* update README, ARCHITECTURE, CANONICAL_MODEL, COMPLIANCE, DATA_SOURCES, and ROADMAP for clarity and consistency ([679999f](https://github.com/aergaroth/openjobseu/commit/679999f6741706f39e2e7edb935d51417ee32e6c))

## [Unreleased] – develop → main (initial release)

### Added

#### Core platform
- Tick-based ingestion runtime (`POST /internal/tick?limit=X`) with text/JSON output formatting and pagination
- Support for batched Full Sync (`incremental=false`) via `scripts/tick-full-sync.sh` to gracefully bypass Cloud Run timeouts
- ATS adapter layer (`app/adapters/ats/`): `GreenhouseAdapter`, `LeverAdapter`, with `probe_jobs` support
- `PersonioAdapter` utilizing a robust streaming XML pull-parser (memory-safe, 10MB limit)
- Discovery pipeline: ATS guessing worker, ATS probe worker, careers-page crawler
- Async Background Tasks API (`/internal/tasks/*`) for long-running operations (backfills, discovery pipelines)

#### Compliance & classification
- Remote/geo classifiers (`geo`, `hard_geo`, `remote`) with EU-relevance scoring
- Enhanced Geo-classifier with direct mapping of EOG countries and major European cities from job titles and scope
- Compliance engine and resolver with scoring and startup backfill utilities
- Salary parser and structured salary model with currency normalisation
- HTML to Markdown description normalization engine (lists, bold, italics, links, blockquotes, headers)
- GIN (pg_trgm) indexing for ultra-fast, relevance-sorted fuzzy search across jobs and companies

#### Job lifecycle
- Job identity and deduplication layer
- Lifecycle transitions (`new → active → stale → expired → unreachable`)
- Availability worker and lifecycle worker

#### API
- Public endpoints: `GET /jobs` (with `?q=` fuzzy search), `GET /jobs/feed`, `GET /jobs/stats/compliance-7d`
- Internal/ops endpoints: `POST /internal/tick`, `GET /internal/audit`, audit stats endpoints, task cancellation
- Feed threshold: `min_compliance_score=80`, cached at `max-age=300`

#### Storage
- PostgreSQL schema with 16 incremental SQL migration files
- SQLAlchemy Core backend; supports `DB_MODE=standard` and `DB_MODE=cloudsql`
- Repositories for jobs, companies, audit, compliance, availability, and discovery
- Complete removal of the legacy `storage/db_logic.py` facade, adopting direct repository imports

#### Ops & CI/CD
- GitHub Actions workflows: `dev_flow.yml`, `prod_flow.yml`, `terraform-plan.yml`
- Terraform infrastructure for GCP (`infra/gcp/dev`, `infra/gcp/prod`) with Cloud Run and Cloud Scheduler
- Runtime-aware structured logging (text locally, JSON in containers)
- Full test suite (`validator/tests/`) strictly blocking unmocked external HTTP requests to prevent test hangs
- Heavily optimized Pytest DB fixtures (replacing structural `TRUNCATE CASCADE` with ultra-fast `DELETE` sweeps)
