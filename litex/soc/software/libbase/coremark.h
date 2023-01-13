#pragma once
#include <stdint.h>

#ifdef CONFIG_COREMARK

#ifdef __cplusplus
extern "C" {
#endif

typedef struct
{
    uint8_t portable_id;
} core_portable;

extern void portable_init(core_portable *p, int *argc, char *argv[]);
extern void portable_fini(core_portable *p);

#ifdef __cplusplus
} // extern "C"
#endif

#endif // CONFIG_COREMARK
