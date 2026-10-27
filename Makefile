EDITION ?= server
RUNNER  ?= vm
IMAGE   := tetronos-builder
RUN     := docker run --rm --privileged -v $(CURDIR):/src:ro -v $(CURDIR)/build:/build -v $(CURDIR)/out:/out \
           -e EDITION=$(EDITION) -e HOST_UID=$(shell id -u) -e HOST_GID=$(shell id -g)
VM      := scripts/vm.sh

.PHONY: iso vm-create vm-start vm-stop vm-shell vm-destroy docker-image clean distclean

iso:
ifeq ($(RUNNER),vm)
	$(VM) start
	$(VM) sync
	$(VM) ssh 'sudo env EDITION=$(EDITION) SRC=/home/builder/src WORKROOT=/var/tmp/build OUTDIR=/home/builder/out HOST_UID=$$(id -u) HOST_GID=$$(id -g) /home/builder/src/scripts/build.sh'
	$(VM) pull
else
	$(MAKE) docker-image
	mkdir -p build out
	$(RUN) $(IMAGE) /src/scripts/build.sh
endif

vm-create:
	$(VM) create
vm-start:
	$(VM) start
vm-stop:
	$(VM) stop
vm-shell:
	$(VM) ssh
vm-destroy:
	$(VM) destroy

docker-image:
	docker build -t $(IMAGE) builder

clean:
ifeq ($(RUNNER),vm)
	$(VM) ssh 'sudo rm -rf /var/tmp/build/$(EDITION)'
else
	docker run --rm --privileged -v $(CURDIR)/build:/build $(IMAGE) rm -rf /build/$(EDITION)
endif

distclean:
	rm -rf out

.PHONY: debs test-debs
debs:
	python3 packaging/build.py

test-debs: debs
	sh packaging/tests/test-debs.sh
