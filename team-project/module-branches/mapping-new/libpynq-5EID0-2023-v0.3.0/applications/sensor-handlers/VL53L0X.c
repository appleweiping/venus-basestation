#include <libpynq.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <stdbool.h>
#include "VL53L0X.h"

#define VL53L0X_ADDR 0x29   // Datasheet shows 0x52 as 8-bit address byte. 0x52 >> 1 = 0x29.

/* STATUS: NOT WORKING - TRY CHARGED ROBOTOS!!*/
static bool initialized = false;

// Main registers
#define REG_SYSRANGE_START                          0x00
#define REG_SYSTEM_SEQUENCE_CONFIG                  0x01
#define REG_SYSTEM_INTERRUPT_CONFIG_GPIO            0x0A
#define REG_SYSTEM_INTERRUPT_CLEAR                  0x0B
#define REG_RESULT_INTERRUPT_STATUS                 0x13
#define REG_RESULT_RANGE_STATUS                     0x14
#define REG_RESULT_DISTANCE_HIGH                    0x1E

#define REG_GPIO_HV_MUX_ACTIVE_HIGH                 0x84
#define REG_VHV_CONFIG_PAD_SCL_SDA__EXTSUP_HV       0x89
#define REG_GLOBAL_CONFIG_SPAD_ENABLES_REF_0        0xB0
#define REG_IDENTIFICATION_MODEL_ID                 0xC0
#define REG_MSRC_CONFIG_CONTROL                     0x60
#define REG_FINAL_RANGE_CONFIG_MIN_COUNT_RATE_RTN_LIMIT 0x44

#define SENSOR_INDEX 0
#define OUT_OF_RANGE_MM 2000

static uint8_t stop_variable = 0;

#define CHECK(x) do { if (!(x)) return false; } while (0)

static bool write8(uint8_t reg, uint8_t value) {
    return iic_write_register(IIC0, VL53L0X_ADDR, reg, &value, 1) == 0;
}

static bool write16(uint8_t reg, uint16_t value) {
    uint8_t data[2];

    data[0] = (uint8_t)(value >> 8);
    data[1] = (uint8_t)(value & 0xFF);

    return iic_write_register(IIC0, VL53L0X_ADDR, reg, data, 2) == 0;
}

static bool write_multi(uint8_t reg, uint8_t *data, uint8_t length) {
    return iic_write_register(IIC0, VL53L0X_ADDR, reg, data, length) == 0;
}

static bool read8(uint8_t reg, uint8_t *value) {
    return iic_read_register(IIC0, VL53L0X_ADDR, reg, value, 1) == 0;
}

static bool read16(uint8_t reg, uint16_t *value) {
    uint8_t data[2];

    if (iic_read_register(IIC0, VL53L0X_ADDR, reg, data, 2)) {
        return false;
    }

    *value = ((uint16_t)data[0] << 8) | data[1];

    return true;
}

static bool read_multi(uint8_t reg, uint8_t *data, uint8_t length) {
    return iic_read_register(IIC0, VL53L0X_ADDR, reg, data, length) == 0;
}

static bool check_basic_iic(void) {
    uint8_t c0 = 0;
    uint8_t c1 = 0;
    uint8_t c2 = 0;

    if (!read8(0xC0, &c0)) return false;
    sleep_msec(10);

    if (!read8(0xC1, &c1)) return false;
    sleep_msec(10);

    if (!read8(0xC2, &c2)) return false;
    sleep_msec(10);

    printf("sensor %d: C0=0x%02X C1=0x%02X C2=0x%02X\n",
           SENSOR_INDEX, c0, c1, c2);

    return c0 == 0xEE && c1 == 0xAA && c2 == 0x10;
}

static bool get_spad_info(uint8_t *count, bool *type_is_aperture) {
    uint8_t tmp = 0;

    CHECK(write8(0x80, 0x01));
    CHECK(write8(0xFF, 0x01));
    CHECK(write8(0x00, 0x00));

    CHECK(write8(0xFF, 0x06));
    CHECK(read8(0x83, &tmp));
    CHECK(write8(0x83, tmp | 0x04));
    CHECK(write8(0xFF, 0x07));
    CHECK(write8(0x81, 0x01));

    CHECK(write8(0x80, 0x01));

    CHECK(write8(0x94, 0x6B));
    CHECK(write8(0x83, 0x00));

    for (int timeout = 0; timeout < 100; timeout++) {
        CHECK(read8(0x83, &tmp));

        if (tmp != 0x00) {
            break;
        }

        sleep_msec(1);

        if (timeout == 99) {
            return false;
        }
    }

    CHECK(write8(0x83, 0x01));
    CHECK(read8(0x92, &tmp));

    *count = tmp & 0x7F;
    *type_is_aperture = (tmp >> 7) & 0x01;

    CHECK(write8(0x81, 0x00));
    CHECK(write8(0xFF, 0x06));

    CHECK(read8(0x83, &tmp));
    CHECK(write8(0x83, tmp & ~0x04));

    CHECK(write8(0xFF, 0x01));
    CHECK(write8(0x00, 0x01));

    CHECK(write8(0xFF, 0x00));
    CHECK(write8(0x80, 0x00));

    return true;
}

static bool load_tuning_settings(void) {
    CHECK(write8(0xFF, 0x01));
    CHECK(write8(0x00, 0x00));

    CHECK(write8(0xFF, 0x00));
    CHECK(write8(0x09, 0x00));
    CHECK(write8(0x10, 0x00));
    CHECK(write8(0x11, 0x00));

    CHECK(write8(0x24, 0x01));
    CHECK(write8(0x25, 0xFF));
    CHECK(write8(0x75, 0x00));

    CHECK(write8(0xFF, 0x01));
    CHECK(write8(0x4E, 0x2C));
    CHECK(write8(0x48, 0x00));
    CHECK(write8(0x30, 0x20));

    CHECK(write8(0xFF, 0x00));
    CHECK(write8(0x30, 0x09));
    CHECK(write8(0x54, 0x00));
    CHECK(write8(0x31, 0x04));
    CHECK(write8(0x32, 0x03));
    CHECK(write8(0x40, 0x83));
    CHECK(write8(0x46, 0x25));
    CHECK(write8(0x60, 0x00));
    CHECK(write8(0x27, 0x00));
    CHECK(write8(0x50, 0x06));
    CHECK(write8(0x51, 0x00));
    CHECK(write8(0x52, 0x96));
    CHECK(write8(0x56, 0x08));
    CHECK(write8(0x57, 0x30));
    CHECK(write8(0x61, 0x00));
    CHECK(write8(0x62, 0x00));
    CHECK(write8(0x64, 0x00));
    CHECK(write8(0x65, 0x00));
    CHECK(write8(0x66, 0xA0));

    CHECK(write8(0xFF, 0x01));
    CHECK(write8(0x22, 0x32));
    CHECK(write8(0x47, 0x14));
    CHECK(write8(0x49, 0xFF));
    CHECK(write8(0x4A, 0x00));

    CHECK(write8(0xFF, 0x00));
    CHECK(write8(0x7A, 0x0A));
    CHECK(write8(0x7B, 0x00));
    CHECK(write8(0x78, 0x21));

    CHECK(write8(0xFF, 0x01));
    CHECK(write8(0x23, 0x34));
    CHECK(write8(0x42, 0x00));
    CHECK(write8(0x44, 0xFF));
    CHECK(write8(0x45, 0x26));
    CHECK(write8(0x46, 0x05));
    CHECK(write8(0x40, 0x40));
    CHECK(write8(0x0E, 0x06));
    CHECK(write8(0x20, 0x1A));
    CHECK(write8(0x43, 0x40));

    CHECK(write8(0xFF, 0x00));
    CHECK(write8(0x34, 0x03));
    CHECK(write8(0x35, 0x44));

    CHECK(write8(0xFF, 0x01));
    CHECK(write8(0x31, 0x04));
    CHECK(write8(0x4B, 0x09));
    CHECK(write8(0x4C, 0x05));
    CHECK(write8(0x4D, 0x04));

    CHECK(write8(0xFF, 0x00));
    CHECK(write8(0x44, 0x00));
    CHECK(write8(0x45, 0x20));
    CHECK(write8(0x47, 0x08));
    CHECK(write8(0x48, 0x28));
    CHECK(write8(0x67, 0x00));
    CHECK(write8(0x70, 0x04));
    CHECK(write8(0x71, 0x01));
    CHECK(write8(0x72, 0xFE));
    CHECK(write8(0x76, 0x00));
    CHECK(write8(0x77, 0x00));

    CHECK(write8(0xFF, 0x01));
    CHECK(write8(0x0D, 0x01));

    CHECK(write8(0xFF, 0x00));
    CHECK(write8(0x80, 0x01));
    CHECK(write8(0x01, 0xF8));

    CHECK(write8(0xFF, 0x01));
    CHECK(write8(0x8E, 0x01));
    CHECK(write8(0x00, 0x01));

    CHECK(write8(0xFF, 0x00));
    CHECK(write8(0x80, 0x00));

    return true;
}

static bool perform_single_ref_calibration(uint8_t vhv_init_byte) {
    uint8_t status = 0;

    CHECK(write8(REG_SYSRANGE_START, 0x01 | vhv_init_byte));

    for (int timeout = 0; timeout < 100; timeout++) {
        CHECK(read8(REG_RESULT_INTERRUPT_STATUS, &status));

        if ((status & 0x07) != 0) {
            CHECK(write8(REG_SYSTEM_INTERRUPT_CLEAR, 0x01));
            CHECK(write8(REG_SYSRANGE_START, 0x00));
            return true;
        }

        sleep_msec(10);
    }

    return false;
}

static bool vl53l0x_init(void) {
    uint8_t value = 0;
    uint8_t spad_count = 0;
    bool spad_type_is_aperture = false;
    uint8_t ref_spad_map[6];

    sleep_msec(5);

    CHECK(read8(REG_IDENTIFICATION_MODEL_ID, &value));

    if (value != 0xEE) {
        printf("sensor %d: wrong ID 0x%02X\n", SENSOR_INDEX, value);
        return false;
    }

    // Enable 2.8V mode.
    CHECK(read8(REG_VHV_CONFIG_PAD_SCL_SDA__EXTSUP_HV, &value));
    CHECK(write8(REG_VHV_CONFIG_PAD_SCL_SDA__EXTSUP_HV, value | 0x01));

    // Store stop variable.
    CHECK(write8(0x88, 0x00));
    CHECK(write8(0x80, 0x01));
    CHECK(write8(0xFF, 0x01));
    CHECK(write8(0x00, 0x00));
    CHECK(read8(0x91, &stop_variable));
    CHECK(write8(0x00, 0x01));
    CHECK(write8(0xFF, 0x00));
    CHECK(write8(0x80, 0x00));

    // Disable some limit checks.
    CHECK(read8(REG_MSRC_CONFIG_CONTROL, &value));
    CHECK(write8(REG_MSRC_CONFIG_CONTROL, value | 0x12));

    // Set final range signal rate limit to 0.25 MCPS.
    CHECK(write16(REG_FINAL_RANGE_CONFIG_MIN_COUNT_RATE_RTN_LIMIT, 32));

    CHECK(write8(REG_SYSTEM_SEQUENCE_CONFIG, 0xFF));

    CHECK(get_spad_info(&spad_count, &spad_type_is_aperture));

    CHECK(read_multi(REG_GLOBAL_CONFIG_SPAD_ENABLES_REF_0, ref_spad_map, 6));

    uint8_t first_spad_to_enable = spad_type_is_aperture ? 12 : 0;
    uint8_t spads_enabled = 0;

    for (uint8_t i = 0; i < 48; i++) {
        if (i < first_spad_to_enable || spads_enabled == spad_count) {
            ref_spad_map[i / 8] &= ~(1 << (i % 8));
        } else if (ref_spad_map[i / 8] & (1 << (i % 8))) {
            spads_enabled++;
        }
    }

    CHECK(write_multi(REG_GLOBAL_CONFIG_SPAD_ENABLES_REF_0, ref_spad_map, 6));

    CHECK(load_tuning_settings());

    // Configure GPIO interrupt: new sample ready.
    CHECK(write8(REG_SYSTEM_INTERRUPT_CONFIG_GPIO, 0x04));

    CHECK(read8(REG_GPIO_HV_MUX_ACTIVE_HIGH, &value));
    CHECK(write8(REG_GPIO_HV_MUX_ACTIVE_HIGH, value & ~0x10));

    CHECK(write8(REG_SYSTEM_INTERRUPT_CLEAR, 0x01));

    // Reference calibrations.
    CHECK(write8(REG_SYSTEM_SEQUENCE_CONFIG, 0x01));
    CHECK(perform_single_ref_calibration(0x40));

    CHECK(write8(REG_SYSTEM_SEQUENCE_CONFIG, 0x02));
    CHECK(perform_single_ref_calibration(0x00));

    // Enable final default ranging sequence.
    CHECK(write8(REG_SYSTEM_SEQUENCE_CONFIG, 0xE8));

    return true;
}

static bool read_distance_mm(uint16_t *distance_mm) {
    uint8_t status = 0;
    uint8_t sysrange = 0;

    // Prepare single measurement.
    CHECK(write8(0x80, 0x01));
    CHECK(write8(0xFF, 0x01));
    CHECK(write8(0x00, 0x00));
    CHECK(write8(0x91, stop_variable));
    CHECK(write8(0x00, 0x01));
    CHECK(write8(0xFF, 0x00));
    CHECK(write8(0x80, 0x00));

    // Start single range measurement.
    CHECK(write8(REG_SYSRANGE_START, 0x01));

    // Wait for start bit to clear.
    for (int timeout = 0; timeout < 100; timeout++) {
        CHECK(read8(REG_SYSRANGE_START, &sysrange));

        if ((sysrange & 0x01) == 0) {
            break;
        }

        sleep_msec(1);
    }

    // Wait until measurement is ready.
    for (int timeout = 0; timeout < 100; timeout++) {
        CHECK(read8(REG_RESULT_INTERRUPT_STATUS, &status));

        if ((status & 0x07) != 0) {
            break;
        }

        sleep_msec(10);
    }

    if ((status & 0x07) == 0) {
        return false;
    }

    CHECK(read16(REG_RESULT_DISTANCE_HIGH, distance_mm));

    // Clear interrupt.
    CHECK(write8(REG_SYSTEM_INTERRUPT_CLEAR, 0x01));

    return true;
}

int distance_init() {
    // Use the Arduino-labelled I2C pins.
    switchbox_set_pin(IO_AR_SCL, SWB_IIC0_SCL);
    switchbox_set_pin(IO_AR_SDA, SWB_IIC0_SDA);

    iic_init(IIC0);
    iic_reset(IIC0);

    setbuf(stdout, NULL);

    printf("[DBG] sensor %d: program started\n", SENSOR_INDEX);

    // Let the sensor and IIC bus settle.
    sleep_msec(500);

    // First make sure basic IIC communication is stable.
    bool iic_ready = false;

    for (int attempt = 1; attempt <= 10; attempt++) {
        printf("DBG] sensor %d: IIC check attempt %d\n", SENSOR_INDEX, attempt);

        if (check_basic_iic()) {
            iic_ready = true;
            break;
        }

        iic_reset(IIC0);
        sleep_msec(300);
    }

    if (!iic_ready) {
        printf("[ERROR] sensor %d: IIC check failed\n", SENSOR_INDEX);
        iic_destroy(IIC0);
        return 1;
    }

    printf("[DBG] sensor %d: IIC bus stable\n", SENSOR_INDEX);

    for (int attempt = 1; attempt <= 5; attempt++) {
        printf("[DBG] sensor %d: init attempt %d\n", SENSOR_INDEX, attempt);

        if (vl53l0x_init()) {
            initialized = true;
            break;
        }

        iic_reset(IIC0);
        sleep_msec(300);
    }

    if (!initialized) {
        printf("[ERROR] Sensor %d: initialization failed\n", SENSOR_INDEX);
        iic_destroy(IIC0);
        return 1;
    }

    printf("[DBG] sensor %d: initialized\n", SENSOR_INDEX);
    initialized = true;
    return 0;
}

uint16_t getDistance() {
    if (!initialized) {
        printf("[ERROR] getDistance() called but distance sensor not initialized!\n");
        return -1;
    }
    uint16_t distance = 0;

    if (read_distance_mm(&distance)
         && distance > 0
         && distance <= OUT_OF_RANGE_MM)
    {
        printf("[DEBUG] sensor %d: %u mm\n", SENSOR_INDEX, distance);
        return distance;
    }
    else
    {
        printf("[ERROR] Sensor %d: out of range\n", SENSOR_INDEX);
        return -1;
    }


}

void distance_destroy() {
    iic_destroy(IIC0);
}
