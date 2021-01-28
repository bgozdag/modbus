// g++ master.cpp -lmodbus -o master

#include <modbus.h>
#include <stdio.h>
#include <errno.h>
#include <stdlib.h>
#include <string.h>

int main(int argc, char *argv[])
{
    modbus_t *ctx;
    int rc;
    int nb = atoi(argv[3]) - atoi(argv[2]) + 1;
    printf("connecting to: %s\n", argv[1]);
    uint16_t regs[nb];
    ctx = modbus_new_tcp(argv[1], 502);
    if (modbus_connect(ctx) == -1)
    {
        printf("Connection failed: %s\n", modbus_strerror(errno));
        modbus_free(ctx);
        exit(101);
    }
    if (strcmp(argv[4], "r") == 0)
    {
        rc = modbus_read_input_registers(ctx, atoi(argv[2]), nb, regs);
        if (rc != nb)
        {
            printf("ERROR modbus_read_registers (%d)\n", rc);
            printf("Address = %d, nb = %d\n", atoi(argv[2]), nb);
            exit(102);
        }
        for (int i = 0; i < rc; i++)
        {
            printf("reg[%d]=%d (0x%X)\n", i, regs[i], regs[i]);
        }
    }
    else
    {
        const uint16_t data = atoi(argv[4]);
        printf("data: %d\n", data);
        rc = modbus_write_registers(ctx, atoi(argv[2]), nb, &data);
        if (rc != nb)
        {
            printf("ERROR modbus_write_registers (%d)\n", rc);
            exit(102);
        }
        rc = modbus_read_registers(ctx, atoi(argv[2]), nb, regs);
        if (rc != nb)
        {
            printf("ERROR modbus_read_registers (%d)\n", rc);
            exit(102);
        }
        for (int i = 0; i < rc; i++)
        {
            printf("reg[%d]=%d (0x%X)\n", i, regs[i], regs[i]);
        }
    }
    modbus_close(ctx);
    modbus_free(ctx);
}