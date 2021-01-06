#include "log.h"

#define PRINTK_PATH "/proc/sys/kernel/printk"

static struct LogConfig logConfig;
char command[256];
char commandPath[128];
char commandFileName[128];

static void logGetLevel()
{
    char logLevel;
    FILE *fp = fopen(PRINTK_PATH, "r");

    if (fp == NULL)
    {
        printf("[ERROR] could not open log config file: %s\n", PRINTK_PATH);
        return;
    }
    logLevel = fgetc(fp);
    logConfig.logLevel = logLevel - '0';
    fclose(fp);
}

static int isLevelModified()
{
    int result = 0;
    struct stat currentStat;
    stat(PRINTK_PATH, &currentStat);

    if (currentStat.st_mtime > logConfig.lastModified.st_mtime)
    {
        stat(PRINTK_PATH, &logConfig.lastModified);
        result = 1;
    }
    return result;
}

void logInit(const char *_fileName, int _maxStoredFile)
{
    if (_fileName == NULL)
    {
        logConfig.logToFile = 0;
    }
    else
    {
        logConfig.maxStoredFile = _maxStoredFile;
        logConfig.logToFile = 1;
        strcpy(logConfig.filePathName, _fileName);
        const char *position = strrchr(_fileName, '/');
        const char *i = _fileName;
        if (position != NULL)
        {
            memset(commandFileName, 0, 128);
            memset(commandPath, 0, 128);
            while (i != position)
            {
                strncat(commandPath, i, 1);
                if (*i == '/')
                    strncat(commandPath, "/", 1);
                i++;
            }
            while (*i != 0)
            {
                i++;
                strncat(commandFileName, i, 1);
            }
            sprintf(command, "mkdir -p -m 777 %s", commandPath);
            system(command);
        }
    }

    logGetLevel();
    stat(PRINTK_PATH, &logConfig.lastModified);

    pthread_mutex_init(&logConfig.mutex, NULL);
}

void logStandard(const char *logColor, LogLevel _logLevel, const char *msg, ...)
{
    if (isLevelModified())
    {
        logGetLevel();
    }

    if (_logLevel > logConfig.logLevel)
        return;

    char input[8192];
    time_t rawtime;
    struct tm *timeinfo;

    time(&rawtime);
    timeinfo = localtime(&rawtime);

    va_list args;
    va_start(args, msg);
    vsprintf(input, msg, args);
    va_end(args);

    char logLevelDesc[8];
    if (_logLevel == LogLevel_DEBUG)
    {
        strcpy(logLevelDesc, "DEBUG");
    }
    else if (_logLevel == LogLevel_INFO)
    {
        strcpy(logLevelDesc, "INFO");
    }
    else if (_logLevel == LogLevel_NOTICE)
    {
        strcpy(logLevelDesc, "NOTICE");
    }
    else if (_logLevel == LogLevel_WARNING)
    {
        strcpy(logLevelDesc, "WARNING");
    }
    else if (_logLevel == LogLevel_ERR)
    {
        strcpy(logLevelDesc, "ERR");
    }
    else if (_logLevel == LogLevel_CRIT)
    {
        strcpy(logLevelDesc, "CRIT");
    }
    else if (_logLevel == LogLevel_ALERT)
    {
        strcpy(logLevelDesc, "ALERT");
    }
    else if (_logLevel == LogLevel_EMERG)
    {
        strcpy(logLevelDesc, "EMERG");
    }

    if (logConfig.logToFile)
    {
        pthread_mutex_lock(&logConfig.mutex);
        sprintf(logConfig.currentFileName, "%s-%02d-%02d-%d.log", logConfig.filePathName, timeinfo->tm_mday, timeinfo->tm_mon + 1, timeinfo->tm_year + 1900);
        if (strcmp(logConfig.previousFileName, logConfig.currentFileName) != 0)
        {
            if (logConfig.fp != NULL)
            {
                fclose(logConfig.fp);
            }
            sprintf(logConfig.previousFileName, "%s-%02d-%02d-%d.log", logConfig.filePathName, timeinfo->tm_mday, timeinfo->tm_mon + 1, timeinfo->tm_year + 1900);
            logConfig.fp = fopen(logConfig.currentFileName, "a");
            sprintf(command, "find %s -type f -name '%s-*' -mtime +%d -exec rm {} \\;", commandPath, commandFileName, logConfig.maxStoredFile - 1);
            system(command);

            if (logConfig.fp == NULL)
            {
                printf("[ERROR] could not access log file: %s\n", logConfig.currentFileName);
                logConfig.logToFile = 0;
                return;
            }
        }
        fprintf(logConfig.fp, "%02d.%02d.%d-%02d:%02d:%02d [%s] %s", timeinfo->tm_mday, timeinfo->tm_mon + 1, timeinfo->tm_year + 1900, timeinfo->tm_hour, timeinfo->tm_min, timeinfo->tm_sec, logLevelDesc, input);
        fflush(logConfig.fp);
        pthread_mutex_unlock(&logConfig.mutex);
    }

    printf("%02d.%02d.%d-%02d:%02d:%02d [%s%s%s] %s", timeinfo->tm_mday, timeinfo->tm_mon + 1, timeinfo->tm_year + 1900, timeinfo->tm_hour, timeinfo->tm_min, timeinfo->tm_sec, logColor, logLevelDesc, CLR_NORMAL, input);
}
