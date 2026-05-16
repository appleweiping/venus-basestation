#include <stdio.h>
#include <stdlib.h>
#include <libpynq.h>

#define R2 10000.0
#define V_REF 3.3

double r_to_t(double r_t) {
    // temporary simple example
    // you still need to implement real thermistor formula here
    return r_t;
}

int main(void) {
    pynq_init();
    adc_init();
    buttons_init();
    switchbox_init();
    gpio_init();
    gpio_reset();

    double v_out;
    double r_t;
    double temperature;

    while (!get_button_state(BUTTON0)) {
        v_out = adc_read_channel(ADC0);   // A0 input

        if (v_out > 0.01) {
            r_t = (V_REF - v_out) * R2 / v_out;
            temperature = r_to_t(r_t);

            printf("v_out: %f, r_t: %f, temperature: %f\n",
                   v_out, r_t, temperature);
        } else {
            printf("v_out too low, cannot calculate resistance\n");
        }

        sleep_msec(1000);
    }

    adc_destroy();
    buttons_destroy();
    pynq_destroy();

    return 0;
}