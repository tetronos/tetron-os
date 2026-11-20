EDITION ?= server
FIRMWARE ?=
TAG     ?=
RUNNER  ?= vm
IMAGE   := tetronos-builder
RUN     := docker run --rm --privileged -v $(CURDIR):/src:ro -v $(CURDIR)/build:/build -v $(CURDIR)/out:/out \
           -e EDITION=$(EDITION) -e FIRMWARE=$(FIRMWARE) -e ISO_TAG=$(TAG) -e HOST_UID=$(shell id -u) -e HOST_GID=$(shell id -g)
VM      := scripts/vm.sh

.PHONY: iso iso-build vm-create vm-start vm-stop vm-shell vm-destroy docker-image clean distclean

# Whole build output to the terminal and out/logs/ (BuildLogsInOut); the
# exit status is the build's, not tee's. -fw follows build.sh: FIRMWARE=all on the
# server edition (the desktop has firmware always and no suffix).
iso:
	@mkdir -p out/logs; \
	fw=; case "$(FIRMWARE)/$(EDITION)" in all/server) fw=-fw ;; esac; \
	log=out/logs/make-iso-$(EDITION)$$fw$(if $(TAG),-$(TAG))-$$(date +%Y%m%d-%H%M%S).log; st=$$(mktemp); \
	echo "log: $$log"; \
	{ $(MAKE) --no-print-directory iso-build; echo $$? > $$st; } 2>&1 | tee $$log; \
	rc=$$(cat $$st); rm -f $$st; echo "log: $$log"; exit $$rc

iso-build: debs
ifeq ($(RUNNER),vm)
	$(VM) start
	$(VM) sync
	$(VM) ssh 'sudo env EDITION=$(EDITION) FIRMWARE=$(FIRMWARE) ISO_TAG=$(TAG) SRC=/home/builder/src WORKROOT=/var/tmp/build OUTDIR=/home/builder/out HOST_UID=$$(id -u) HOST_GID=$$(id -g) /home/builder/src/scripts/build.sh'
	$(VM) pull
	scripts/out-report.sh out
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

.PHONY: debs test-debs install-tui
# LOCAL_DEBS=DIR: test builds only, kind = deb packages are taken from DIR
# when it has their file name (build.py --local-debs); never for a release.
# Stopgap: the engine script and the static TUI come from the sibling repo.
INSTALL_REPO ?= $(HOME)/code/tetronos-install
install-tui:
	cd $(INSTALL_REPO) && cargo build --release --target x86_64-unknown-linux-musl
	install -m 0755 $(INSTALL_REPO)/target/x86_64-unknown-linux-musl/release/tetronos-install-tui packaging/files/tetronos-install/
	install -m 0755 $(INSTALL_REPO)/scripts/tetronos-install packaging/files/tetronos-install/

debs: install-tui
	python3 packaging/build.py $(if $(LOCAL_DEBS),--local-debs $(LOCAL_DEBS))

test-debs: debs
	python3 packaging/tests/test_build.py
	sh packaging/tests/test-debs.sh
