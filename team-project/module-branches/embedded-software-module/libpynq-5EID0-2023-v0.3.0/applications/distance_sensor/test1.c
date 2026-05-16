#include <stdio.h>
#include <stdint.h>
#include <fcntl.h>
#include <unistd.h>
#include <sys/ioctl.h>
#include <linux/i2c-dev.h>

#define VL53L0X_ADDR     0x29
#define I2C_BUS          "/dev/i2c-1"

// Write a byte to a register
void write_reg(int fd, uint8_t reg, uint8_t val) {
    uint8_t buf[2] = {reg, val};
    write(fd, buf, 2);
}

// Read a byte from a register
uint8_t read_reg(int fd, uint8_t reg) {
    write(fd, &reg, 1);
    uint8_t val;
    read(fd, &val, 1);
    return val;
}

// Read 16-bit big-endian value
uint16_t read_reg16(int fd, uint8_t reg) {
    write(fd, &reg, 1);
    uint8_t buf[2];
    read(fd, buf, 2);
    return (buf[0] << 8) | buf[1];
}

int main2() {
    int fd = open(I2C_BUS, O_RDWR);
    if (fd < 0) { perror("open"); return 1; }
    ioctl(fd, I2C_SLAVE, VL53L0X_ADDR);

    // Verify device (WHO_AM_I register 0xC0 should return 0xEE)
    uint8_t id = read_reg(fd, 0xC0);
    printf("Device ID: 0x%02X (expect 0xEE)\n", id);

    // Basic init sequence (single ranging mode)
    write_reg(fd, 0x88, 0x00);  // standard range mode
    write_reg(fd, 0x80, 0x01);
    write_reg(fd, 0xFF, 0x01);
    write_reg(fd, 0x00, 0x00);
    write_reg(fd, 0xFF, 0x00);
    write_reg(fd, 0x80, 0x00);

    // Trigger a single measurement
    write_reg(fd, 0x00, 0x01);  // SYSRANGE_START

    // Poll until measurement complete (bit 0 of 0x13 goes high)
    uint8_t status;
    do {
        status = read_reg(fd, 0x13);
        sleep(1);
    } while (!(status & 0x07));

    // Read range result (register 0x1E, 2 bytes, in mm)
    uint16_t range_mm = read_reg16(fd, 0x1E);
    printf("Distance: %u mm\n", range_mm);

    // Clear interrupt
    write_reg(fd, 0x0B, 0x01);

    close(fd);
    return 0;
}