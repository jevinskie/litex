/* Copyright (C) 2017 LambdaConcept */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#ifdef _WIN32
#include <Windows.h>
#include <pathcch.h>
#pragma comment(lib, "Pathcch.lib")
#else
#include <libgen.h>
#include <unistd.h>
#endif
#ifdef __APPLE__
#include <mach-o/dyld.h>
#endif
#include "tinydir.h"
#include "error.h"
#include "libdylib.h"
#include "modules.h"

#ifdef _MSC_VER
#define LIBEXT "dll"
#else
#define LIBEXT "so"
#endif

#define LITEX_MAX_PATH 4096

static struct ext_module_list_s *modlist=NULL;

int litex_sim_register_ext_module(struct ext_module_s *mod)
{
  int ret=RC_OK;
  struct ext_module_list_s *ml=NULL;

  if(!mod)
  {
    eprintf("Invalid arguments\n");
    ret=RC_INVARG;
    goto out;
  }
  ml = (struct ext_module_list_s *)malloc(sizeof(struct ext_module_list_s));
  if(NULL == ml)
  {
    ret = RC_NOENMEM;
    eprintf("Not enough memory\n");
    goto out;
  }
  memset(ml, 0, sizeof( struct ext_module_list_s));
  ml->module = mod;
  ml->next = modlist;
  modlist = ml;

out:
  return ret;
}

static char *get_executable_path(void) {
  char *buf = malloc(LITEX_MAX_PATH);
  int err = 0;
  if (!buf) {
    eprintf("Not enough memory\n");
    return NULL;
  }
  memset(buf, 0, LITEX_MAX_PATH);
#ifdef _WIN32
  if (GetModuleFileNameA(NULL, buf, LITEX_MAX_PATH) == 0) {
    err = 1;
  }
#elif !defined(__APPLE__)
  if (readlink("/proc/self/exe", buf, LITEX_MAX_PATH - 1) <= 0) {
    err = 1;
  }
#elif defined(__APPLE__)
  uint32_t bufsz = LITEX_MAX_PATH;
  if (_NSGetExecutablePath(buf, &bufsz)) {
    err = 1;
  }
#else
#error unsupported platform
#endif
  if (err) {
    eprintf("Can't get executable file name\n");
    free(buf);
    return NULL;
  }
  return buf;
}

static char *get_parent_path(const char *path) {
  char *buf = malloc(LITEX_MAX_PATH);
  int err = 0;
  if (!buf) {
    eprintf("Not enough memory\n");
    return NULL;
  }
#ifdef _WIN32
  strncpy(buf, path, LITEX_MAX_PATH);
  if (PathCchRemoveFileSpec(buf, LITEX_MAX_PATH) != S_OK) {
    err = 1;
  }
#else
  strncpy(buf, path, LITEX_MAX_PATH);
  const char *tmp = dirname(buf);
  strncpy(buf, tmp, LITEX_MAX_PATH);
#endif
  if (err) {
    eprintf("Can't get parent of path '%s'\n", path);
    free(buf);
    return NULL;
  }
  return buf;
}

char *litex_sim_append_to_path(const char *path, const char *part) {
  char *buf = malloc(LITEX_MAX_PATH);
  int err = 0;
  if (!buf) {
    eprintf("Not enough memory\n");
    return NULL;
  }
  strncpy(buf, path, LITEX_MAX_PATH);
#ifdef _WIN32
  if (PathCchAppendEx(buf, LITEX_MAX_PATH, part, PATHCCH_ALLOW_LONG_PATHS) != S_OK) {
    err = 1;
  }
#else
  int res = snprintf(buf, LITEX_MAX_PATH, "%s/%s", path, part);
  if (res <= 0 || res >= LITEX_MAX_PATH) {
    err = 1;
  }
#endif
  if (err) {
    eprintf("Can't append '%s' to path '%s'\n", path, part);
    free(buf);
    return NULL;
  }
  return buf;
}

char *litex_sim_get_gateware_dir(void) {
  char *exe_path = get_executable_path();
  if (!exe_path) {
    return NULL;
  }
  char *parent_path = get_parent_path(exe_path);
  if (!parent_path) {
    free(exe_path);
    return NULL;
  }
  char *parent_parent_path = get_parent_path(parent_path);
  if (!parent_parent_path) {
    free(exe_path);
    free(parent_path);
    return NULL;
  }
  return parent_parent_path;
}

char *litex_sim_get_ext_modules_dir(void) {
  char *gateware_dir = litex_sim_get_gateware_dir();
  if (!gateware_dir) {
    return NULL;
  }
  char *mod_dir = litex_sim_append_to_path(gateware_dir, "modules");
  free(gateware_dir);
  return mod_dir;
}

int litex_sim_load_ext_modules(struct ext_module_list_s **mlist)
{
  int ret = RC_OK;
  tinydir_dir dir;
  int dir_opened = 0;
  tinydir_file file;
  dylib_ref lib;
  int (*litex_sim_ext_module_init)(int (*reg)(struct ext_module_s *));
  char *mod_dir = litex_sim_get_ext_modules_dir();
  if (!mod_dir) {
    ret = RC_ERROR;
    eprintf("Error getting module directory\n");
    goto out;
  }
  if (tinydir_open(&dir, mod_dir) == -1)
  {
    dir_opened = 1;
    ret = RC_ERROR;
    eprintf("Error opening module directory '%s'\n", mod_dir);
    goto out;
  }
  if(modlist)
  {
    ret = RC_ERROR;
    eprintf("modules already loaded !\n");
    goto out;
  }
  while(dir.has_next)
  {
    if(-1 == tinydir_readfile(&dir, &file))
    {
      ret = RC_ERROR;
      eprintf("Can't get file \n");
      goto out;
    }

    if(!strcmp(file.extension, LIBEXT))
    {
      char *mod_path = litex_sim_append_to_path(mod_dir, file.name);
      if (!mod_path) {
        eprintf("Error getting module path from directory '%s' and file '%s'\n", mod_dir, file.name);
        goto out;
      }
      lib = libdylib_open(mod_path);
      if(!lib)
      {
        ret = RC_ERROR;
        eprintf("Can't load library %s\n", libdylib_last_error());
        goto out;
      }
      free(mod_path);

      if(!libdylib_find(lib, "litex_sim_ext_module_init"))
      {
        ret = RC_ERROR;
        eprintf("Module has no litex_sim_ext_module_init function\n");
        goto out;
      }
      LIBDYLIB_BINDNAME(lib, litex_sim_ext_module_init);
      if(!litex_sim_ext_module_init)
      {
        ret = RC_ERROR;
        eprintf("Can't bind %s\n", libdylib_last_error());
        goto out;
      }
      ret = litex_sim_ext_module_init(litex_sim_register_ext_module);
      if(RC_OK != ret)
      {
        goto out;
      }
    }
    if(-1 == tinydir_next(&dir))
    {
      eprintf("Error getting next file\n");
      ret = RC_ERROR;
      goto out;
    }
  }
  *mlist = modlist;
out:
  free(mod_dir);
  if (dir_opened) {
    tinydir_close(&dir);
  }
  return ret;
}

int litex_sim_find_ext_module(struct ext_module_list_s *first, char *name , struct ext_module_list_s **found)
{
  struct ext_module_list_s *list = NULL;
  int ret=RC_OK;

  if(!first || !name || !found)
  {
    ret = RC_INVARG;
    eprintf("Invalid first:%s arg:%s found:%p\n", first->module->name, name, found);
    goto out;
  }

  for(list = first; list; list=list->next)
  {
    if(!strcmp(name, list->module->name))
      break;
  }
out:
  *found = list;
  return ret;
}

int litex_sim_find_module(struct module_s *first, char *name , struct module_s **found)
{
  struct module_s *list = NULL;
  int ret=RC_OK;

  if(!first || !name || !found)
  {
    ret = RC_INVARG;
    eprintf("Invalid first:%s arg:%s found:%p\n", first->name, name, found);
    goto out;
  }

  for(list = first; list; list=list->next)
  {
    if(!strcmp(name, list->name))
      break;
  }
out:
  *found = list;
  return ret;
}
