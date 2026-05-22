#ifndef TMPRTR_V02
#define TMPRTR_V02

#include <libpynq.h>

void temperature_init(void);
double temperature_voltage(void);
double temperature_raw_channel(void);
double getTemperature(void);
void temperature_destroy(void);

#endif