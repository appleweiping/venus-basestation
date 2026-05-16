#include "vl53l0x.h"
#include "i2c.h"
#include <libpynq.h>
#include <stdint.h>
#include <stdbool.h>

/*
 * Single-sensor PYNQ/libpynq version.
 *
 * Assumptions:
 * - One VL53L0X sensor only.
 * - Sensor uses default 7-bit I2C address 0x29.
 * - XSHUT is not controlled by software.
 * - PYNQ IIC setup is done in main.c.
 */

#define REG_IDENTIFICATION_MODEL_ID                 0xC0
#define REG_VHV_CONFIG_PAD_SCL_SDA_EXTSUP_HV        0x89
#define REG_MSRC_CONFIG_CONTROL                     0x60
#define REG_FINAL_RANGE_CONFIG_MIN_COUNT_RATE_RTN_LIMIT 0x44
#define REG_SYSTEM_SEQUENCE_CONFIG                  0x01
#define REG_DYNAMIC_SPAD_REF_EN_START_OFFSET        0x4F
#define REG_DYNAMIC_SPAD_NUM_REQUESTED_REF_SPAD     0x4E
#define REG_GLOBAL_CONFIG_REF_EN_START_SELECT       0xB6
#define REG_SYSTEM_INTERRUPT_CONFIG_GPIO            0x0A
#define REG_GPIO_HV_MUX_ACTIVE_HIGH                 0x84
#define REG_SYSTEM_INTERRUPT_CLEAR                  0x0B
#define REG_RESULT_INTERRUPT_STATUS                 0x13
#define REG_SYSRANGE_START                          0x00
#define REG_GLOBAL_CONFIG_SPAD_ENABLES_REF_0        0xB0
#define REG_RESULT_RANGE_STATUS                     0x14

#define RANGE_SEQUENCE_STEP_DSS                     0x28
#define RANGE_SEQUENCE_STEP_PRE_RANGE               0x40
#define RANGE_SEQUENCE_STEP_FINAL_RANGE             0x80

#define VL53L0X_EXPECTED_DEVICE_ID                  0xEE
#define VL53L0X_DEFAULT_ADDRESS                     0x29

#define SPAD_TYPE_APERTURE                          0x01
#define SPAD_START_SELECT                           0xB4
#define SPAD_MAX_COUNT                              44
#define SPAD_MAP_ROW_COUNT                          6
#define SPAD_ROW_SIZE                               8
#define SPAD_APERTURE_START_INDEX                   12

#define TIMEOUT_SHORT_MS                            100
#define TIMEOUT_RANGE_MS                            1000

typedef struct vl53l0x_info
{
    uint8_t addr;
} vl53l0x_info_t;

typedef enum
{
    CALIBRATION_TYPE_VHV,
    CALIBRATION_TYPE_PHASE
} calibration_type_t;

static const vl53l0x_info_t vl53l0x_infos[] =
{
    [VL53L0X_IDX_FIRST] = { .addr = VL53L0X_DEFAULT_ADDRESS },
};

static uint8_t stop_variable = 0;

static bool wait_for_interrupt(uint32_t timeout_ms)
{
    uint8_t interrupt_status = 0;

    for (uint32_t elapsed = 0; elapsed < timeout_ms; elapsed++) {
        if (!i2c_read_addr8_data8(REG_RESULT_INTERRUPT_STATUS, &interrupt_status)) {
            return false;
        }

        if ((interrupt_status & 0x07) != 0) {
            return true;
        }

        sleep_msec(1);
    }

    return false;
}

static bool wait_for_sysrange_start_clear(uint32_t timeout_ms)
{
    uint8_t sysrange_start = 0;

    for (uint32_t elapsed = 0; elapsed < timeout_ms; elapsed++) {
        if (!i2c_read_addr8_data8(REG_SYSRANGE_START, &sysrange_start)) {
            return false;
        }

        if ((sysrange_start & 0x01) == 0) {
            return true;
        }

        sleep_msec(1);
    }

    return false;
}

static bool device_is_booted(void)
{
    uint8_t device_id = 0;

    for (int attempt = 0; attempt < 20; attempt++) {
        if (i2c_read_addr8_data8(REG_IDENTIFICATION_MODEL_ID, &device_id) &&
            device_id == VL53L0X_EXPECTED_DEVICE_ID) {
            return true;
        }

        sleep_msec(10);
    }

    return false;
}

static bool data_init(void)
{
    bool success = false;

    uint8_t vhv_config_scl_sda = 0;

    if (!i2c_read_addr8_data8(REG_VHV_CONFIG_PAD_SCL_SDA_EXTSUP_HV,
                              &vhv_config_scl_sda)) {
        return false;
    }

    vhv_config_scl_sda |= 0x01;

    if (!i2c_write_addr8_data8(REG_VHV_CONFIG_PAD_SCL_SDA_EXTSUP_HV,
                               vhv_config_scl_sda)) {
        return false;
    }

    success = i2c_write_addr8_data8(0x88, 0x00);

    success &= i2c_write_addr8_data8(0x80, 0x01);
    success &= i2c_write_addr8_data8(0xFF, 0x01);
    success &= i2c_write_addr8_data8(0x00, 0x00);
    success &= i2c_read_addr8_data8(0x91, &stop_variable);
    success &= i2c_write_addr8_data8(0x00, 0x01);
    success &= i2c_write_addr8_data8(0xFF, 0x00);
    success &= i2c_write_addr8_data8(0x80, 0x00);

    return success;
}

static bool read_strobe(void)
{
    uint8_t strobe = 0;

    if (!i2c_write_addr8_data8(0x83, 0x00)) {
        return false;
    }

    for (int timeout = 0; timeout < TIMEOUT_SHORT_MS; timeout++) {
        if (!i2c_read_addr8_data8(0x83, &strobe)) {
            return false;
        }

        if (strobe != 0) {
            if (!i2c_write_addr8_data8(0x83, 0x01)) {
                return false;
            }

            return true;
        }

        sleep_msec(1);
    }

    return false;
}

static bool get_spad_info_from_nvm(uint8_t *spad_count,
                                   uint8_t *spad_type,
                                   uint8_t good_spad_map[SPAD_MAP_ROW_COUNT])
{
    bool success = false;
    uint8_t tmp_data8 = 0;
    uint32_t tmp_data32 = 0;

    if (spad_count == NULL || spad_type == NULL || good_spad_map == NULL) {
        return false;
    }

    success  = i2c_write_addr8_data8(0x80, 0x01);
    success &= i2c_write_addr8_data8(0xFF, 0x01);
    success &= i2c_write_addr8_data8(0x00, 0x00);
    success &= i2c_write_addr8_data8(0xFF, 0x06);
    success &= i2c_read_addr8_data8(0x83, &tmp_data8);
    success &= i2c_write_addr8_data8(0x83, tmp_data8 | 0x04);
    success &= i2c_write_addr8_data8(0xFF, 0x07);
    success &= i2c_write_addr8_data8(0x81, 0x01);
    success &= i2c_write_addr8_data8(0x80, 0x01);

    if (!success) {
        return false;
    }

    if (!i2c_write_addr8_data8(0x94, 0x6B)) {
        return false;
    }

    if (!read_strobe()) {
        return false;
    }

    if (!i2c_read_addr8_data32(0x90, &tmp_data32)) {
        return false;
    }

    *spad_count = (tmp_data32 >> 8) & 0x7F;
    *spad_type = (tmp_data32 >> 15) & 0x01;

    success  = i2c_write_addr8_data8(0x81, 0x00);
    success &= i2c_write_addr8_data8(0xFF, 0x06);
    success &= i2c_read_addr8_data8(0x83, &tmp_data8);
    success &= i2c_write_addr8_data8(0x83, tmp_data8 & 0xFB);
    success &= i2c_write_addr8_data8(0xFF, 0x01);
    success &= i2c_write_addr8_data8(0x00, 0x01);
    success &= i2c_write_addr8_data8(0xFF, 0x00);
    success &= i2c_write_addr8_data8(0x80, 0x00);

    if (!success) {
        return false;
    }

    if (!i2c_read_addr8_bytes(REG_GLOBAL_CONFIG_SPAD_ENABLES_REF_0,
                              good_spad_map,
                              SPAD_MAP_ROW_COUNT)) {
        return false;
    }

    return true;
}

static bool set_spads_from_nvm(void)
{
    uint8_t spad_map[SPAD_MAP_ROW_COUNT] = { 0 };
    uint8_t good_spad_map[SPAD_MAP_ROW_COUNT] = { 0 };
    uint8_t spads_enabled_count = 0;
    uint8_t spads_to_enable_count = 0;
    uint8_t spad_type = 0;

    if (!get_spad_info_from_nvm(&spads_to_enable_count,
                                &spad_type,
                                good_spad_map)) {
        return false;
    }

    bool success = i2c_write_addr8_data8(0xFF, 0x01);
    success &= i2c_write_addr8_data8(REG_DYNAMIC_SPAD_REF_EN_START_OFFSET, 0x00);
    success &= i2c_write_addr8_data8(REG_DYNAMIC_SPAD_NUM_REQUESTED_REF_SPAD, 0x2C);
    success &= i2c_write_addr8_data8(0xFF, 0x00);
    success &= i2c_write_addr8_data8(REG_GLOBAL_CONFIG_REF_EN_START_SELECT,
                                     SPAD_START_SELECT);

    if (!success) {
        return false;
    }

    uint8_t offset = (spad_type == SPAD_TYPE_APERTURE) ?
                     SPAD_APERTURE_START_INDEX : 0;

    for (int row = 0; row < SPAD_MAP_ROW_COUNT; row++) {
        for (int column = 0; column < SPAD_ROW_SIZE; column++) {
            int index = (row * SPAD_ROW_SIZE) + column;

            if (spads_enabled_count == spads_to_enable_count) {
                break;
            }

            if (index >= SPAD_MAX_COUNT) {
                return false;
            }

            if (index < offset) {
                continue;
            }

            if ((good_spad_map[row] >> column) & 0x01) {
                spad_map[row] |= (1 << column);
                spads_enabled_count++;
            }
        }

        if (spads_enabled_count == spads_to_enable_count) {
            break;
        }
    }

    if (spads_enabled_count != spads_to_enable_count) {
        return false;
    }

    if (!i2c_write_addr8_bytes(REG_GLOBAL_CONFIG_SPAD_ENABLES_REF_0,
                               spad_map,
                               SPAD_MAP_ROW_COUNT)) {
        return false;
    }

    return true;
}

static bool load_default_tuning_settings(void)
{
    bool success = i2c_write_addr8_data8(0xFF, 0x01);

    success &= i2c_write_addr8_data8(0x00, 0x00);
    success &= i2c_write_addr8_data8(0xFF, 0x00);
    success &= i2c_write_addr8_data8(0x09, 0x00);
    success &= i2c_write_addr8_data8(0x10, 0x00);
    success &= i2c_write_addr8_data8(0x11, 0x00);
    success &= i2c_write_addr8_data8(0x24, 0x01);
    success &= i2c_write_addr8_data8(0x25, 0xFF);
    success &= i2c_write_addr8_data8(0x75, 0x00);

    success &= i2c_write_addr8_data8(0xFF, 0x01);
    success &= i2c_write_addr8_data8(0x4E, 0x2C);
    success &= i2c_write_addr8_data8(0x48, 0x00);
    success &= i2c_write_addr8_data8(0x30, 0x20);

    success &= i2c_write_addr8_data8(0xFF, 0x00);
    success &= i2c_write_addr8_data8(0x30, 0x09);
    success &= i2c_write_addr8_data8(0x54, 0x00);
    success &= i2c_write_addr8_data8(0x31, 0x04);
    success &= i2c_write_addr8_data8(0x32, 0x03);
    success &= i2c_write_addr8_data8(0x40, 0x83);
    success &= i2c_write_addr8_data8(0x46, 0x25);
    success &= i2c_write_addr8_data8(0x60, 0x00);
    success &= i2c_write_addr8_data8(0x27, 0x00);
    success &= i2c_write_addr8_data8(0x50, 0x06);
    success &= i2c_write_addr8_data8(0x51, 0x00);
    success &= i2c_write_addr8_data8(0x52, 0x96);
    success &= i2c_write_addr8_data8(0x56, 0x08);
    success &= i2c_write_addr8_data8(0x57, 0x30);
    success &= i2c_write_addr8_data8(0x61, 0x00);
    success &= i2c_write_addr8_data8(0x62, 0x00);
    success &= i2c_write_addr8_data8(0x64, 0x00);
    success &= i2c_write_addr8_data8(0x65, 0x00);
    success &= i2c_write_addr8_data8(0x66, 0xA0);

    success &= i2c_write_addr8_data8(0xFF, 0x01);
    success &= i2c_write_addr8_data8(0x22, 0x32);
    success &= i2c_write_addr8_data8(0x47, 0x14);
    success &= i2c_write_addr8_data8(0x49, 0xFF);
    success &= i2c_write_addr8_data8(0x4A, 0x00);

    success &= i2c_write_addr8_data8(0xFF, 0x00);
    success &= i2c_write_addr8_data8(0x7A, 0x0A);
    success &= i2c_write_addr8_data8(0x7B, 0x00);
    success &= i2c_write_addr8_data8(0x78, 0x21);

    success &= i2c_write_addr8_data8(0xFF, 0x01);
    success &= i2c_write_addr8_data8(0x23, 0x34);
    success &= i2c_write_addr8_data8(0x42, 0x00);
    success &= i2c_write_addr8_data8(0x44, 0xFF);
    success &= i2c_write_addr8_data8(0x45, 0x26);
    success &= i2c_write_addr8_data8(0x46, 0x05);
    success &= i2c_write_addr8_data8(0x40, 0x40);
    success &= i2c_write_addr8_data8(0x0E, 0x06);
    success &= i2c_write_addr8_data8(0x20, 0x1A);
    success &= i2c_write_addr8_data8(0x43, 0x40);

    success &= i2c_write_addr8_data8(0xFF, 0x00);
    success &= i2c_write_addr8_data8(0x34, 0x03);
    success &= i2c_write_addr8_data8(0x35, 0x44);

    success &= i2c_write_addr8_data8(0xFF, 0x01);
    success &= i2c_write_addr8_data8(0x31, 0x04);
    success &= i2c_write_addr8_data8(0x4B, 0x09);
    success &= i2c_write_addr8_data8(0x4C, 0x05);
    success &= i2c_write_addr8_data8(0x4D, 0x04);

    success &= i2c_write_addr8_data8(0xFF, 0x00);
    success &= i2c_write_addr8_data8(0x44, 0x00);
    success &= i2c_write_addr8_data8(0x45, 0x20);
    success &= i2c_write_addr8_data8(0x47, 0x08);
    success &= i2c_write_addr8_data8(0x48, 0x28);
    success &= i2c_write_addr8_data8(0x67, 0x00);
    success &= i2c_write_addr8_data8(0x70, 0x04);
    success &= i2c_write_addr8_data8(0x71, 0x01);
    success &= i2c_write_addr8_data8(0x72, 0xFE);
    success &= i2c_write_addr8_data8(0x76, 0x00);
    success &= i2c_write_addr8_data8(0x77, 0x00);

    success &= i2c_write_addr8_data8(0xFF, 0x01);
    success &= i2c_write_addr8_data8(0x0D, 0x01);

    success &= i2c_write_addr8_data8(0xFF, 0x00);
    success &= i2c_write_addr8_data8(0x80, 0x01);
    success &= i2c_write_addr8_data8(0x01, 0xF8);

    success &= i2c_write_addr8_data8(0xFF, 0x01);
    success &= i2c_write_addr8_data8(0x8E, 0x01);
    success &= i2c_write_addr8_data8(0x00, 0x01);

    success &= i2c_write_addr8_data8(0xFF, 0x00);
    success &= i2c_write_addr8_data8(0x80, 0x00);

    return success;
}

static bool configure_interrupt(void)
{
    uint8_t gpio_hv_mux_active_high = 0;

    if (!i2c_write_addr8_data8(REG_SYSTEM_INTERRUPT_CONFIG_GPIO, 0x04)) {
        return false;
    }

    if (!i2c_read_addr8_data8(REG_GPIO_HV_MUX_ACTIVE_HIGH,
                              &gpio_hv_mux_active_high)) {
        return false;
    }

    gpio_hv_mux_active_high &= ~0x10;

    if (!i2c_write_addr8_data8(REG_GPIO_HV_MUX_ACTIVE_HIGH,
                               gpio_hv_mux_active_high)) {
        return false;
    }

    if (!i2c_write_addr8_data8(REG_SYSTEM_INTERRUPT_CLEAR, 0x01)) {
        return false;
    }

    return true;
}

static bool set_sequence_steps_enabled(uint8_t sequence_step)
{
    return i2c_write_addr8_data8(REG_SYSTEM_SEQUENCE_CONFIG, sequence_step);
}

static bool static_init(void)
{
    if (!set_spads_from_nvm()) {
        return false;
    }

    if (!load_default_tuning_settings()) {
        return false;
    }

    if (!configure_interrupt()) {
        return false;
    }

    if (!set_sequence_steps_enabled(RANGE_SEQUENCE_STEP_DSS |
                                    RANGE_SEQUENCE_STEP_PRE_RANGE |
                                    RANGE_SEQUENCE_STEP_FINAL_RANGE)) {
        return false;
    }

    return true;
}

static bool perform_single_ref_calibration(calibration_type_t calib_type)
{
    uint8_t sysrange_start = 0;
    uint8_t sequence_config = 0;

    switch (calib_type) {
    case CALIBRATION_TYPE_VHV:
        sequence_config = 0x01;
        sysrange_start = 0x01 | 0x40;
        break;

    case CALIBRATION_TYPE_PHASE:
        sequence_config = 0x02;
        sysrange_start = 0x01;
        break;

    default:
        return false;
    }

    if (!i2c_write_addr8_data8(REG_SYSTEM_SEQUENCE_CONFIG, sequence_config)) {
        return false;
    }

    if (!i2c_write_addr8_data8(REG_SYSRANGE_START, sysrange_start)) {
        return false;
    }

    if (!wait_for_interrupt(TIMEOUT_RANGE_MS)) {
        return false;
    }

    if (!i2c_write_addr8_data8(REG_SYSTEM_INTERRUPT_CLEAR, 0x01)) {
        return false;
    }

    if (!i2c_write_addr8_data8(REG_SYSRANGE_START, 0x00)) {
        return false;
    }

    return true;
}

static bool perform_ref_calibration(void)
{
    if (!perform_single_ref_calibration(CALIBRATION_TYPE_VHV)) {
        return false;
    }

    if (!perform_single_ref_calibration(CALIBRATION_TYPE_PHASE)) {
        return false;
    }

    if (!set_sequence_steps_enabled(RANGE_SEQUENCE_STEP_DSS |
                                    RANGE_SEQUENCE_STEP_PRE_RANGE |
                                    RANGE_SEQUENCE_STEP_FINAL_RANGE)) {
        return false;
    }

    return true;
}

static bool init_addresses(void)
{
    /*
     * Single-sensor setup:
     * no XSHUT control, no address reassignment.
     */
    i2c_set_slave_address(VL53L0X_DEFAULT_ADDRESS);
    return device_is_booted();
}

static bool init_config(vl53l0x_idx_t idx)
{
    if (idx != VL53L0X_IDX_FIRST) {
        return false;
    }

    i2c_set_slave_address(vl53l0x_infos[idx].addr);

    if (!data_init()) {
        return false;
    }

    if (!static_init()) {
        return false;
    }

    if (!perform_ref_calibration()) {
        return false;
    }

    return true;
}

bool vl53l0x_init(void)
{
    if (!init_addresses()) {
        return false;
    }

    if (!init_config(VL53L0X_IDX_FIRST)) {
        return false;
    }

    return true;
}

bool vl53l0x_read_range_single(vl53l0x_idx_t idx, uint16_t *range)
{
    bool success = false;

    if (idx != VL53L0X_IDX_FIRST || range == NULL) {
        return false;
    }

    i2c_set_slave_address(vl53l0x_infos[idx].addr);

    success  = i2c_write_addr8_data8(0x80, 0x01);
    success &= i2c_write_addr8_data8(0xFF, 0x01);
    success &= i2c_write_addr8_data8(0x00, 0x00);
    success &= i2c_write_addr8_data8(0x91, stop_variable);
    success &= i2c_write_addr8_data8(0x00, 0x01);
    success &= i2c_write_addr8_data8(0xFF, 0x00);
    success &= i2c_write_addr8_data8(0x80, 0x00);

    if (!success) {
        return false;
    }

    if (!i2c_write_addr8_data8(REG_SYSRANGE_START, 0x01)) {
        return false;
    }

    if (!wait_for_sysrange_start_clear(TIMEOUT_RANGE_MS)) {
        return false;
    }

    if (!wait_for_interrupt(TIMEOUT_RANGE_MS)) {
        return false;
    }

    if (!i2c_read_addr8_data16(REG_RESULT_RANGE_STATUS + 10, range)) {
        return false;
    }

    if (!i2c_write_addr8_data8(REG_SYSTEM_INTERRUPT_CLEAR, 0x01)) {
        return false;
    }

    if (*range == 8190 || *range == 8191 || *range > 2000) {
        *range = VL53L0X_OUT_OF_RANGE;
    }

    return true;
}