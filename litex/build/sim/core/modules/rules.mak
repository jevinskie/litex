CC ?= gcc
OPT_LEVEL ?= O3
UNAME_S := $(shell uname -s)
UNAME_M := $(shell uname -m)

ifeq ($(UNAME_S),Darwin)
	ifeq ($(UNAME_M),x86_64)
		CFLAGS += -I/usr/local/include
		LDFLAGS += -L/usr/local/lib
	else
		CFLAGS += -I/opt/homebrew/include
		LDFLAGS += -L/opt/homebrew/lib
	endif
	LDFLAGS += -ljson-c
	CFLAGS += -Wall -$(OPT_LEVEL) -ggdb -fPIC
else
	CFLAGS += -Wall -$(OPT_LEVEL) -ggdb -fPIC -Werror
endif
LDFLAGS += -levent -shared -fPIC

MOD_SRC_DIR=$(SRC_DIR)/modules/$(MOD)
EXTRA_MOD_SRC_DIR=$(EXTRA_MOD_BASE_DIR)/$(MOD)

all: $(MOD).so

%.o: $(MOD_SRC_DIR)/%.c
	$(CC) -c $(CFLAGS) -I$(MOD_SRC_DIR)/../.. -o $@ $<

%.o: $(EXTRA_MOD_SRC_DIR)/%.c
	$(CC) -c $(CFLAGS) -I$(SRC_DIR) -o $@ $<

%.so: %.o
ifeq ($(UNAME_S),Darwin)
	$(CC) $(LDFLAGS) -o $@ $^
else
	$(CC) $(LDFLAGS) -Wl,-soname,$@ -o $@ $<
endif

# keep .o files around so debug info works on macOS
.PRECIOUS: %.o

.PHONY: clean
clean:
	rm -f *.o *.so
