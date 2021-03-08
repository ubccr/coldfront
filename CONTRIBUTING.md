Branching and Merging
This repo requires all changes to be done in a branch and then merged into the
production branch after review via a merge request. This enforces that the
validation and deployment steps have passed and executed cleanly before
allowing a merge to production.

Branching
In order to create a new branch, run:

    $ cd /path/to/coldfront
    $ git fetch origin
    $ git checkout -b $initials_$purpose origin/master
Now you can make and commit changes to the puppet codebase in your branch.

Branch Naming
Please use the following format:  $initials_$purpose


$initials: this is a consistent set of initials to map to you for alerting purposes.  E.g. Warren Frame uses wf

$purpose: the rest of your branch name, ideally related to what you intend to do

If this happens, simply rename your
branch and push again. For example, if you pushed branch my-new-branch you can
rename the branch using:

    $ git checkout -b my_new_branch my-new-branch`

Dont forget to clean up the branch with the invalid branch name! See the
Cleaning up section below for detailed instructions on deleting
branches.

Pushing and deploying
When you're ready to test your changes, simply push them to the upstream repo:

    $ git push origin example_branch

This will kick off an asynchronous gitlab pipeline which runs a number of
validation checks on your branch. Assuming those checks pass, your branch will
then be built and deployed on the production puppet servers under a new
environment with the same name as your branch.
Please pay attention to chat or the gitlab-int web interface for build
success/failure status.

