#pragma once
#include <stdint.h>

#ifdef __cplusplus
extern "C" {
#endif

uint64_t get_uptime_cycles(void);
#if 0
double get_uptime_seconds(void);
#endif

#ifdef __cplusplus
} // extern "C"
#endif
