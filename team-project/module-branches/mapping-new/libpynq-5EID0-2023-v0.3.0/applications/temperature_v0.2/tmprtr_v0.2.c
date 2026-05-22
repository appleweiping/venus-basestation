#include "tmprtr_v0.2.h"
#include <stdio.h>
#include <libpynq.h>

void temperature_init() {
    adc_init();
}

double temperature_voltage() {
    return adc_read_channel(ADC0);
}

double temperature_raw_channel() {
    return adc_read_channel_raw(ADC0);
}


double getTemperature() {
    return temperature_voltage() * 100.0;
}

void temperature_destroy() {
    adc_destroy();
}