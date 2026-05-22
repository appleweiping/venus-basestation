#include "vlx.h"

#define OFFSET 0
#define SAMPLES 10

static volatile int running = 1;
void handle_sigint(int sig) { (void)sig; running = 0; }

int tofInit(VL53L0X_Dev_t *dev, iic_index_t bus, uint8_t addr) {
    dev->iic_bus = bus;
    dev->address = addr;

    // Check ID (Expected 0xEE)
    uint8_t id;
    iic_read_register(dev->iic_bus, dev->address, 0xC0, &id, 1);
    if (id != 0xEE) return -1;

    // Mandatory Initialization Sequence
    uint8_t init_seq[][2] = {
        {0x88, 0x00}, {0x80, 0x01}, {0xFF, 0x01}, {0x00, 0x00},
        {0x91, 0x3C}, {0x00, 0x01}, {0xFF, 0x00}, {0x80, 0x00},
        {0x0B, 0x01} // Clear interrupts
    };

    for(int i = 0; i < 9; i++) {
        iic_write_register(dev->iic_bus, dev->address, init_seq[i][0], &init_seq[i][1], 1);
    }
    return 0;
}

uint32_t tofReadDistance(VL53L0X_Dev_t *dev) {
    uint8_t start = 0x01;
    uint8_t status = 0;
    uint8_t data[2];

    // Trigger measurement
    iic_write_register(dev->iic_bus, dev->address, 0x00, &start, 1);

    // Poll for completion (timeout ~100ms)
    for (int i = 0; i < 100; i++) {
        iic_read_register(dev->iic_bus, dev->address, 0x13, &status, 1);
        if (status & 0x07) break;
        sleep_msec(1);
    }

    // Read result
    iic_read_register(dev->iic_bus, dev->address, 0x1E, data, 2);
    
    // Clear interrupt for next reading
    uint8_t clear = 0x01;
    iic_write_register(dev->iic_bus, dev->address, 0x0B, &clear, 1);

    return (uint32_t)((data[0] << 8) | data[1]);
}
