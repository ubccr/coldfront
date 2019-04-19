# ColdFront Changelog

## [Unreleased]
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

[Unreleased]: https://github.com/ubccr/coldfront/compare/v0.0.1...HEAD
[0.0.1]: https://github.com/ubccr/coldfront/releases/tag/v0.0.1
