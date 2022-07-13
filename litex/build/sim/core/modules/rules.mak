CC ?= gcc
OPT_LEVEL ?= O3
UNAME_S := $(shell uname -s)

ifeq ($(UNAME_S),Darwin)
    CFLAGS += -I/usr/local/include/
    LDFLAGS += -L/usr/local/lib -ljson-c
    CFLAGS += -Wall -$(OPT_LEVEL) -ggdb -fPIC
else
    CFLAGS += -Wall -$(OPT_LEVEL) -ggdb -fPIC -Werror
endif
LDFLAGS += -ljson-c -levent -shared -fPIC

MOD_SRC_DIR=$(SRC_DIR)/modules/$(MOD)
EXTRA_MOD_SRC_DIR=$(EXTRA_MOD_BASE_DIR)/$(MOD)

all: $(MOD).so

%.o: $(MOD_SRC_DIR)/%.c
	$(CC) -c $(CFLAGS) -I$(MOD_SRC_DIR)/../.. -o $@ $<

%.o: $(EXTRA_MOD_SRC_DIR)/%.c
	$(CC) -c $(CFLAGS) -I$(SRC_DIR) -o $@ $<

%.so: %.o
ifeq ($(UNAME_S),Darwin)
	$(CC) -o $@ $^ $(LDFLAGS)
else
	$(CC) -Wl,-soname,$@ -o $@ $^ $(LDFLAGS)
endif

.PHONY: clean
clean:
	rm -f *.o *.so
