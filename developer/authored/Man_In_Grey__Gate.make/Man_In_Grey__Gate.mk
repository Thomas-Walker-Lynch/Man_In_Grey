# Man_In_Grey__Gate.mk
#
# The settings for building a gate on Man-In-Grey's general gate. Harmony.mk
# reads this file last when it builds this namespace, and stages it with
# libMan_In_Grey.a and Gate.lib.c, so promotion puts all three in
# consumer/Man_In_Grey__Gate/. An application builds its own gate by including
# the promoted copy from a .mk beside its gate's .CLI.c, for example:
#
#   include $(REPO_HOME)/shared/project-dependency/Man-In-Grey/Man_In_Grey__Gate/Man_In_Grey__Gate.mk
#
# or by linking to it under a name ending in .mk there.
#
# The directory of this file: the last makefile make has read is the one it
# is reading now, and := takes the value before this file includes anything.
# realpath follows a link to the file itself.
Man_In_Grey__Gate__dp := $(patsubst %/,%,$(dir $(realpath $(lastword $(MAKEFILE_LIST)))))

# A gate runs setuid, so it is built hardened.
CFLAGS   += -O2 -fstack-protector-strong -U_FORTIFY_SOURCE -D_FORTIFY_SOURCE=2
LN_FLAGS += -Wl,-z,relro -Wl,-z,now

# Where a gate built in another project finds Gate.lib.c and libMan_In_Grey.a.
# In Man-In-Grey's own build this is the source directory, and Harmony.mk
# finds both without it.
CFLAGS   += -I $(Man_In_Grey__Gate__dp)
LN_FLAGS += -L$(Man_In_Grey__Gate__dp) -lMan_In_Grey
