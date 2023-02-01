# ColdFront: A Step-by-Step Guide 

## Making sure your GitHub version control is setup
1. Install VSCode or a similar editor on your machine (add note about virtual machines)
2. Fork the ColdFront repo
3. Clone the repo on your machine (`git clone https://github.com/YourUsername/coldfront`)
4. Make sure git is installed on your machine
5. Change directories to the ColdFront folder (`cd coldfront`)
6. Add the remote repository to your git (`git remote add upstream https://github.com/ubccr/coldfront`)
7. Run `git remote -v` and ensure that the remote and origin repositories are correct
8. Run the following commands in order to make sure your branch is up-to-date
```
git checkout main
git fetch upstream
git merge upstream/main
```
(fetches and merges changes to CCR repo and brings them to your local computer)
```
git status 
```
(shows the difference, if any, between both repos)
```
git push origin main 
```
(pushes local changes to your GitHub repo)

## Starting the ColdFront server on your machine