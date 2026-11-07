# developer/tool/build_component/makefile
.SUFFIXES:
.EXPORT_ALL_VARIABLES:

RT_MAKEFILE_DP := $(REPO_HOME)/shared/tool/makefile

# the setuid gate is built hardened
ifeq ($(NAMESPACE),Man_In_Grey_gate)
  CFLAGS_PROJECT_LOCAL  := -O2 -fstack-protector-strong -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=2
  LN_FLAGS_PROJECT_LOCAL := -Wl,-z,relro -Wl,-z,now
endif

.PHONY: usage 
usage:
	@printf "Usage: make [usage|version|information|all|lib|CLI|kmod|clean]\n"

.PHONY: version 
version:
	@printf "local ----------------------------------------\n"
	@echo tool/makefile version 2.0
	@printf "Harmony.mk ----------------------------------------\n"
	@$(MAKE) -f $(RT_MAKEFILE_DP)/Harmony.mk version
	@printf "target_kernel-module.mk ----------------------------------------\n"
	@$(MAKE) -f $(RT_MAKEFILE_DP)/target_kernel-module.mk version

.PHONY: information
information:
	@printf "local ----------------------------------------\n"
	-@echo CURDIR='$(CURDIR)'
	@echo REPO_HOME="$(REPO_HOME)"
	@echo NAMESPACE="$(NAMESPACE)"
	@echo C_SOURCE_DIR="$(C_SOURCE_DIR)"
	@echo KMOD_BUILD_DIR="/lib/modules/$(shell uname -r)/build"
	@echo CURDIR="$(CURDIR)"
	@printf "Harmony.mk ----------------------------------------\n"
	@$(MAKE) -f $(RT_MAKEFILE_DP)/Harmony.mk information
	@printf "target_kernel-module.mk ----------------------------------------\n"
	@$(MAKE) -f $(RT_MAKEFILE_DP)/target_kernel-module.mk information

.PHONY: all
all: library CLI kmod

.PHONY: library lib
library lib:
	@$(MAKE) -f $(RT_MAKEFILE_DP)/Harmony.mk library

.PHONY: CLI
CLI:
	@$(MAKE) -f $(RT_MAKEFILE_DP)/Harmony.mk CLI

.PHONY: kmod
kmod:
	@$(MAKE) -f $(RT_MAKEFILE_DP)/target_kernel-module.mk kmod

.PHONY: clean
clean:
	@printf "local ----------------------------------------\n"
	@printf "Harmony.mk ----------------------------------------\n"
	@$(MAKE) -f $(RT_MAKEFILE_DP)/Harmony.mk clean
	@printf "target_kernel-module.mk ----------------------------------------\n"
	@$(MAKE) -f $(RT_MAKEFILE_DP)/target_kernel-module.mk clean
