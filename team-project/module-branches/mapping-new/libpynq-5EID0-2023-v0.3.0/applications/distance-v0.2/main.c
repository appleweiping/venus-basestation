#include <stdio.h>
#include <signal.h>
#include <libpynq.h>
#include "vlx.h"

#define OFFSET 0
#define SAMPLES 10



int main(void) {
    //signal(SIGINT, handle_sigint);
    bool running = true;
    pynq_init();

    switchbox_set_pin(IO_AR_SCL, SWB_IIC0_SCL);
    switchbox_set_pin(IO_AR_SDA, SWB_IIC0_SDA);
    iic_init(IIC0);

    VL53L0X_Dev_t sensor;
    if (tofInit(&sensor, IIC0, 0x29) != 0) {
        printf("Sensor Init Failed!\n");
        return 1;
    }

    printf("Starting averaged scans (10 samples, 5s interval)...\n");

    while (running) {
        uint32_t sum = 0;
        int valid_samples = 0;

        printf("Sampling...");
        fflush(stdout);

        for (int i = 0; i < SAMPLES; i++) {
            uint32_t raw = tofReadDistance(&sensor);
            
            // Only average values that aren't error codes (like 8190)
            if (raw > OFFSET && raw < 2000) {
                sum += (raw - OFFSET);
                valid_samples++;
            }
            // Small delay between samples to let the sensor reset
            sleep_msec(30); 
        }

        if (valid_samples > 0) {
            float avg_mm = (float)sum / valid_samples;
            float avg_cm = avg_mm / 10.0; // Convert mm to cm
            printf("\rAverage Distance: %.2f cm (based on %d samples)\n", avg_cm, valid_samples);
        } else {
            printf("\rAverage Distance: Error (Out of bounds)\n");
        }

        // 5-second wait until the next 10-sample burst
        for(int i = 0; i < 50; i++) {
            if(!running) break;
            sleep_msec(10); 
        }
    }

    iic_destroy(IIC0);
    pynq_destroy();
    return 0;
}