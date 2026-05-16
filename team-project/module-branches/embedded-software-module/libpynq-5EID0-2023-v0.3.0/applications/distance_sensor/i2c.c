#include "i2c.h"
#include <libpynq.h>
#include <stdint.h>
#include <stdbool.h>

#define DEFAULT_SLAVE_ADDRESS 0x29

static uint8_t current_slave_address = DEFAULT_SLAVE_ADDRESS;

void i2c_set_slave_address(uint8_t addr)
{
    current_slave_address = addr;
}

void i2c_init(void)
{
    current_slave_address = DEFAULT_SLAVE_ADDRESS;
    iic_reset(IIC0);
}

bool i2c_read_addr8_data8(uint8_t addr, uint8_t *data)
{
    return iic_read_register(IIC0, current_slave_address, addr, data, 1) == 0;
}

bool i2c_read_addr8_data16(uint8_t addr, uint16_t *data)
{
    uint8_t buffer[2];

    if (iic_read_register(IIC0, current_slave_address, addr, buffer, 2)) {
        return false;
    }

    *data = ((uint16_t)buffer[0] << 8) | buffer[1];
    return true;
}

bool i2c_read_addr16_data8(uint16_t addr, uint8_t *data)
{
    return iic_read_register(IIC0, current_slave_address, (uint8_t)addr, data, 1) == 0;
}

bool i2c_read_addr16_data16(uint16_t addr, uint16_t *data)
{
    return i2c_read_addr8_data16((uint8_t)addr, data);
}

bool i2c_read_addr8_data32(uint16_t addr, uint32_t *data)
{
    uint8_t buffer[4];

    if (iic_read_register(IIC0, current_slave_address, (uint8_t)addr, buffer, 4)) {
        return false;
    }

    *data = ((uint32_t)buffer[0] << 24) |
            ((uint32_t)buffer[1] << 16) |
            ((uint32_t)buffer[2] << 8)  |
            buffer[3];

    return true;
}

bool i2c_read_addr16_data32(uint16_t addr, uint32_t *data)
{
    return i2c_read_addr8_data32(addr, data);
}

bool i2c_read_addr8_bytes(uint8_t start_addr, uint8_t *bytes, uint16_t byte_count)
{
    return iic_read_register(IIC0, current_slave_address, start_addr, bytes, byte_count) == 0;
}

bool i2c_write_addr8_data8(uint8_t addr, uint8_t data)
{
    return iic_write_register(IIC0, current_slave_address, addr, &data, 1) == 0;
}

bool i2c_write_addr8_data16(uint8_t addr, uint16_t data)
{
    uint8_t buffer[2];

    buffer[0] = (uint8_t)(data >> 8);
    buffer[1] = (uint8_t)(data & 0xFF);

    return iic_write_register(IIC0, current_slave_address, addr, buffer, 2) == 0;
}

bool i2c_write_addr16_data8(uint16_t addr, uint8_t data)
{
    return i2c_write_addr8_data8((uint8_t)addr, data);
}

bool i2c_write_addr16_data16(uint16_t addr, uint16_t data)
{
    return i2c_write_addr8_data16((uint8_t)addr, data);
}

bool i2c_write_addr8_bytes(uint8_t start_addr, uint8_t *bytes, uint16_t byte_count)
{
    return iic_write_register(IIC0, current_slave_address, start_addr, bytes, byte_count) == 0;
}