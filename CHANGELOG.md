# ColdFront Changelog

## [1.1.0] - 2022-02-08

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
[Unreleased]: https://github.com/ubccr/coldfront/compare/v1.1.0...HEAD
