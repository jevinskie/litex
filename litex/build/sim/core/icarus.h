#pragma once

#ifdef __cplusplus
extern "C" {
#endif

#include <stdint.h>

void litex_sim_eval(void *vsim, uint64_t time_ps);
void litex_sim_init_tracer(void *vsim);
void litex_sim_tracer_dump();
int litex_sim_got_finish();
void litex_sim_init_cmdargs(int argc, char *argv[]);
#if VM_COVERAGE
void litex_sim_coverage_dump();
#endif

#ifdef __cplusplus
}; // extern "C"
#endif
