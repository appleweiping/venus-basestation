#ifndef VLX_H
#define VLX_H

#include <stdint.h>
#include <libpynq.h>

typedef struct {
    iic_index_t iic_bus;
    uint8_t address;
} VL53L0X_Dev_t;

// Function prototypes
int tofInit(VL53L0X_Dev_t *dev, iic_index_t bus, uint8_t addr);
uint32_t tofReadDistance(VL53L0X_Dev_t *dev);
void write_reg(VL53L0X_Dev_t *dev, uint8_t reg, uint8_t val);
uint8_t read_reg(VL53L0X_Dev_t *dev, uint8_t reg);

#endif