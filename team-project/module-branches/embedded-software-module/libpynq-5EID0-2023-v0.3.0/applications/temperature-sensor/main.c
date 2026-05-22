#include <stdio.h>
#include <libpynq.h>

int main(void) {
    pynq_init();
    adc_init();

    while (1) {
        // Returns voltage directly: 0.0 to 3.3 V
        double voltage = adc_read_channel(ADC0);

        // TMP36 formula: temp °C = (voltage) * 100
        double temperature = (voltage) * 100.0;

        // Raw 16-bit value (0–65535) if you need it
        uint32_t raw = adc_read_channel_raw(ADC0);

        printf("Raw: %u | Voltage: %.3f V | Temperature: %.1f C\n",
               raw, voltage, temperature);

        sleep_msec(1000);
    }

    adc_destroy();
    pynq_destroy();
    return EXIT_SUCCESS;
}