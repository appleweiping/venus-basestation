#include <libpynq.h>
#include <buttons.h>
#include "tmprtr_v0.2.h"

int main(void) {
    pynq_init();
    temperature_init();

    while (1) {
        printf("Raw: %u | Voltage: %.3f V | Temperature: %.1f C\n",
               temperature_raw_channel(), temperature_voltage(), getTemperature());

        sleep_msec(1000);
        if (get_button_state(BUTTON0) == 1) break;
    }

    temperature_destroy();
    pynq_destroy();
    return EXIT_SUCCESS;
}