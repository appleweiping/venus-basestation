#include "motion-functions.h"
#include <libpynq.h>
#include <stepper.h>
#define ratio 10


void move(int distance_in_cm) {
    float left,right;

    left = distance_in_cm * ratio;
    right = left;

    if (steps <= 32767 && steps >= -32768) {
    stepper_steps((int16_t)left, (int16_t)right);
    while(!stepper_steps_done()) continue;
}

    sleep_msec(100);
}
