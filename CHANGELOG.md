# ColdFront Changelog

## [Unreleased]

## [1.0.4] - 2021-03-25

- Fix [#235](https://github.com/ubccr/coldfront/issues/235)
- Fix [#271](https://github.com/ubccr/coldfront/issues/271)
- Fix [#279](https://github.com/ubccr/coldfront/issues/279)
- Add LDAP User Search plugin configs

## [1.0.3] - 2021-03-02

- Refactor ColdFront settings. See [PR #264](https://github.com/ubccr/coldfront/pull/264)
- Lots of documenation updates. [See here](https://coldfront.readthedocs.io)
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
[Unreleased]: https://github.com/ubccr/coldfront/compare/v1.0.4...HEAD
