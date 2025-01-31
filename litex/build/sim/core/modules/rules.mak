CC ?= gcc
UNAME_S := $(shell uname -s)

ifeq ($(UNAME_S),Darwin)
    CFLAGS += -I/usr/local/include -I/opt/brew/include -I/opt/homebrew/include
    LDFLAGS += -L/usr/local/lib -L/opt/brew/lib -L/opt/homebrew/lib -ljson-c -ggdb
    CFLAGS += -Wall -O3 -ggdb -fPIC -Werror
else
    CFLAGS += -Wall -O3 -ggdb -fPIC -Werror
endif
LDFLAGS += -levent -shared -fPIC

MOD_SRC_DIR=$(SRC_DIR)/modules/$(MOD)

all: $(MOD).so

%.o: $(MOD_SRC_DIR)/%.c
	$(CC) -c $(CFLAGS) -I$(MOD_SRC_DIR)/../.. -o $@ $<

%.so: %.o
ifeq ($(UNAME_S),Darwin)
	$(CC) $(LDFLAGS) -o $@ $^
else
	$(CC) $(LDFLAGS) -Wl,-soname,$@ -o $@ $<
endif

.PHONY: clean
clean:
	rm -f *.o *.so
