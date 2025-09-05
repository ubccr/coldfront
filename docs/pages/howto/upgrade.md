# Upgrade ColdFront

This howto guide demonstrates one way to upgrade your ColdFront codebase to the latest release or the `main` branch using `git`. 

## Git setup

You will need to set up two git remotes:

- `origin` -> Your organization's Git repo for ColdFront
- `upstream` -> `$ git remote add upstream https://github.com/ubccr/coldfront.git`

Next, you will want to have at least three git branches to work with:

- `<custom>` -> This is your default branch, containing your organization's ColdFront codebase
- `main` -> This branch tracks the `main` branch of the ColdFront project
- `staged_upgrade` -> This is based on your `custom` branch, used for resolving merge conflicts

```sh
# let's assume you only have a `main` branch and a `custom` branch
$ git checkout main

# pull in the latest changes
$ git pull upstream main
# or checkout a new tagged release
$ git tag -l
$ git checkout v1.x.x

$ git checkout custom

# make a new branch off of your `custom` branch
$ git checkout -b staged_upgrade
$ git merge main

# resolve any conflicts in your text editor
$ git commit -m "merge bring in latest changes"
```

The trickiest part of the process will be to resolve any conflicts from merging `main` into your `staged_upgrade` branch. This is where you want to make sure your local customizations are kept in tact from the upgrade. 

## Database Migrations

After your code is merged, migrate your database to accomodate changes to models:

```sh
# make sure you have activated your virtual environment
$ source .venv/bin/activate
$ coldfront makemigrations --merge
$ coldfront migrate
```

## Testing

Restart your server in your testing environment to confirm everything is working as expected. 

```
# either in a local dev environment
$ DEBUG=True uv run coldfront runserver
# or on a test server environment
$ sudo systemctl restart gunicorn
```

If everything looks good, merge your `staged_upgrade` branch into your default branch:

```sh
$ git checkout custom
$ git merge staged_upgrade
# update your remote
$ git push origin custom
$ git branch -d staged_upgrade
```

Your organization's ColdFront codebase should now have the latest updates from the upstream ColdFront project. If you want to enable some of the newest ColdFront features, you may need to [install](/install#installation-methods) newer packages.