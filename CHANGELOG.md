# ColdFront Changelog

## [1.1.7] - 2025-07-22

- Automatically change default Slurm account if removal causes conflicts [#597](https://github.com/ubccr/coldfront/pull/597)
- Fix allocation request list displays incorrect date for allocation renewals [#647](https://github.com/ubccr/coldfront/issues/647)
- Add allocation limits for a resource [#667](https://github.com/ubccr/coldfront/pull/667)
- Add REST API [#632](https://github.com/ubccr/coldfront/pull/632)
- Migrate to UV [#677](https://github.com/ubccr/coldfront/pull/677)
- Add EULA enforcement [#671](https://github.com/ubccr/coldfront/pull/671)
- Contiguous Internal Project ID [#646](https://github.com/ubccr/coldfront/pull/646)
- Add auto-compute allocation plugin [#698](https://github.com/ubccr/coldfront/pull/698)
- Add project openldap plugin [#696](https://github.com/ubccr/coldfront/pull/696)
- Add institution feature [#670](https://github.com/ubccr/coldfront/pull/670)
- Update Dockerfile [#715](https://github.com/ubccr/coldfront/pull/715)

## [1.1.6] - 2024-03-27

- Upgrade to Django 4.2 LTS [#601](https://github.com/ubccr/coldfront/pull/601)
- Update python version in Dockerfile to 3.8 [#578](https://github.com/ubccr/coldfront/pull/578)
- Add factoryboy Project and Allocation unit tests [#546](https://github.com/ubccr/coldfront/pull/546)
- Add docs for configuring LDAP auth against Active Directory [#556](https://github.com/ubccr/coldfront/pull/556)
- Fix grants formatting error [#442](https://github.com/ubccr/coldfront/issues/442)
- Add docs on creating a plugin [#472](https://github.com/ubccr/coldfront/issues/472)
- Add justification to allocation invoices [#305](https://github.com/ubccr/coldfront/issues/305)
- Add docs on configuring generic OIDC auth [#528](https://github.com/ubccr/coldfront/pull/528)
- Fix bug where notifications were auto-enabled user role changed [#457](https://github.com/ubccr/coldfront/issues/457)
- Add LDAP user search custom mapping and TLS support [#545](https://github.com/ubccr/coldfront/pull/545)
- Add docs on `collect static` for `SITE_STATIC` usage [#358](https://github.com/ubccr/coldfront/issues/358)
- Add signal for new allocation requests [#549](https://github.com/ubccr/coldfront/pull/549)

## [1.1.5] - 2023-07-12

- SECURITY BUG FIX: Unprotected eval when adding publication. [#551](https://github.com/ubccr/coldfront/pull/551)
- Documentation improvements

## [1.1.4] - 2023-02-11

- Datepicker changed to flatpickr. Remove jquery-ui [#438](https://github.com/ubccr/coldfront/issues/438)
- Combined email expiry notifications [#413](https://github.com/ubccr/coldfront/pull/413)
- Remove obsolete arguments in signal defs [#422](https://github.com/ubccr/coldfront/pull/422)
- Allow sorting of users on detail page [#408](https://github.com/ubccr/coldfront/issues/408)
- Fix approve button deleting description text [#433](https://github.com/ubccr/coldfront/issues/433)
- Add Project Attributes [#466](https://github.com/ubccr/coldfront/pull/466)
- Slurm plugin: fix allocations in pending renewal status [#176](https://github.com/ubccr/coldfront/issues/176)
- Update list displayes to sort case insensitive throughout front end [#393](https://github.com/ubccr/coldfront/issues/393)
- Fix FreeIPA plugin not recognizing usernames greater than 11 characters [#416](https://github.com/ubccr/coldfront/issues/416)
- Send signal if allocation status is revoked [#474](https://github.com/ubccr/coldfront/issues/474)
- Upgrade to Django 3.2.17
- Allow configuration of session timeout [#452](https://github.com/ubccr/coldfront/issues/452)
- Increase max length for user first_name [#490](https://github.com/ubccr/coldfront/pull/490)

## [1.1.3] - 2022-07-07

- Fix erronous allocation change request error message [#428](https://github.com/ubccr/coldfront/issues/428)
- Upgrade bootstrap and move to static assets [#405](https://github.com/ubccr/coldfront/issues/405) 
- Allow changes on allocations in the test dataset
- Add new ColdFront logos and branding [#431](https://github.com/ubccr/coldfront/pull/431)

## [1.1.2] - 2022-07-06

- Fix "Select all" toggle for allocations [#396](https://github.com/ubccr/coldfront/issues/396) 
- Fixed allocation expiration task bug [#401](https://github.com/ubccr/coldfront/pull/401)
- Fix new user sorting [#395](https://github.com/ubccr/coldfront/issues/395) 
- Fix allocation approved status [#379](https://github.com/ubccr/coldfront/issues/379) 
- Add notes on project detail page [#194](https://github.com/ubccr/coldfront/issues/194) 
- Add partial match for attribute search  [#421](https://github.com/ubccr/coldfront/pull/421)
- Fix miscellaneous config issues [#414](https://github.com/ubccr/coldfront/issues/414) 
- Upgrade to Django 3.2.14

## [1.1.1] - 2022-04-26

- Fix grant export to only download those found under search [#222](https://github.com/ubccr/coldfront/issues/222) 
- Fix bug that allowed users to be added to inactive allocations [#386](https://github.com/ubccr/coldfront/issues/386)
- Fix allocation request approval redirect [#388](https://github.com/ubccr/coldfront/issues/388)
- Upgrade to Django 3.2.13
- Fix bug in slurm plugin where `SLURM_NOOP` was a str instead of a bool [#392](https://github.com/ubccr/coldfront/pull/392)

## [1.1.0] - 2022-03-09

- Add a checkbox to 'select all' users on the project to enable/disable notifications [#291](https://github.com/ubccr/coldfront/issues/291)
- Archived grant not viewable by PI [#259](https://github.com/ubccr/coldfront/issues/259)
- Add more detail info when multiple allocations on a project for same resource [#193](https://github.com/ubccr/coldfront/issues/193)
- Admins can prevent the renewal of allocations [#203](https://github.com/ubccr/coldfront/issues/203)
- Allow logout redirect URL to be configured [#311](https://github.com/ubccr/coldfront/pull/311)
- Fix empty user search exception [#313](https://github.com/ubccr/coldfront/issues/313)
- Add allocation change requests [#294](https://github.com/ubccr/coldfront/issues/294)
- Added signal dispatch for resource allocations [#319](https://github.com/ubccr/coldfront/pull/319)
- mokey oidc plugin: Handle groups claim as list [#332](https://github.com/ubccr/coldfront/pull/332)
- Fix divide by zero error when attribute that has 0 usage [#336](https://github.com/ubccr/coldfront/issues/336)
- Allocation request flow updates [#341](https://github.com/ubccr/coldfront/issues/341) 
- Add attribute expansion support [#324](https://github.com/ubccr/coldfront/pull/324)
- Fix adding not-selected publications [#343](https://github.com/ubccr/coldfront/pull/343)
- Add forward filter parameters between active-archived projects search pages [#347](https://github.com/ubccr/coldfront/pull/347)
- Fix sorting arrows for allocation search [#344](https://github.com/ubccr/coldfront/pull/344)
- SECURITY BUG FIX: Check permissions on notification updates [#348](https://github.com/ubccr/coldfront/pull/348) 
- Allow site-level control of how resources ordered within an allocation [#334](https://github.com/ubccr/coldfront/issues/334)
- LDAP user search plugin: Add ldap connect timeout config option [#351](https://github.com/ubccr/coldfront/pull/351)
- Upgrade to Django v3.2 [#295](https://github.com/ubccr/coldfront/issues/295)
- Fix error on duplicate publication entry [#369](https://github.com/ubccr/coldfront/issues/369)
- Add resource list page [#323](https://github.com/ubccr/coldfront/issues/322)
- Add resource detail page [#320](https://github.com/ubccr/coldfront/issues/320)
- Fix adding publications with large number of authors [#283](https://github.com/ubccr/coldfront/issues/283)
- Allow allocation users to see allocations of all statuses [#292](https://github.com/ubccr/coldfront/issues/292)
- Show allocations for both Active and New projects [#365](https://github.com/ubccr/coldfront/pull/365)

## [1.0.4] - 2021-03-25

- Slurm plugin: disabled resource should not show up in slurm files [#235](https://github.com/ubccr/coldfront/issues/235)
- Fix ldap config [#271](https://github.com/ubccr/coldfront/issues/271)
- Add sample csv data to pip packaging [#279](https://github.com/ubccr/coldfront/issues/279)
- Add LDAP User Search plugin configs

## [1.0.3] - 2021-03-02

- Refactor ColdFront settings [#264](https://github.com/ubccr/coldfront/pull/264)
- Lots of documenation updates now hosted on readthedocs. [see here](https://coldfront.readthedocs.io)
- Fix setuptools for pip installs

## [1.0.2] - 2021-02-15

- Accessibility fixes @zooley
- OnDemand integration (adds link to ondemand)
- Bug/Issue fixes

## [1.0.1] - 2020-07-17

- Add test data
- Fixed subscription breakdown by status plot failing due to missing resource
- Add links to all projects and subscriptions for admin and director 
- Move template inside email conditional.
- Remove django-hijack. Switch to using django-su. Fixes #85
- Add freeipa consistency checker command line tool
- Add freeipa ldap user search
- Limit freeipa LDAP searching to enabled users
- Limit local searches to active users
- Add functionality to send automated nightly email for expiring and just expired subscription
- Set default status to active when adding users to subscriptions
- Make project review functionality optional 
- Add functionality to run functions on subscription expire
- Rename `delete` user to `remove` user in subscription
- Add ability to specify if subscriptions can be renewed
- Remove `inactive` status and replace it with `renewal requested` status for subscriptions
- Add optional description field to subscription model. This will allow distinguishing between subscriptions with the same resources.
- Fixed archived projects requiring project review
- Move is_private from SubscriptionAttribute to SubscriptionAttributeType
- Show expired subscription on project detail page. Subscriptions are sorted by end date, so expired subscriptions will be at the bottom. 

## [0.0.1] - 2018-10-03

- Initial release

[0.0.1]: https://github.com/ubccr/coldfront/releases/tag/v0.0.1
[1.0.1]: https://github.com/ubccr/coldfront/releases/tag/v1.0.1
[1.0.2]: https://github.com/ubccr/coldfront/releases/tag/v1.0.2
[1.0.3]: https://github.com/ubccr/coldfront/releases/tag/v1.0.3
[1.0.4]: https://github.com/ubccr/coldfront/releases/tag/v1.0.4
[1.1.0]: https://github.com/ubccr/coldfront/releases/tag/v1.1.0
[1.1.1]: https://github.com/ubccr/coldfront/releases/tag/v1.1.1
[1.1.2]: https://github.com/ubccr/coldfront/releases/tag/v1.1.2
[1.1.3]: https://github.com/ubccr/coldfront/releases/tag/v1.1.3
[1.1.4]: https://github.com/ubccr/coldfront/releases/tag/v1.1.4
[1.1.5]: https://github.com/ubccr/coldfront/releases/tag/v1.1.5
[1.1.6]: https://github.com/ubccr/coldfront/releases/tag/v1.1.6
[1.1.7]: https://github.com/ubccr/coldfront/releases/tag/v1.1.7
[Unreleased]: https://github.com/ubccr/coldfront/compare/v1.1.7...HEAD
