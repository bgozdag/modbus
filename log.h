#ifndef LOG_H
#define LOG_H

#ifdef __cplusplus
extern "C"
{
#endif

#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdarg.h>
#include <pthread.h>
#include <errno.h>
#include <time.h>
#include <sys/stat.h>

#define CLR_NORMAL "\x1B[0m"
#define CLR_RED "\x1B[31m"
#define CLR_GREEN "\x1B[32m"
#define CLR_YELLOW "\x1B[33m"
#define CLR_BLUE "\x1B[34m"
#define CLR_CYAN "\x1B[36m"
#define CLR_CYANBG "\x1B[46m"
#define CLR_PURPLEBG "\x1B[45m"
#define CLR_REDBG "\x1B[41m"

#define logDebug(...) \
    logStandard(CLR_BLUE, LogLevel_DEBUG, __VA_ARGS__)

#define logInfo(...) \
    logStandard(CLR_GREEN, LogLevel_INFO, __VA_ARGS__)

#define logNotice(...) \
    logStandard(CLR_CYAN, LogLevel_NOTICE, __VA_ARGS__)

#define logWarning(...) \
    logStandard(CLR_YELLOW, LogLevel_WARNING, __VA_ARGS__)

#define logErr(...) \
    logStandard(CLR_RED, LogLevel_ERR, __VA_ARGS__)

#define logCrit(...) \
    logStandard(CLR_CYANBG, LogLevel_CRIT, __VA_ARGS__)

#define logAlert(...) \
    logStandard(CLR_PURPLEBG, LogLevel_ALERT, __VA_ARGS__)

#define logEmerg(...) \
    logStandard(CLR_REDBG, LogLevel_EMERG, __VA_ARGS__)

    typedef enum
    {
        LogLevel_EMERG = 0,
        LogLevel_ALERT = 1,
        LogLevel_CRIT = 2,
        LogLevel_ERR = 3,
        LogLevel_WARNING = 4,
        LogLevel_NOTICE = 5,
        LogLevel_INFO = 6,
        LogLevel_DEBUG = 7
    } LogLevel;

    struct LogConfig
    {
        char filePathName[128];
        char currentFileName[256];
        char previousFileName[256];
        FILE *fp;
        LogLevel logLevel;
        int logToFile;
        struct stat lastModified;
        int maxStoredFile;
        pthread_mutex_t mutex;
    };

    void logStandard(const char *_logColor, LogLevel _logLevel, const char *msg, ...);
    void logInit(const char *_fileName, int maxStoredFile);
    

#ifdef __cplusplus
}
#endif

#endif
