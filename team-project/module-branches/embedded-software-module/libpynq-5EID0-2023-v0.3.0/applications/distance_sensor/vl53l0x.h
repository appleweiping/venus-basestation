#ifndef VL53L0X_H
#define VL53L0X_H

#include <stdbool.h>
#include <stdint.h>

#define VL53L0X_OUT_OF_RANGE 8190

typedef enum
{
    VL53L0X_IDX_FIRST
} vl53l0x_idx_t;

bool vl53l0x_init(void);
bool vl53l0x_read_range_single(vl53l0x_idx_t idx, uint16_t *range);

#endif