# developer/tool/build_component/makefile
#
# The project's make settings, for every namespace the project builds with
# make. Harmony.mk includes this file after its own defaults and before the
# namespace's *.mk files, which have the last say. This file holds settings,
# not rules for building: Harmony.mk has those.
#
# Add to a default with +=, replace one with :=, for example:
#
#   CFLAGS   += -O2
#   LN_FLAGS += -lm
#
# Settings for one namespace go in a .mk file beside its source instead, such
# as authored/<namespace>.make/<namespace>.mk. That file is also staged and
# promoted with the namespace's library, so a project built against the
# library reads the same settings.
#
# Harmony.mk's information and clean are double-colon rules, so a recipe
# added here as 'information::' or 'clean::' runs as well as Harmony.mk's.
# Make runs them in the order it read them, so this file's runs first.
