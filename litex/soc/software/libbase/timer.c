#include <timer.h>
#include <generated/csr.h>

uint64_t get_uptime_cycles(void) {
#ifdef CSR_TIMER0_UPTIME_CYCLES_ADDR
	timer0_uptime_latch_write(1);
	return timer0_uptime_cycles_read();
#else
    return 0;
#endif
}

#if 0
double get_uptime_seconds(void) {
    return get_uptime_cycles() / (double)CONFIG_CLOCK_FREQUENCY;
}
#endif
