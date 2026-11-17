/* Benchmark only: request Basalt's normal buffered fallback for one model path. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdlib.h>
#include <string.h>

static int reject_direct(const char *path, int flags) {
    const char *model = getenv("BASALT_TEST_BUFFERED_PACK");
    if ((flags & O_DIRECT) && model && strcmp(path, model) == 0) {
        errno = EOPNOTSUPP;
        return 1;
    }
    return 0;
}

#define WRAP_OPEN(name) \
int name(const char *path, int flags, ...) { \
    if (reject_direct(path, flags)) return -1; \
    int (*real_open)(const char *, int, ...) = dlsym(RTLD_NEXT, #name); \
    if ((flags & O_CREAT) || (flags & O_TMPFILE) == O_TMPFILE) { \
        va_list args; va_start(args, flags); \
        int mode = va_arg(args, int); va_end(args); \
        return real_open(path, flags, mode); \
    } \
    return real_open(path, flags); \
}
WRAP_OPEN(open)
WRAP_OPEN(open64)
