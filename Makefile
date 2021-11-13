PRODIMAGE     = coldfront:latest
PRODBUILDARGS = --ssh default

DRFIMAGE      = coldfront
DRFBUILDARGS  = --ssh default
DRFFILE       = Dockerfile-ifx


DOCKERCOMPOSEFILE = docker-compose.yml
DOCKERCOMPOSEARGS =

help:
	@$(SPHINXBUILD) -M help "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)

.PHONY: test Makefile docs drf build clean
clean:
	find . -name "*.pyc" -print0 | xargs -0 rm -f
build: drf
drf:
	docker build -t $(DRFIMAGE) -f $(DRFFILE) $(DRFBUILDARGS) .

prod:
	./set-version.sh
	docker build -t $(PRODIMAGE) $(PRODBUILDARGS) .
up: drf
	docker-compose -f $(DOCKERCOMPOSEFILE) $(DOCKERCOMPOSEARGS) up
down:
	docker-compose -f $(DOCKERCOMPOSEFILE) down
up-local: drf
	docker-compose -f docker-compose-local.yml $(DOCKERCOMPOSEARGS) up
down-local:
	docker-compose -f docker-compose-local.yml down
run: drf
	docker-compose run $(DRFIMAGE) /bin/bash
test: drf
	docker run --rm -it -v `pwd`:/app $(DRFIMAGE) ./manage.py test -v 2
docs:
	docker-compose run $(DRFIMAGE) make html; docker-compose down

# Catch-all target: route all unknown targets to Sphinx using the new
# "make mode" option.  $(O) is meant as a shortcut for $(SPHINXOPTS).
%: Makefile
	@$(SPHINXAPIDOC) -e -M --force -o "$(SOURCEDIR)" fiine
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
