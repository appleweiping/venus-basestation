#include "motion-functions.h"
#include <libpynq.h>
#include <stepper.h>
#define ratio 10

void motionInit(int speed_0_to_100) {
    stepper_init();
    stepper_enable();

    stepper_set_speed(10000, 10000);

}

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

void turn90(side turning_side) {
    switch (turning_side) {
        case LEFT:
                stepper_steps(-1600, 1600);
            break;
        case RIGHT:
                stepper_steps(1600, -1600);
            break;
        default: 
            printf("Default case: turn90");
            break;
        
    }
    stepper_steps(1600, 1600);
}

bool moving() { return stepper_steps_done(); }

void motionDestroy() {
    stepper_destroy();

}
