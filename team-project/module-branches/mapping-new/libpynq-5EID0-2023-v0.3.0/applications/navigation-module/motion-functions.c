#include "motion-functions.h"
#include <libpynq.h>
#include <stepper.h>

//TODO:
/*
    - Make move function use distance_in_cm parameter
    - Make motionInit quantize the speed (if needed)
    -
*/

static int* distance_register_h;

void motionInit(int speed_0_to_100, int* distance_register) {
    stepper_init();
    stepper_enable();
    distance_register_h = distance_register;
    stepper_set_speed(10000, 10000);

}

void orient(color_sensor_t raw_sensor) {
    /* THIS FUNCTION SHOULD TURN THE ROBOT AT AN ANGLE SUCH THAT IT'S 
    FORWARD TRAJECTORY IS PARALLEL TO THE BORDER */
    while (raw_sensor.color_pointer == black) 
}

void logSTeps(int steps) {

}

void log_distance(int distance_cm) {
    *distance_register_h += distance_cm;
}

void move(int distance_in_cm) {
    
    log_distance(distance_in_cm);
    logSteps();
    stepper_steps(1600, 1600);
    while(!stepper_steps_done()) continue;

    sleep_msec(200);
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
