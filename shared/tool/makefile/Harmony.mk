# make/Harmony.mk - build *.lib.c and *.CLI.c
# written for the Harmony skeleton, always invoked from cwd  $REPO_HOME/<role>
# files have two suffixes by convention, e.g.: X.lib.c or Y.CLI.c
#
# One make reads three layers, each after the one before, so each can change
# what the layers before it set:
#
#   1. Harmony's defaults, in this file
#   2. the project's settings, tool/build_component/makefile
#   3. the namespace's settings, any *.mk beside its source
#
# A layer adds to a default with += and replaces one with :=. The flags the
# build itself depends on (dependency files, the global header, the source
# directory) are added after the layers, so replacing a default cannot remove
# them.
#
# The layers are read before the derived variables and the rules, because
# make expands those as it reads them. A rule a layer defines is read at that
# point too, so its targets and prerequisites cannot use the derived lists.

.SUFFIXES:
.DELETE_ON_ERROR:
.DEFAULT_GOAL := usage

#--------------------------------------------------------------------------------
# 1. Harmony's defaults

SHELL := /bin/bash

ECHO := printf "%b\n"

RT_MAKEFILE_DP := $(REPO_HOME)/shared/tool/makefile

# The build component supplies these on the environment, for the namespace
# being built; ?= keeps its values, and a layer can still replace them.
C_SOURCE_DIR     ?= authored
LIBRARY_DIR      ?= scratchpad/made
MACHINE_DIR      ?= scratchpad/made

C                := gcc
CFLAGS           := -std=gnu11 -Wall -Wextra -Wpedantic -finput-charset=UTF-8
LN_FLAGS         := -L/lib64 -L/lib

LIBRARY_NAME     := $(PROJECT)

BUILD_DIR        := scratchpad/build
OBJECT_DIR        = $(BUILD_DIR)/object

KMOD_SOURCE_DIR  ?= authored
KMOD_CCFLAGS     ?= -I $(KMOD_SOURCE_DIR)
# Pass the global header to Kbuild exactly as done for user-space
KMOD_CCFLAGS     += -include $(REPO_HOME)/shared/tool/makefile/RT_global.h
KMOD_OUTPUT_DIR  ?= scratchpad/kmod

#--------------------------------------------------------------------------------
# 2. the project's settings

include tool/build_component/makefile

#--------------------------------------------------------------------------------
# 3. the namespace's settings

-include $(wildcard $(C_SOURCE_DIR)/*.mk)

#--------------------------------------------------------------------------------
# derived variables

LIBRARY_NAME     := $(subst -,_,$(LIBRARY_NAME))
LIBRARY_FILE     := $(LIBRARY_DIR)/lib$(LIBRARY_NAME).a

# source discovery (single dir)
c_source_lib  := $(wildcard $(C_SOURCE_DIR)/*.lib.c)
c_source_exec := $(wildcard $(C_SOURCE_DIR)/*.CLI.c)

# remove suffix to get base name
c_base_lib  := $(sort $(patsubst %.lib.c,%, $(notdir $(c_source_lib))))
c_base_exec := $(sort $(patsubst %.CLI.c,%, $(notdir $(c_source_exec))))

# two sets of object files, one for the lib, and one for the CLI programs
object_lib  := $(patsubst %, $(OBJECT_DIR)/%.lib.o, $(c_base_lib))
object_exec := $(patsubst %, $(OBJECT_DIR)/%.CLI.o, $(c_base_exec))

# executables are made from exec_ sources
exec_ := $(patsubst %, $(MACHINE_DIR)/%, $(c_base_exec))

# A library's product is its archive, its interface and its settings: in the
# single-file C module the .lib.c is its own header, and a .mk holds what a
# program built against the library needs. Both are staged beside the
# archive, so promotion hands a consumer all three. A namespace that makes no
# library stages neither.
interface_ := $(if $(c_source_lib),$(patsubst $(C_SOURCE_DIR)/%,$(LIBRARY_DIR)/%,$(c_source_lib) $(wildcard $(C_SOURCE_DIR)/*.mk)))

# the flags the build depends on, after the layers
CFLAGS   += -MMD -MP
CFLAGS   += -include "$(REPO_HOME)/shared/tool/makefile/RT_global.h"
CFLAGS   += -I $(C_SOURCE_DIR)
# the project library is linked only when the namespace makes one
LN_FLAGS += -L$(LIBRARY_DIR) $(if $(object_lib),-l$(LIBRARY_NAME))

#--------------------------------------------------------------------------------
# pull in dependencies

-include $(object_lib:.o=.d) $(object_exec:.o=.d)


#--------------------------------------------------------------------------------
# targets

.PHONY: usage
usage:
	@printf "Usage: make [usage|version|information|all|library|lib|CLI|kmod|clean]\n"

.PHONY: version
version:
	@echo Harmony.mk version 9.0
	if [ ! -z "$(C)" ]; then $(C) -v; fi
	/bin/make -v
	@$(MAKE) --no-print-directory -f $(RT_MAKEFILE_DP)/target_kernel-module.mk version

# information and clean are double-colon rules, so the project's settings or a
# namespace's .mk can add a recipe of its own; each recipe runs.
.PHONY: information
information::
	@printf "· → Unicode middle dot - visible: [%b]\n" "·"
	@echo "REPO_HOME: " $(REPO_HOME)
	@echo "NAMESPACE: " $(NAMESPACE)
	@echo "C_SOURCE_DIR: " $(C_SOURCE_DIR)
	@echo "BUILD_DIR: " $(BUILD_DIR)
	@echo "LIBRARY_DIR: " $(LIBRARY_DIR)
	@echo "MACHINE_DIR: " $(MACHINE_DIR)
	@echo "makefiles read: " $(MAKEFILE_LIST)
	@echo "CFLAGS: " $(CFLAGS)
	@echo "LN_FLAGS: " $(LN_FLAGS)
	@echo "c_source_lib: " $(c_source_lib)
	@echo "c_source_exec: " $(c_source_exec)
	@echo "c_base_lib: " $(c_base_lib)
	@echo "c_base_exec: " $(c_base_exec)
	@echo "object_lib: " $(object_lib)
	@echo "object_exec: " $(object_exec)
	@echo "exec_: " $(exec_)
	@echo "interface_: " $(interface_)
	@$(MAKE) --no-print-directory -f $(RT_MAKEFILE_DP)/target_kernel-module.mk information

.PHONY: all
all: library CLI kmod

.PHONY: library lib
library lib: $(LIBRARY_FILE) $(interface_)

$(LIBRARY_FILE): $(object_lib)
	@mkdir -p $(LIBRARY_DIR)
	@if [ -s "$@" ] || [ -n "$(object_lib)" ]; then \
		echo "ar rcs $@ $^"; \
		ar rcs $@ $^; \
	else \
		rm -f "$@"; \
	fi

# each staged interface file depends on its source file of the same name
$(interface_): $(LIBRARY_DIR)/%: $(C_SOURCE_DIR)/%
	@mkdir -p $(LIBRARY_DIR)
	cp $< $@

.PHONY: CLI
CLI: library $(exec_)

# The kernel modules are built by a make of their own, which drives Kbuild.
# It defines targets of the same names as this file, so it is run, not
# included.
.PHONY: kmod
kmod:
	@$(MAKE) --no-print-directory -f $(RT_MAKEFILE_DP)/target_kernel-module.mk kmod

# generally better to use the project local clean scripts, but this will make it so that the make targets can be run again
.PHONY: clean
clean::
	rm -f $(LIBRARY_FILE) $(interface_)
	for obj in $(object_lib) $(object_exec); do rm -f $$obj $${obj%.o}.d || true; done
	for i in $(exec_); do [ -e $$i ] && rm $$i || true; done
	rm -rf $(BUILD_DIR)
	@$(MAKE) --no-print-directory -f $(RT_MAKEFILE_DP)/target_kernel-module.mk clean


# recipes

$(OBJECT_DIR)/%.o: $(C_SOURCE_DIR)/%.c
	@mkdir -p $(OBJECT_DIR)
	$(C) $(CFLAGS) $(if $(findstring .lib,$@),-D$(if $(NAMESPACE),$(NAMESPACE)·,)$(basename $*)) -o $@ -c $<

$(MACHINE_DIR)/%: $(OBJECT_DIR)/%.CLI.o
	@mkdir -p $(MACHINE_DIR)
	$(C) -o $@ $< $(LN_FLAGS)
