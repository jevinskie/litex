include ../include/generated/variables.mak
include $(SOC_DIRECTORY)/software/common.mak

OBJECTS =  \
	crc16.o    \
	crc32.o    \
	console.o  \
	system.o   \
	progress.o \
	memtest.o  \
	uart.o     \
	spiflash.o \
	i2c.o \
	isr.o \
	timer.o

OBJECTS+=coremark.o core_state.o core_matrix.o core_list_join.o core_main.o core_util.o

all: libbase.a

libbase.a: $(OBJECTS)
	$(AR) crs libbase.a $(OBJECTS)

# pull in dependency info for *existing* .o files
-include $(OBJECTS:.o=.d)

%.o: $(LIBBASE_DIRECTORY)/%.c
	$(compile)

%.o: $(LIBBASE_DIRECTORY)/../coremark/%.c
	$(compile)

.PHONY: all clean

clean:
	$(RM) $(OBJECTS)
	$(RM) libbase.a .*~ *~
