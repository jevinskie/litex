#include "coremark.h"

static void run_coremark(int nb_params, char **params)
{
    struct core_portable p;
    portable_init(&p, nb_params, params);
    portable_fini(&p);
}