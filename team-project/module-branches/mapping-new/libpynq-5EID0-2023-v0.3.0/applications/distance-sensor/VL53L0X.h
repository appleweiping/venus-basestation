#ifndef VL53LOX_H
#define VL53LOX_H

#include <libpynq.h>

int distance_init(void); /*! BLOCKING 1.1s !*/
void distance_destroy();
uint16_t getDistance(void);


#endif